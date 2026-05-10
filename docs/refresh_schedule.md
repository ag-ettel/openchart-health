# CMS Data Refresh Schedule

This document describes the recommended cadence for the automated CMS data
refresh pipeline and gives concrete cron / Windows Task Scheduler entries.

The actual run logic lives in `scripts/scheduled_refresh.py`. The detection
phase (`scripts/detect_cms_refresh.py`) can also be invoked standalone.

---

## CMS publication cadence (what we are watching)

Source: `docs/phase_0_findings.md` §"CMS data refresh schedule" and the
January 2026 Hospital Data Dictionary.

| Datasets | CMS cadence | When CMS publishes |
|---|---|---|
| Hospital General Information (xubh-q36u) | quarterly | Jan / Apr / Jul / Oct |
| HCAHPS (dgck-syfz) | quarterly | Jan / Apr / Jul / Oct |
| HAI (77hc-ibv8) | quarterly | Jan / Apr / Jul / Oct |
| Timely & Effective Care quarterly subset (yv7e-xc69) | quarterly | Jan / Apr / Jul / Oct |
| Complications & Deaths (ynj2-r877) | annual | January |
| Readmissions (632h-zaca) | annual | January |
| Outpatient Imaging (wkfw-kthe) | annual | January |
| MSPB (rrqw-56er) | annual | January |
| HRRP (9n3s-kdb3) | annual | August (FY cycle) |
| HACRP (yq43-i98g) | annual | November (FY cycle) |
| VBP (pudb-wetr) | annual | November (FY cycle) |
| NH Provider Information (4pq5-n9py) | monthly | first business week |
| NH MDS Quality (djen-97ju) | quarterly | Jan / Apr / Jul / Oct |
| NH Claims Quality (ijh5-nb2v) | semi-annual | Apr / Oct |
| NH Health Deficiencies (r5ix-sfxw) | monthly | first business week |
| NH Penalties (g6vv-u9sr) | monthly | first business week |
| NH Ownership (y2hd-n93e) | monthly | first business week |
| SNF QRP Provider (fykj-qjee) | quarterly (FY cycle) | Jan / Apr / Jul / Oct |
| SNF VBP (284v-j9fz) | annual | October (FY cycle) |

These dates are not strict — CMS slips by a few days regularly. The
detection script polls dataset `modified` timestamps directly so the
scheduler only needs to run frequently enough to *catch* a publication
within an acceptable lag, not to predict it.

---

## Recommended scheduler cadence

**Detection-only:** every weekday morning at 06:00 local time. Lightweight
(one HTTP GET per tracked dataset; ~25 requests). Writes a JSON report; no
pipeline run unless a refresh is detected.

**Full refresh:** runs automatically inside the same job whenever detection
flags new data. The orchestrator's per-dataset 5% failure threshold and the
atomic export staging mean a failed run cannot corrupt `build/data/`.

**Why every weekday rather than monthly/quarterly?** CMS publication is the
*upstream* event we react to; the operating cost of polling is tiny. Polling
daily means a real publication is acted on within a day, while polling at
the documented cadence loses up to a month of recency for monthly NH
datasets when CMS slips.

---

## Linux / macOS — cron

Add to the user crontab (`crontab -e`). Set `OPENCHART_DB_URL` and
`REFRESH_NOTIFY_URL` either in the crontab or in a sourced env file.

```cron
# CMS data refresh — weekdays at 06:00 local time
SHELL=/bin/bash
OPENCHART_DB_URL=postgresql+psycopg://postgres:postgres@localhost:5432/openchart
REFRESH_NOTIFY_URL=https://hooks.example.com/openchart-refresh
0 6 * * 1-5 cd /opt/openchart-health && /usr/bin/env python scripts/scheduled_refresh.py >> logs/cron.out 2>&1
```

For weekend coverage during known CMS publication weeks (early
January / April / July / October) extend to `* * 1-5,6,0` or simply run
daily (`0 6 * * *`) — the lock prevents concurrent runs and detection
without changes is a no-op.

Detection-only sanity poll (every two hours during business days):

```cron
0 8-18/2 * * 1-5 cd /opt/openchart-health && /usr/bin/env python scripts/detect_cms_refresh.py >> logs/detect.out 2>&1
```

---

## Windows — Task Scheduler

Create the task with `schtasks` from an elevated PowerShell prompt. Adjust
the working directory and python path as appropriate.

```powershell
$action = New-ScheduledTaskAction `
  -Execute "C:\Users\legion\miniconda3\python.exe" `
  -Argument "scripts\scheduled_refresh.py" `
  -WorkingDirectory "E:\openchart-health"

$trigger = New-ScheduledTaskTrigger -Daily -At 6:00am

$principal = New-ScheduledTaskPrincipal `
  -UserId "$env:USERNAME" -LogonType S4U -RunLevel Limited

$settings = New-ScheduledTaskSettingsSet `
  -StartWhenAvailable `
  -DontStopIfGoingOnBatteries `
  -AllowStartIfOnBatteries `
  -ExecutionTimeLimit (New-TimeSpan -Hours 6) `
  -MultipleInstances IgnoreNew

Register-ScheduledTask `
  -TaskName "OpenChart-CMSRefresh" `
  -Action $action -Trigger $trigger `
  -Principal $principal -Settings $settings `
  -Description "Polls CMS for new dataset vintages, runs pipeline + export when detected"
```

To set environment variables for the task (cron-style env injection isn't
available, so use a wrapper batch file or the user's environment):

```powershell
[Environment]::SetEnvironmentVariable("OPENCHART_DB_URL",
  "postgresql+psycopg://postgres:postgres@localhost:5432/openchart", "User")
[Environment]::SetEnvironmentVariable("REFRESH_NOTIFY_URL",
  "https://hooks.example.com/openchart-refresh", "User")
```

Detection-only secondary task (every 2 hours, business days only) — same
pattern but with `scripts\detect_cms_refresh.py` and a different trigger:

```powershell
$trigger = New-ScheduledTaskTrigger -Once -At 8:00am `
  -RepetitionInterval (New-TimeSpan -Hours 2) `
  -RepetitionDuration (New-TimeSpan -Hours 10)
```

---

## Webhook payload

When `REFRESH_NOTIFY_URL` is set, both success and failure runs POST a
single JSON document. Example success payload:

```json
{
  "tool": "scripts/scheduled_refresh.py",
  "host": "build-01",
  "duration_seconds": 612.4,
  "exit_code": 0,
  "started_at": "2026-05-09T13:00:00+00:00",
  "completed_at": "2026-05-09T13:10:12+00:00",
  "success": true,
  "skipped": false,
  "skip_reason": null,
  "refresh_available_count": 3,
  "pipeline": {
    "rows_upserted": 482910,
    "rows_failed": 0,
    "aborted": false,
    "anomalies_sample": []
  },
  "export_files_written": 21344,
  "ownership_diff_path": "docs/ownership_changes_2026-04_to_2026-05.md",
  "detection_report_path": "logs/cms_refresh_check_2026-05-09.json",
  "log_path": "logs/scheduled_refresh_2026-05-09.log",
  "error": null
}
```

Exit codes:

| Code | Meaning |
|---|---|
| 0 | Success — refreshed or skipped because no new data |
| 1 | Unhandled exception |
| 2 | Detection failed (DB connectivity, etc.) |
| 3 | CMS API errors during detection (refresh skipped to avoid stale ingest) |
| 4 | Pipeline / export raised an exception |
| 5 | Pipeline aborted on Rule 6 (>5% per-dataset failure threshold) |
| 75 | Lock contention — another scheduled_refresh is already running |

---

## Operational checklist

Before enabling the scheduled task in production:

- [ ] Confirm `OPENCHART_DB_URL` points at the production database and the
      account has the migration-applied schema (check
      `pipeline_runs.completed_at` exists).
- [ ] Confirm `REFRESH_NOTIFY_URL` is set (or intentionally absent — the
      script will no-op on absence).
- [ ] Verify `data/` is writable by the scheduled-task account.
- [ ] Verify `build/data/` is writable. The export step performs an atomic
      rename `build/data` → `build/data_previous`, then
      `build/data_staging` → `build/data` (see
      `pipeline/export/build_json.py:1056-1062`). A failed run will leave
      `build/data_previous/` as the most recent successful export — the
      caller restores manually if needed.
- [ ] Run `python scripts/detect_cms_refresh.py --no-db` once to confirm
      DKAN connectivity from the host.
- [ ] Run `python scripts/scheduled_refresh.py --detection-only` once to
      verify lock acquisition + webhook delivery without touching data.

---

## Archive download (TODO — manual step for now)

The detection script captures the `distribution[].downloadURL` for each
dataset and surfaces it in the JSON report. **Automated archive download
into `data/hospitals/` and `data/nursing_homes/` is NOT implemented in
this task.**

Reasons:

1. CMS publishes some datasets only as the live datastore (no zip archive),
   while the historical CSV archives we use for backfill come from a
   separate "topic archive" page (per-provider-type ZIP bundles, not
   per-dataset). The DKAN distribution metadata gives single-dataset CSV
   URLs that don't match the existing
   `hospitals_MM_YYYY/` archive structure.
2. Discovering the canonical "Care Compare data archive" ZIP URL
   programmatically is fragile; CMS rotates filenames and serves them from
   a non-DKAN endpoint.
3. The pipeline tolerates missing archives (`discover_archives()` returns
   what's on disk); a failed download must not block detection.

**Manual step until automated:** when detection flags a refresh, an
operator downloads the appropriate Care Compare archive ZIP from
[data.cms.gov](https://data.cms.gov) and drops it into the matching
directory under `data/`. Naming convention:

- `data/hospitals/hospitals_MM_YYYY/hospitals_MM_YYYY.zip`
- `data/nursing_homes/nursing_homes_including_rehab_services_MM_YYYY/nursing_homes_including_rehab_services_MM_YYYY.zip`

Once the archive is on disk, the next scheduled run picks it up
automatically through `pipeline.ingest.csv_reader.discover_archives()`.

**Follow-up to wire automation:** add an `archive_download.py` step to
`scripts/scheduled_refresh.py` once the canonical archive URL pattern is
documented. The detection report already carries the per-dataset
`download_urls` list, which can serve as the trigger.

---

## Monthly ownership diff

`scripts/check_ownership_changes.py` runs automatically after every
successful refresh that ingests at least two NH archive vintages. The
output goes to `docs/ownership_changes_<previous>_to_<current>.md` (and
the parallel `.json`). When fewer than two vintages exist on disk, the
diff is skipped silently and the schedule logs a note.

The ownership diff is best-effort: a failure does not fail the
scheduled-refresh run. To run it manually:

```bash
python scripts/check_ownership_changes.py --previous 2026-04 --current 2026-05
```

---

## Manual one-off rebuild

To force a full rebuild outside the schedule (e.g. after dropping/recreating
the database):

```bash
python scripts/scheduled_refresh.py --force --skip-ownership-diff
```

`--force` runs the pipeline + export even when no refresh is detected.
`--skip-ownership-diff` is recommended on full rebuilds; the diff is most
informative when it reflects a single CMS refresh, not a complete reload.
