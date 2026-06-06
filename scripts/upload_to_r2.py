"""Upload build/data/*.json to the Cloudflare R2 bucket via the S3 API.

R2 hosts the 22K per-provider JSONs that exceed Cloudflare Pages' file limit.
After a pipeline + export refresh, this script syncs build/data/ to the
`openchart-data` bucket.

Setup (one-time):
    Create an R2 API token in the Cloudflare dashboard
    (R2 → Manage R2 API tokens → Create API token, Object Read & Write
    on `openchart-data`). Then set in the shell:

    PowerShell:
        $env:R2_ACCESS_KEY_ID     = "<access key id>"
        $env:R2_SECRET_ACCESS_KEY = "<secret>"

    bash:
        export R2_ACCESS_KEY_ID="<access key id>"
        export R2_SECRET_ACCESS_KEY="<secret>"

Run:
    python scripts/upload_to_r2.py                     # upload all 22K JSONs
    python scripts/upload_to_r2.py --dry-run           # list what would upload
    python scripts/upload_to_r2.py --workers 32        # tune parallelism
    python scripts/upload_to_r2.py --only 050002.json  # one file (smoke test)

Endpoint and bucket are hard-coded — change here if either ever moves.
"""

from __future__ import annotations

import argparse
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import boto3
from botocore.config import Config


ACCOUNT_ID = "fe0c2db7ae939294767ccae6fa96ae54"
BUCKET = "openchart-data"
ENDPOINT = f"https://{ACCOUNT_ID}.r2.cloudflarestorage.com"


def _load_dotenv() -> None:
    """Populate os.environ from a sibling .env file if present.

    Only sets keys that are not already in the environment so explicit shell
    exports still win. No third-party dependency required.
    """
    env_path = Path(__file__).parent.parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def make_client() -> "boto3.client":
    _load_dotenv()
    access = os.environ.get("R2_ACCESS_KEY_ID")
    secret = os.environ.get("R2_SECRET_ACCESS_KEY")
    if not access or not secret:
        sys.exit(
            "R2_ACCESS_KEY_ID / R2_SECRET_ACCESS_KEY not set in the environment "
            "or .env file. See the module docstring for setup."
        )
    return boto3.client(
        service_name="s3",
        endpoint_url=ENDPOINT,
        aws_access_key_id=access,
        aws_secret_access_key=secret,
        config=Config(
            region_name="auto",
            signature_version="s3v4",
            retries={"max_attempts": 5, "mode": "standard"},
        ),
    )


def upload_one(client: "boto3.client", path: Path) -> tuple[str, bool, str | None]:
    key = path.name
    try:
        client.upload_file(
            str(path),
            BUCKET,
            key,
            ExtraArgs={"ContentType": "application/json", "CacheControl": "public, max-age=300"},
        )
        return key, True, None
    except Exception as exc:  # noqa: BLE001
        return key, False, str(exc)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument(
        "--source",
        default=str(Path(__file__).parent.parent / "build" / "data"),
        help="Directory of JSON files to upload (default: build/data/).",
    )
    parser.add_argument("--workers", type=int, default=16, help="Parallel uploads (default 16).")
    parser.add_argument("--only", help="Upload only this single filename (smoke test).")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    src = Path(args.source)
    if not src.is_dir():
        sys.exit(f"Source not found: {src}")

    if args.only:
        files = [src / args.only]
        if not files[0].exists():
            sys.exit(f"--only {args.only} not found in {src}")
    else:
        files = sorted(src.glob("*.json"))

    if not files:
        sys.exit(f"No .json files in {src}")

    total = len(files)
    total_bytes = sum(f.stat().st_size for f in files)
    print(f"Uploading {total} files ({total_bytes / 1024 / 1024:.1f} MB) to "
          f"s3://{BUCKET} via {ENDPOINT}")

    if args.dry_run:
        for f in files[:10]:
            print(f"  {f.name}")
        if total > 10:
            print(f"  ... and {total - 10} more")
        return 0

    client = make_client()

    done = 0
    failed: list[tuple[str, str]] = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(upload_one, client, f): f for f in files}
        for fut in as_completed(futures):
            key, ok, err = fut.result()
            done += 1
            if not ok:
                failed.append((key, err or ""))
            if done % 500 == 0 or done == total:
                print(f"  uploaded {done}/{total}  ({len(failed)} failed)")

    if failed:
        print(f"\n{len(failed)} uploads failed. First 20:")
        for k, e in failed[:20]:
            print(f"  {k}: {e}")
        return 1

    print(f"\nDone. {total} files uploaded to s3://{BUCKET}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
