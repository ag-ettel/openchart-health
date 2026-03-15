"""
Phase 0 reconnaissance: confirm Socrata dataset IDs for all CMS hospital datasets.

Queries the CMS Provider Data API (DKAN-based, data.cms.gov/provider-data/api/1/)
to locate each dataset by name, confirms the dataset ID, fetches the total row count,
and prints a summary.

NOTE: The old Socrata API (data.cms.gov/api/views/) returned 410 Gone as of 2026.
This script uses the new Provider Data DKAN API exclusively.

Throwaway script. Do not import from pipeline modules. Archive when Phase 0 closes.
"""

import json
import time
import urllib.error
import urllib.parse
import urllib.request

PROVIDER_DATA_API = "https://data.cms.gov/provider-data/api/1"

# Candidate IDs were confirmed via catalog search against live API on 2026-03-14.
# Entries marked SEARCH_REQUIRED have no reliable candidate and require catalog search.
# NOTE: "Hospital Overall Star Rating" is NOT a separate dataset: the
# hospital_overall_rating field lives in Hospital General Information (xubh-q36u).
DATASETS = [
    {
        "name": "Hospital General Information",
        "candidate_id": "xubh-q36u",
        "search_terms": "hospital general information",
        "notes": "Also contains hospital_overall_rating — star rating is not a separate dataset.",
    },
    {
        "name": "Hospital Overall Star Rating",
        "candidate_id": None,  # Not a separate dataset; field in xubh-q36u
        "search_terms": "hospital overall star rating",
        "notes": "EXPECTED MISSING: star rating is a column in Hospital General Information (xubh-q36u), not a standalone dataset.",
    },
    {
        "name": "Timely and Effective Care",
        "candidate_id": "yv7e-xc69",
        "search_terms": "timely and effective care hospital",
        "notes": "",
    },
    {
        "name": "HCAHPS Patient Survey",
        "candidate_id": "dgck-syfz",
        "search_terms": "HCAHPS patient survey hospital",
        "notes": "",
    },
    {
        "name": "Complications and Deaths",
        "candidate_id": "ynj2-r877",
        "search_terms": "complications and deaths hospital",
        "notes": "",
    },
    {
        "name": "Healthcare-Associated Infections (HAI)",
        "candidate_id": "77hc-ibv8",
        "search_terms": "healthcare associated infections hospital",
        "notes": "",
    },
    {
        "name": "Unplanned Hospital Visits (Readmissions)",
        "candidate_id": "632h-zaca",
        "search_terms": "unplanned hospital visits",
        "notes": "",
    },
    {
        "name": "Outpatient Imaging Efficiency",
        "candidate_id": "wkfw-kthe",
        "search_terms": "outpatient imaging efficiency",
        "notes": "Old candidate was wkfw-k4wr; updated to wkfw-kthe from catalog search.",
    },
    {
        "name": "Medicare Hospital Spending Per Patient",
        "candidate_id": "rrqw-56er",
        "search_terms": "medicare spending per beneficiary hospital",
        "notes": "Old candidate was nrth-mfbm; CMS title is 'Medicare Spending Per Beneficiary'.",
    },
    {
        "name": "Payment and Value of Care",
        "candidate_id": None,  # No exact dataset found; may be split across VBP tables
        "search_terms": "payment value of care hospital",
        "notes": "EXPECTED MISSING: no single dataset by this name found. Closest are VBP program tables. Needs pipeline_decisions.md entry.",
    },
    {
        "name": "Health Equity Summary",
        "candidate_id": None,  # Not found in current catalog
        "search_terms": "health equity hospital",
        "notes": "EXPECTED MISSING: no hospital-level health equity dataset found in current catalog. Needs pipeline_decisions.md entry.",
    },
    {
        "name": "Hospital Readmissions Reduction Program (HRRP)",
        "candidate_id": "9n3s-kdb3",
        "search_terms": "hospital readmissions reduction program",
        "notes": "",
    },
    {
        "name": "Hospital-Acquired Condition Reduction Program (HACRP)",
        "candidate_id": "yq43-i98g",
        "search_terms": "hospital acquired condition reduction",
        "notes": "",
    },
    {
        "name": "Hospital Value-Based Purchasing Program (VBP)",
        "candidate_id": "ypbt-wvdk",
        "search_terms": "hospital value based purchasing",
        "notes": "",
    },
]


def fetch_json(url: str, timeout: int = 30) -> dict | list | None:
    """Fetch JSON from a URL, returning None with printed error on any failure."""
    try:
        req = urllib.request.Request(
            url, headers={"Accept": "application/json", "User-Agent": "openchart-recon/0.1"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        print(f"   HTTP {exc.code}: {url}")
        return None
    except urllib.error.URLError as exc:
        print(f"   URLError ({exc.reason}): {url}")
        return None
    except Exception as exc:
        print(f"   Error ({type(exc).__name__}: {exc}): {url}")
        return None


def verify_and_count(dataset_id: str) -> tuple[bool, int | None]:
    """
    Verify a dataset ID exists and return its row count.
    Uses the DKAN datastore query endpoint with count=true.
    Returns (exists, row_count). row_count is None on failure.
    """
    url = f"{PROVIDER_DATA_API}/datastore/query/{dataset_id}/0?limit=1&count=true"
    data = fetch_json(url, timeout=30)
    if data is None:
        return False, None
    if isinstance(data, dict) and "count" in data:
        try:
            return True, int(data["count"])
        except (ValueError, TypeError):
            return True, None
    # Dataset exists but response format unexpected
    return True, None


def search_catalog(search_terms: str, limit: int = 5) -> list[dict]:
    """
    Search the CMS Provider Data catalog for datasets matching the given terms.
    Returns a list of result entries (may be empty).
    """
    params = urllib.parse.urlencode({"fulltext": search_terms, "limit": limit})
    url = f"{PROVIDER_DATA_API}/search?{params}"
    data = fetch_json(url, timeout=20)
    if not data:
        return []
    # Results is a dict keyed by "dkan_dataset/{id}"
    raw_results = data.get("results", {})
    if isinstance(raw_results, dict):
        return list(raw_results.values())
    if isinstance(raw_results, list):
        return raw_results
    return []


def run() -> None:
    print("=" * 78)
    print("CMS Hospital Dataset ID Confirmation -- Phase 0 Reconnaissance")
    print(f"Provider Data API: {PROVIDER_DATA_API}")
    print("Run date: 2026-03-14")
    print("=" * 78)
    print()

    results = []

    for ds in DATASETS:
        name = ds["name"]
        candidate_id = ds["candidate_id"]
        notes = ds["notes"]

        print(f"-- {name}")

        if candidate_id is None:
            print(f"   Candidate ID  : none (expected to be missing or split)")
            if notes:
                print(f"   Note          : {notes}")
            # Still try a search to see if anything comes up
            print(f"   Searching catalog for: {ds['search_terms']!r}")
            search_results = search_catalog(ds["search_terms"])
            time.sleep(0.4)
            if search_results:
                print(f"   Search found  : {len(search_results)} result(s)")
                for r in search_results[:3]:
                    title = r.get("title", r.get("name", "?"))
                    rid = r.get("identifier", r.get("id", "?"))
                    print(f"     - {rid}: {title}")
            else:
                print(f"   Search found  : none -- confirmed absent from current catalog")
            print(f"   Status        : DOCUMENTED MISSING -- needs pipeline_decisions.md entry")
            print()
            results.append({
                "name": name,
                "candidate_id": "N/A",
                "confirmed_id": "NOT IN CATALOG",
                "confirmed_name": None,
                "row_count": None,
                "resource_url": "N/A",
                "status": "MISSING",
                "notes": notes,
            })
            continue

        print(f"   Candidate ID  : {candidate_id}")

        # Step 1: verify candidate and get row count directly
        exists, row_count = verify_and_count(candidate_id)
        time.sleep(0.4)

        if exists:
            resource_url = f"{PROVIDER_DATA_API}/datastore/query/{candidate_id}/0"
            row_str = f"{row_count:,}" if row_count is not None else "UNKNOWN"
            print(f"   Candidate verified via datastore query.")
            print(f"   Row count     : {row_str}")
            print(f"   Resource URL  : {resource_url}")
            if notes:
                print(f"   Note          : {notes}")
            print(f"   Status        : OK")
            print()
            results.append({
                "name": name,
                "candidate_id": candidate_id,
                "confirmed_id": candidate_id,
                "confirmed_name": None,
                "row_count": row_count,
                "resource_url": resource_url,
                "status": "OK",
                "notes": notes,
            })
        else:
            # Fall back to catalog search
            print(f"   Candidate not verified. Searching catalog for: {ds['search_terms']!r}")
            search_results = search_catalog(ds["search_terms"])
            time.sleep(0.4)

            found_id = None
            found_name = None
            if search_results:
                top = search_results[0]
                found_id = top.get("identifier") or top.get("id")
                found_name = top.get("title") or top.get("name", "")
                print(f"   Top search result: {found_id}: {found_name}")
                if len(search_results) > 1:
                    print(f"   ({len(search_results) - 1} additional result(s) -- review manually)")
            else:
                print(f"   No results found in catalog.")

            if found_id and found_id != candidate_id:
                # Verify the search result
                exists2, row_count2 = verify_and_count(found_id)
                time.sleep(0.4)
                if exists2:
                    resource_url = f"{PROVIDER_DATA_API}/datastore/query/{found_id}/0"
                    row_str = f"{row_count2:,}" if row_count2 is not None else "UNKNOWN"
                    print(f"   ID MISMATCH: candidate={candidate_id} -> actual={found_id}")
                    print(f"   Row count     : {row_str}")
                    print(f"   Resource URL  : {resource_url}")
                    if notes:
                        print(f"   Note          : {notes}")
                    print(f"   Status        : NEEDS REVIEW (ID was wrong)")
                    print()
                    results.append({
                        "name": name,
                        "candidate_id": candidate_id,
                        "confirmed_id": found_id,
                        "confirmed_name": found_name,
                        "row_count": row_count2,
                        "resource_url": resource_url,
                        "status": "NEEDS REVIEW",
                        "notes": notes,
                    })
                    continue

            print(f"   WARNING: could not confirm any ID for this dataset.")
            if notes:
                print(f"   Note          : {notes}")
            print(f"   Status        : NEEDS MANUAL LOOKUP")
            print()
            results.append({
                "name": name,
                "candidate_id": candidate_id,
                "confirmed_id": "NOT FOUND",
                "confirmed_name": None,
                "row_count": None,
                "resource_url": "N/A",
                "status": "NEEDS MANUAL LOOKUP",
                "notes": notes,
            })

    # Summary table
    print("=" * 78)
    print("SUMMARY")
    print("=" * 78)
    col_w = 48
    print(f"{'Dataset':<{col_w}}  {'Confirmed ID':<12}  {'Rows':>10}  Status")
    print("-" * 78)
    for r in results:
        row_str = f"{r['row_count']:,}" if r["row_count"] is not None else "---"
        print(f"{r['name']:<{col_w}}  {r['confirmed_id']:<12}  {row_str:>10}  {r['status']}")

    print()
    ok = [r for r in results if r["status"] == "OK"]
    missing = [r for r in results if r["status"] == "MISSING"]
    problem = [r for r in results if r["status"] not in ("OK", "MISSING")]

    print(f"Confirmed OK     : {len(ok)}")
    print(f"Documented missing (expected): {len(missing)}")
    print(f"Need attention   : {len(problem)}")
    if problem:
        print()
        print("Datasets requiring follow-up:")
        for r in problem:
            print(f"  [{r['status']}] {r['name']}")
            if r["notes"]:
                print(f"    Note: {r['notes']}")
    if missing:
        print()
        print("Documented missing -- add pipeline_decisions.md entries for:")
        for r in missing:
            print(f"  {r['name']}")
            if r["notes"]:
                print(f"    {r['notes']}")


if __name__ == "__main__":
    run()
