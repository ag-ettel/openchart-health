"""Scheduled CMS data refresh wrapper.

Designed to be invoked by cron (Linux/macOS) or Task Scheduler (Windows).
See docs/refresh_schedule.md for recommended cadence and entry templates.

Sequence:
    1. Acquire single-instance file lock (.pipeline_refresh.lock)
    2. Run detection (scripts/detect_cms_refresh.py)
    3. If new data is available: run pipeline -> benchmarks -> export
    4. Run ownership change diff if a previous archive vintage exists
    5. POST status to REFRESH_NOTIFY_URL (env, optional)
    6. Release lock

Failure modes (Rule 6 — no silent failures):
    - Pipeline aborts on >5% per-dataset failure threshold; orchestrator
      already preserves build/data/. We propagate the abort as a non-zero
      exit and surface the anomaly list in the notification payload.
    - Export failures: build_json renames build/data -> build/data_previous
      *before* renaming build/data_staging -> build/data, so any failure
      mid-export leaves the previous successful export intact (verified
      against pipeline/export/build_json.py:1056-1062).
    - Lock contention: exit immediately with code 75 (EX_TEMPFAIL).
    - Webhook failures are logged but do not change the exit code; the
      run already happened.

Logs: logs/scheduled_refresh_YYYY-MM-DD.log (append).
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import socket
import subprocess
import sys
import time
import traceback
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

import requests

# Allow running as a top-level script
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.detect_cms_refresh import (  # noqa: E402
    DEFAULT_DB_URL,
    default_output_path as detection_default_output,
    detect_refreshes,
    write_report,
)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

LOGS_DIR = _REPO_ROOT / "logs"


def _configure_logging(verbose: bool) -> Path:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_path = LOGS_DIR / f"scheduled_refresh_{today}.log"

    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s"
    ))
    stream = logging.StreamHandler(sys.stderr)
    stream.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(logging.DEBUG if verbose else logging.INFO)
    root.addHandler(handler)
    root.addHandler(stream)
    return log_path


logger = logging.getLogger("scheduled_refresh")


# ---------------------------------------------------------------------------
# Lock — file-based, single-instance.
# ---------------------------------------------------------------------------

# NOTE: `.claude/scheduled_tasks.lock` is reserved for the Claude Code harness'
# own scheduler. We use a dedicated path so refresh runs don't collide with
# unrelated tooling in the workspace.
LOCK_PATH = _REPO_ROOT / ".pipeline_refresh.lock"


@contextmanager
def acquire_lock(path: Path = LOCK_PATH) -> Iterator[Path]:
    """Acquire an exclusive file lock for the duration of the context.

    Cross-platform implementation: O_CREAT | O_EXCL is atomic on POSIX, and
    also rejects on Windows when the file already exists. If the file is
    present, the lock is contended.

    Stale lock recovery: if the recorded PID is not running, we steal the
    lock. Without this, a crashed previous run would block forever.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    # Detect stale lock (process listed in the file isn't alive)
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                existing = json.load(f)
            stale_pid = int(existing.get("pid", 0))
            if stale_pid and not _pid_alive(stale_pid):
                logger.warning("Stale lock from PID %d found; reclaiming.", stale_pid)
                path.unlink(missing_ok=True)
        except (json.JSONDecodeError, ValueError, OSError) as exc:
            logger.warning("Could not parse existing lock %s (%s); leaving in place.", path, exc)

    try:
        fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise LockContention(f"Lock {path} already held") from exc

    payload = {
        "pid": os.getpid(),
        "host": socket.gethostname(),
        "acquired_at": datetime.now(timezone.utc).isoformat(),
        "tool": "scripts/scheduled_refresh.py",
    }
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f)
        yield path
    finally:
        try:
            path.unlink(missing_ok=True)
        except OSError as exc:
            logger.warning("Failed to remove lock %s: %s", path, exc)


class LockContention(RuntimeError):
    """Raised when the lock is already held by a live process."""


def _pid_alive(pid: int) -> bool:
    """Return True iff the OS reports a process with this PID is running."""
    if pid <= 0:
        return False
    if os.name == "nt":
        # Windows: tasklist; if the PID isn't in the output it's gone.
        try:
            out = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/NH", "/FO", "CSV"],
                capture_output=True, text=True, timeout=10, check=False,
            )
            return str(pid) in (out.stdout or "")
        except (OSError, subprocess.TimeoutExpired):
            return True  # Conservative: assume alive (don't steal lock)
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # Owned by another user — still alive
    except OSError:
        return True


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass
class RunResult:
    started_at: str
    completed_at: str | None = None
    success: bool = False
    skipped: bool = False
    skip_reason: str | None = None
    refresh_available_count: int = 0
    pipeline_rows_upserted: int = 0
    pipeline_rows_failed: int = 0
    pipeline_aborted: bool = False
    pipeline_anomalies: list[str] = field(default_factory=list)
    export_files_written: int | None = None
    ownership_diff_path: str | None = None
    detection_report_path: str | None = None
    log_path: str | None = None
    error: str | None = None
    error_traceback: str | None = None


# ---------------------------------------------------------------------------
# Pipeline + export invocation
# ---------------------------------------------------------------------------

def _run_pipeline(
    db_url: str,
    data_dir: str,
    provider_types: list[str] | None,
) -> dict[str, Any]:
    """Run the full pipeline + export through the orchestrator.

    Imports inside the function so that detection-only invocations of this
    script don't pay the import cost (and don't fail when the pipeline
    package has heavy optional deps).
    """
    from pipeline.export.build_json import export_all  # local import
    from pipeline.orchestrate import run_pipeline  # local import

    logger.info("Running pipeline (db=%s, data=%s, provider_types=%s)",
                db_url, data_dir, provider_types)
    result = run_pipeline(
        db_url=db_url,
        data_dir=data_dir,
        provider_types=provider_types,
    )

    if result.aborted:
        # Rule 6: abort propagates. build/data is preserved by export not running.
        return {
            "rows_upserted": result.rows_upserted,
            "rows_failed": result.rows_failed,
            "aborted": True,
            "anomalies": list(result.anomalies),
            "export_files_written": None,
        }

    logger.info("Pipeline OK; running export_all")
    files_written = export_all(db_url=db_url)

    return {
        "rows_upserted": result.rows_upserted,
        "rows_failed": result.rows_failed,
        "aborted": False,
        "anomalies": list(result.anomalies),
        "export_files_written": files_written,
    }


# ---------------------------------------------------------------------------
# Ownership diff
# ---------------------------------------------------------------------------

def _maybe_run_ownership_diff(data_dir: Path, db_url: str) -> Path | None:
    """Run scripts/check_ownership_changes.py against the two newest NH archives.

    Returns the path to the generated markdown report, or None when there
    are fewer than two NH vintages on disk (no diff possible).
    """
    script = _REPO_ROOT / "scripts" / "check_ownership_changes.py"
    if not script.exists():
        logger.info("Ownership diff script not present; skipping.")
        return None

    try:
        from pipeline.ingest.csv_reader import discover_archives
    except ImportError as exc:
        logger.warning("csv_reader import failed; skipping ownership diff: %s", exc)
        return None

    archives = [a for a in discover_archives(data_dir) if a.provider_type == "nursing_homes"]
    if len(archives) < 2:
        logger.info("Ownership diff: fewer than two NH archives; skipping.")
        return None

    archives_sorted = sorted(archives, key=lambda a: (a.year, a.month))
    previous = archives_sorted[-2].vintage_label
    current = archives_sorted[-1].vintage_label
    out_md = _REPO_ROOT / "docs" / f"ownership_changes_{previous}_to_{current}.md"

    logger.info("Running ownership diff %s -> %s", previous, current)
    try:
        completed = subprocess.run(
            [
                sys.executable, str(script),
                "--previous", previous,
                "--current", current,
                "--data-dir", str(data_dir),
                "--db-url", db_url,
            ],
            cwd=str(_REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.error("Ownership diff failed to run: %s", exc)
        return None

    if completed.returncode != 0:
        logger.error(
            "Ownership diff exited %d. stderr=%s",
            completed.returncode, (completed.stderr or "")[-500:],
        )
        return None

    if out_md.exists():
        logger.info("Ownership diff written to %s", out_md)
        return out_md
    return None


# ---------------------------------------------------------------------------
# Webhook
# ---------------------------------------------------------------------------

def _notify_webhook(payload: dict[str, Any]) -> None:
    """POST status payload to REFRESH_NOTIFY_URL when set; no-op otherwise.

    Exception is logged with full context but never re-raised — a webhook
    failure must not turn a successful refresh into a reported failure.
    """
    url = os.environ.get("REFRESH_NOTIFY_URL")
    if not url:
        logger.info("REFRESH_NOTIFY_URL not set; skipping webhook.")
        return
    try:
        response = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=15.0,
        )
        if response.status_code >= 400:
            logger.warning(
                "Webhook %s returned %d: %s",
                url, response.status_code, (response.text or "")[:300],
            )
        else:
            logger.info("Webhook %s acknowledged (%d)", url, response.status_code)
    except requests.RequestException as exc:
        logger.warning("Webhook %s failed: %s", url, exc)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _build_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument(
        "--db-url",
        default=DEFAULT_DB_URL,
        help="Postgres SQLAlchemy URL.",
    )
    parser.add_argument(
        "--data-dir",
        default=str(_REPO_ROOT / "data"),
        help="Path to data/ directory (CMS archives).",
    )
    parser.add_argument(
        "--provider-types",
        nargs="+",
        choices=["hospitals", "nursing_homes"],
        default=None,
        help="Limit pipeline + detection to specific provider types.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Run pipeline + export even when no refresh is detected. "
             "Useful for ad-hoc rebuilds.",
    )
    parser.add_argument(
        "--detection-only",
        action="store_true",
        help="Run detection and webhook only; skip pipeline + export.",
    )
    parser.add_argument(
        "--skip-ownership-diff",
        action="store_true",
        help="Skip the post-refresh ownership change diff.",
    )
    parser.add_argument("--verbose", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_argparser().parse_args(argv)
    log_path = _configure_logging(args.verbose)

    started = datetime.now(timezone.utc)
    result = RunResult(started_at=started.isoformat(), log_path=str(log_path))

    try:
        with acquire_lock():
            logger.info("Lock acquired at %s", LOCK_PATH)

            # --- Detection ---
            try:
                report = detect_refreshes(
                    db_url=args.db_url, provider_types=args.provider_types,
                )
            except Exception as exc:
                tb = traceback.format_exc()
                logger.error("Detection failed: %s\n%s", exc, tb)
                result.error = f"detection: {exc}"
                result.error_traceback = tb
                return _finalize(result, started, success=False, exit_code=2)

            detection_report_path = detection_default_output()
            write_report(report, detection_report_path)
            result.detection_report_path = str(detection_report_path)
            result.refresh_available_count = report.refresh_count

            # If the detection itself flagged API errors, we still want to
            # know — but don't run the pipeline against potentially stale
            # info. Caller can re-run after the API recovers.
            if report.api_errors and not args.force:
                logger.warning("Detection reported %d API errors — skipping pipeline.",
                               report.api_errors)
                result.skipped = True
                result.skip_reason = f"detection_api_errors={report.api_errors}"
                return _finalize(result, started, success=False, exit_code=3)

            if report.refresh_count == 0 and not args.force:
                logger.info("No new data — pipeline run skipped.")
                result.skipped = True
                result.skip_reason = "no_refresh_available"
                return _finalize(result, started, success=True, exit_code=0)

            if args.detection_only:
                logger.info("--detection-only set; not running pipeline.")
                result.skipped = True
                result.skip_reason = "detection_only_flag"
                return _finalize(result, started, success=True, exit_code=0)

            # --- Pipeline + export ---
            try:
                pipe_result = _run_pipeline(
                    db_url=args.db_url,
                    data_dir=args.data_dir,
                    provider_types=args.provider_types,
                )
            except Exception as exc:
                tb = traceback.format_exc()
                logger.error("Pipeline / export failed: %s\n%s", exc, tb)
                result.error = f"pipeline: {exc}"
                result.error_traceback = tb
                return _finalize(result, started, success=False, exit_code=4)

            result.pipeline_rows_upserted = int(pipe_result.get("rows_upserted") or 0)
            result.pipeline_rows_failed = int(pipe_result.get("rows_failed") or 0)
            result.pipeline_aborted = bool(pipe_result.get("aborted"))
            result.pipeline_anomalies = list(pipe_result.get("anomalies") or [])[:50]
            ex_files = pipe_result.get("export_files_written")
            result.export_files_written = int(ex_files) if isinstance(ex_files, int) else None

            if result.pipeline_aborted:
                logger.error("Pipeline aborted (Rule 6). build/data preserved.")
                return _finalize(result, started, success=False, exit_code=5)

            # --- Ownership diff (best-effort) ---
            if not args.skip_ownership_diff:
                try:
                    diff_path = _maybe_run_ownership_diff(
                        data_dir=Path(args.data_dir), db_url=args.db_url,
                    )
                    if diff_path:
                        result.ownership_diff_path = str(diff_path)
                except Exception as exc:  # noqa: BLE001
                    # Best-effort: ownership diff failure doesn't fail the run.
                    logger.warning("Ownership diff step failed: %s", exc)

            return _finalize(result, started, success=True, exit_code=0)

    except LockContention as exc:
        logger.error("Lock contention: %s", exc)
        result.error = "lock_contention"
        return _finalize(result, started, success=False, exit_code=75)
    except Exception as exc:  # noqa: BLE001 — Rule 6
        tb = traceback.format_exc()
        logger.error("Unhandled error in scheduled_refresh: %s\n%s", exc, tb)
        result.error = str(exc)
        result.error_traceback = tb
        return _finalize(result, started, success=False, exit_code=1)


def _finalize(
    result: RunResult,
    started: datetime,
    *,
    success: bool,
    exit_code: int,
) -> int:
    completed = datetime.now(timezone.utc)
    result.completed_at = completed.isoformat()
    result.success = success

    payload: dict[str, Any] = {
        "tool": "scripts/scheduled_refresh.py",
        "host": socket.gethostname(),
        "duration_seconds": (completed - started).total_seconds(),
        "exit_code": exit_code,
        "started_at": result.started_at,
        "completed_at": result.completed_at,
        "success": result.success,
        "skipped": result.skipped,
        "skip_reason": result.skip_reason,
        "refresh_available_count": result.refresh_available_count,
        "pipeline": {
            "rows_upserted": result.pipeline_rows_upserted,
            "rows_failed": result.pipeline_rows_failed,
            "aborted": result.pipeline_aborted,
            "anomalies_sample": result.pipeline_anomalies[:10],
        },
        "export_files_written": result.export_files_written,
        "ownership_diff_path": result.ownership_diff_path,
        "detection_report_path": result.detection_report_path,
        "log_path": result.log_path,
        "error": result.error,
    }
    _notify_webhook(payload)
    logger.info(
        "scheduled_refresh complete in %.1fs (exit=%d, success=%s, skipped=%s)",
        (completed - started).total_seconds(), exit_code, success, result.skipped,
    )
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
