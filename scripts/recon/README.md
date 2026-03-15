# scripts/recon/

**All files in this directory are throwaway Phase 0 reconnaissance code.**

These scripts exist solely to confirm CMS API field names, suppression encodings,
footnote structures, dataset IDs, and row samples against live API responses.

## Rules

- **Do not import any file from this directory into pipeline modules.** Ever.
- Scripts here are not held to production code standards (typing, tests, docstrings).
- All scripts must be archived or deleted when Phase 0 closes.
- If you add a script, note its purpose in the table below.

## Scripts

| File | Purpose | Status |
|------|---------|--------|
| `confirm_dataset_ids.py` | Confirm Socrata dataset IDs for all 14 hospital datasets against the live CMS Provider Data Catalog API; prints confirmed ID, row count, and resource URL per dataset | Active |

## Phase 0 Outputs

Findings from these scripts are recorded in:
- `docs/phase_0_findings.md` — confirmed dataset IDs, field names, suppression encodings, footnote structures, refresh schedules
- `tests/pipeline/fixtures/hospital/` — representative raw API response samples (≥100 rows per dataset)
