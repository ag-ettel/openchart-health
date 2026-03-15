"""
Phase 0 reconnaissance: pull sample rows from each confirmed CMS hospital dataset.

For each dataset with a confirmed Socrata/DKAN ID, fetches at least 200 rows using
a minimum of two paginated requests (100 rows per page). Saves the combined raw JSON
response to scripts/recon/raw_samples/{dataset_id}.json and prints the field names
present in each response.

Throwaway script. Do not import from pipeline modules. Archive when Phase 0 closes.

Dataset IDs sourced from confirm_dataset_ids.py run on 2026-03-14.
"""

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

PROVIDER_DATA_API = "https://data.cms.gov/provider-data/api/1"

USER_AGENT = (
    "openchart-health-phase0-recon/0.1 "
    "(CMS hospital quality aggregator; Phase 0 sample pull; "
    "contact: openchart-health project)"
)

# Confirmed IDs from confirm_dataset_ids.py run 2026-03-14.
# Star Rating is a field in xubh-q36u, not a separate dataset.
# Payment & Value of Care and Health Equity have no current catalog entry.
DATASETS = [
    {
        "name": "Hospital General Information",
        "dataset_id": "xubh-q36u",
        "notes": "Contains hospital_overall_rating (star rating). Pull 1000 rows — "
                 "this is the provider master table and we want good coverage of "
                 "provider_subtype values.",
        "target_rows": 1000,
    },
    {
        "name": "Timely and Effective Care",
        "dataset_id": "yv7e-xc69",
        "notes": "Multi-measure dataset; high row count expected.",
        "target_rows": 1000,
    },
    {
        "name": "HCAHPS Patient Survey",
        "dataset_id": "dgck-syfz",
        "notes": "Expanded to 2000 rows to find suppressed/footnote rows. "
                 "200-row sample had only 3 hospitals; footnote rows were absent.",
        "target_rows": 2000,
    },
    {
        "name": "Complications and Deaths",
        "dataset_id": "ynj2-r877",
        "notes": "Tail-risk measures. Expect suppressed rows.",
        "target_rows": 1000,
    },
    {
        "name": "Healthcare-Associated Infections (HAI)",
        "dataset_id": "77hc-ibv8",
        "notes": "Tail-risk measures. Expect suppressed rows.",
        "target_rows": 1000,
    },
    {
        "name": "Unplanned Hospital Visits (Readmissions)",
        "dataset_id": "632h-zaca",
        "notes": "SES-sensitive measures.",
        "target_rows": 1000,
    },
    {
        "name": "Outpatient Imaging Efficiency",
        "dataset_id": "wkfw-kthe",
        "notes": "",
        "target_rows": 1000,
    },
    {
        "name": "Medicare Hospital Spending Per Patient",
        "dataset_id": "rrqw-56er",
        "notes": "CMS title is 'Medicare Spending Per Beneficiary'.",
        "target_rows": 1000,
    },
    {
        "name": "Hospital Readmissions Reduction Program (HRRP)",
        "dataset_id": "9n3s-kdb3",
        "notes": "Payment adjustment program.",
        "target_rows": 1000,
    },
    {
        "name": "Hospital-Acquired Condition Reduction Program (HACRP)",
        "dataset_id": "yq43-i98g",
        "notes": "Payment adjustment program.",
        "target_rows": 1000,
    },
    {
        "name": "Hospital Value-Based Purchasing Program (VBP)",
        "dataset_id": "ypbt-wvdk",
        "notes": "Payment adjustment program.",
        "target_rows": 1000,
    },
]

PAGE_SIZE = 100
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "raw_samples")


def fetch_json(url: str, timeout: int = 60) -> dict | list | None:
    """Fetch JSON from a URL, returning None with printed error on any failure."""
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = ""
        try:
            body = exc.read(500).decode("utf-8", errors="replace")
        except Exception:
            pass
        print(f"   HTTP {exc.code}: {url}")
        if body:
            print(f"   Response body (first 500 chars): {body[:500]}")
        return None
    except urllib.error.URLError as exc:
        print(f"   URLError ({exc.reason}): {url}")
        return None
    except Exception as exc:
        print(f"   Error ({type(exc).__name__}: {exc}): {url}")
        return None


def fetch_page(dataset_id: str, offset: int, limit: int) -> dict | None:
    """
    Fetch one page from the DKAN datastore query endpoint.

    Returns the raw response dict, or None on failure.
    """
    params = urllib.parse.urlencode({
        "limit": limit,
        "offset": offset,
        "count": "true",
    })
    url = f"{PROVIDER_DATA_API}/datastore/query/{dataset_id}/0?{params}"
    return fetch_json(url)


def pull_dataset(dataset_id: str, dataset_name: str, target_rows: int, notes: str) -> dict:
    """
    Pull at least target_rows rows from a dataset using paginated requests.

    Guarantees at least two separate HTTP requests regardless of target_rows.
    Returns a result dict suitable for JSON serialisation.
    """
    print(f"\n{'=' * 70}")
    print(f"Dataset : {dataset_name}")
    print(f"ID      : {dataset_id}")
    if notes:
        print(f"Notes   : {notes}")
    print(f"Target  : {target_rows} rows ({PAGE_SIZE} rows/page, "
          f"min 2 pages)")

    pages_raw = []
    all_rows: list[dict] = []
    total_count: int | None = None
    offset = 0
    page_num = 0

    # Always fetch at least 2 pages; continue until we have target_rows or exhaust
    while True:
        page_num += 1
        limit = PAGE_SIZE
        print(f"   Page {page_num}: offset={offset}, limit={limit} ... ", end="", flush=True)

        response = fetch_page(dataset_id, offset, limit)
        if response is None:
            print("FAILED")
            break

        # DKAN returns {"count": N, "results": [...]}
        rows = response.get("results", [])
        if total_count is None:
            try:
                total_count = int(response.get("count", 0))
            except (ValueError, TypeError):
                total_count = None

        count_str = f"{total_count:,}" if total_count is not None else "?"
        print(f"got {len(rows)} rows (total in dataset: {count_str})")

        pages_raw.append({
            "page": page_num,
            "offset": offset,
            "limit": limit,
            "rows_returned": len(rows),
            "results": rows,
        })
        all_rows.extend(rows)
        offset += len(rows)

        # Stop conditions:
        # 1. We fetched fewer rows than requested (end of dataset)
        if len(rows) < limit:
            if page_num < 2:
                # Haven't hit our minimum of 2 pages yet — try one more
                print(f"   End of data after page {page_num} but minimum 2 pages "
                      f"required; attempting page {page_num + 1}.")
                offset = len(all_rows)  # already at end but try anyway
                continue
            print(f"   End of data reached after {page_num} page(s).")
            break
        # 2. We have enough rows AND have done at least 2 pages
        if len(all_rows) >= target_rows and page_num >= 2:
            break

        time.sleep(0.35)  # polite delay between requests

    # Collect field names from the first non-empty row
    fields: list[str] = []
    for row in all_rows:
        if isinstance(row, dict) and row:
            fields = sorted(row.keys())
            break

    print(f"   Total rows fetched   : {len(all_rows)}")
    print(f"   Pages requested      : {page_num}")
    print(f"   Fields ({len(fields)}) : {', '.join(fields)}")

    return {
        "dataset_id": dataset_id,
        "dataset_name": dataset_name,
        "notes": notes,
        "total_count_reported": total_count,
        "rows_fetched": len(all_rows),
        "pages_requested": page_num,
        "field_names": fields,
        "pages": pages_raw,
    }


def run() -> None:
    print("=" * 70)
    print("CMS Hospital Dataset Sample Pull — Phase 0 Reconnaissance")
    print(f"API: {PROVIDER_DATA_API}")
    print(f"Output dir: {OUTPUT_DIR}")
    print(f"User-Agent: {USER_AGENT}")
    print(f"Run date: 2026-03-14")
    print("=" * 70)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    summary: list[dict] = []

    for ds in DATASETS:
        dataset_id = ds["dataset_id"]
        dataset_name = ds["name"]
        target_rows = ds["target_rows"]
        notes = ds["notes"]

        result = pull_dataset(dataset_id, dataset_name, target_rows, notes)

        # Save raw output
        out_path = os.path.join(OUTPUT_DIR, f"{dataset_id}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"   Saved: {out_path}")

        summary.append({
            "name": dataset_name,
            "dataset_id": dataset_id,
            "rows_fetched": result["rows_fetched"],
            "pages": result["pages_requested"],
            "field_count": len(result["field_names"]),
            "ok": result["rows_fetched"] > 0,
        })

        time.sleep(0.5)

    # Final summary
    print(f"\n{'=' * 70}")
    print("SUMMARY")
    print(f"{'=' * 70}")
    col = 45
    print(f"{'Dataset':<{col}}  {'ID':<12}  {'Rows':>6}  {'Pages':>5}  {'Fields':>6}  OK?")
    print("-" * 70)
    for s in summary:
        ok_str = "YES" if s["ok"] else "FAIL"
        print(
            f"{s['name']:<{col}}  {s['dataset_id']:<12}  "
            f"{s['rows_fetched']:>6}  {s['pages']:>5}  {s['field_count']:>6}  {ok_str}"
        )

    failed = [s for s in summary if not s["ok"]]
    print(f"\nTotal datasets attempted : {len(summary)}")
    print(f"Successful               : {len(summary) - len(failed)}")
    print(f"Failed                   : {len(failed)}")
    if failed:
        print("\nFailed datasets:")
        for s in failed:
            print(f"  {s['dataset_id']}  {s['name']}")


if __name__ == "__main__":
    run()
