"""
CSV Archive Audit Script — scans all hospital and nursing home CSV vintages for:
1. Unique values in key categorical/sentinel fields across all archives
2. Column header stability across vintages
3. Period ranges across vintages (for longitudinal coverage)
4. Measure ID stability across vintages

Usage: python scripts/csv_audit.py
"""

import csv
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

DATA_DIR = Path("e:/openchart-health/data")

# ---------------------------------------------------------------------------
# Hospital datasets to audit — (filename pattern, key columns to scan)
# ---------------------------------------------------------------------------
HOSPITAL_FILES = {
    "Complications_and_Deaths-Hospital.csv": {
        "categorical": ["Compared to National", "Footnote"],
        "periods": ("Start Date", "End Date"),
        "measure_id": "Measure ID",
    },
    "Healthcare_Associated_Infections-Hospital.csv": {
        "categorical": ["Compared to National", "Footnote"],
        "periods": ("Start Date", "End Date"),
        "measure_id": "Measure ID",
    },
    "Unplanned_Hospital_Visits-Hospital.csv": {
        "categorical": ["Compared to National", "Footnote"],
        "periods": ("Start Date", "End Date"),
        "measure_id": "Measure ID",
    },
    "HCAHPS-Hospital.csv": {
        "categorical": [
            "Patient Survey Star Rating",
            "HCAHPS Answer Percent",
            "HCAHPS Linear Mean Value",
        ],
        "periods": ("Start Date", "End Date"),
        "measure_id": "HCAHPS Measure ID",
    },
    "Timely_and_Effective_Care-Hospital.csv": {
        "categorical": ["Score", "Footnote", "Condition"],
        "periods": ("Start Date", "End Date"),
        "measure_id": "Measure ID",
    },
    "Outpatient_Imaging_Efficiency-Hospital.csv": {
        "categorical": ["Footnote"],
        "periods": ("Start Date", "End Date"),
        "measure_id": "Measure ID",
    },
    "Medicare_Hospital_Spending_Per_Patient-Hospital.csv": {
        "categorical": ["Footnote"],
        "periods": ("Start Date", "End Date"),
        "measure_id": "Measure ID",
    },
    "Hospital_General_Information.csv": {
        "categorical": [
            "Hospital Type",
            "Hospital Ownership",
            "Emergency Services",
            "Hospital overall rating",
            "Hospital overall rating footnote",
            "Meets criteria for birthing friendly designation",
        ],
        "periods": None,
        "measure_id": None,
    },
}

# Nursing home datasets
NH_FILES = {
    "NH_ProviderInfo_*.csv": {
        "match_prefix": "NH_ProviderInfo",
        "categorical": [
            "Ownership Type",
            "Provider Type",
            "Urban",
            "Special Focus Status",
            "Abuse Icon",
            "Continuing Care Retirement Community",
            "Provider Changed Ownership in Last 12 Months",
            "With a Resident and Family Council",
            "Automatic Sprinkler Systems in All Required Areas",
            "Most Recent Health Inspection More Than 2 Years Ago",
        ],
        "periods": None,
        "measure_id": None,
    },
    "NH_QualityMsr_MDS_*.csv": {
        "match_prefix": "NH_QualityMsr_MDS",
        "categorical": [
            "Footnote for Q1 Measure Score",
            "Footnote for Q2 Measure Score",
            "Footnote for Q3 Measure Score",
            "Footnote for Q4 Measure Score",
            "Footnote for Four Quarter Average Score",
            "Used in Quality Measure Five Star Rating",
            "Resident type",
        ],
        "periods": ("Measure Period",),
        "measure_id": "Measure Code",
    },
    "NH_QualityMsr_Claims_*.csv": {
        "match_prefix": "NH_QualityMsr_Claims",
        "categorical": ["Footnote for Score", "Used in Quality Measure Five Star Rating", "Resident type"],
        "periods": ("Measure Period",),
        "measure_id": "Measure Code",
    },
    "NH_HealthCitations_*.csv": {
        "match_prefix": "NH_HealthCitations",
        "categorical": [
            "Survey Type",
            "Scope Severity Code",
            "Deficiency Prefix",
            "Standard Deficiency",
            "Complaint Deficiency",
            "Infection Control Inspection Deficiency",
            "Citation under IDR",
            "Citation under IIDR",
        ],
        "periods": None,
        "measure_id": None,
    },
    "NH_Penalties_*.csv": {
        "match_prefix": "NH_Penalties",
        "categorical": ["Penalty Type"],
        "periods": None,
        "measure_id": None,
    },
}


def find_csv(directory: Path, filename: str, match_prefix: str | None = None) -> Path | None:
    """Find a CSV file by exact name or prefix match."""
    exact = directory / filename
    if exact.exists():
        return exact
    if match_prefix:
        for f in directory.iterdir():
            if f.name.startswith(match_prefix) and f.suffix == ".csv":
                return f
    return None


def scan_categorical(path: Path, columns: list[str]) -> dict[str, Counter]:
    """Return unique value counts for specified columns."""
    results: dict[str, Counter] = {col: Counter() for col in columns}
    with open(path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            for col in columns:
                val = row.get(col, "")
                if val and not _is_pure_numeric(val):
                    results[col][val] += 1
    return results


def scan_periods(path: Path, period_cols: tuple) -> Counter:
    """Return unique period combinations."""
    periods: Counter = Counter()
    with open(path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = tuple(row.get(c, "") for c in period_cols)
            periods[key] += 1
    return periods


def scan_measure_ids(path: Path, measure_col: str) -> set[str]:
    """Return unique measure IDs."""
    ids: set[str] = set()
    with open(path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            mid = row.get(measure_col, "")
            if mid:
                ids.add(mid)
    return ids


def get_headers(path: Path) -> list[str]:
    """Return column headers."""
    with open(path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames or [])


def _is_pure_numeric(val: str) -> bool:
    """Check if value is purely numeric (including decimals/negatives)."""
    try:
        float(val)
        return True
    except ValueError:
        return False


def audit_dataset(
    name: str,
    spec: dict,
    directories: list[tuple[str, Path]],
) -> None:
    """Audit one dataset across all archive directories."""
    print(f"\n{'='*80}")
    print(f"  {name}")
    print(f"{'='*80}")

    match_prefix = spec.get("match_prefix")

    # 1. Header stability
    all_headers: dict[str, list[str]] = {}
    for label, directory in directories:
        path = find_csv(directory, name, match_prefix)
        if path:
            all_headers[label] = get_headers(path)

    if len(all_headers) > 1:
        labels = list(all_headers.keys())
        base_label, base_headers = labels[0], set(all_headers[labels[0]])
        for label in labels[1:]:
            other = set(all_headers[label])
            added = other - base_headers
            removed = base_headers - other
            if added or removed:
                print(f"\n  HEADER CHANGES: {base_label} -> {label}")
                if added:
                    print(f"    Added: {added}")
                if removed:
                    print(f"    Removed: {removed}")
        if all(set(all_headers[l]) == base_headers for l in labels[1:]):
            print(f"\n  Headers: STABLE across {len(all_headers)} vintages ({len(base_headers)} columns)")

    # 2. Categorical unique values
    if spec.get("categorical"):
        print(f"\n  --- Unique Categorical Values ---")
        all_vals: dict[str, dict[str, Counter]] = {}
        for label, directory in directories:
            path = find_csv(directory, name, match_prefix)
            if path:
                all_vals[label] = scan_categorical(path, spec["categorical"])

        for col in spec["categorical"]:
            # Merge across all vintages
            merged: Counter = Counter()
            per_vintage: dict[str, Counter] = {}
            for label in all_vals:
                per_vintage[label] = all_vals[label].get(col, Counter())
                merged.update(per_vintage[label])

            if merged:
                print(f"\n  {col}:")
                for val, count in merged.most_common(30):
                    # Show which vintages have this value
                    presence = []
                    for label in all_vals:
                        c = per_vintage[label].get(val, 0)
                        if c:
                            presence.append(f"{label}:{c:,}")
                    print(f"    {val!r:65s} total={count:>9,}  [{', '.join(presence)}]")

    # 3. Period ranges
    if spec.get("periods"):
        print(f"\n  --- Reporting Periods ---")
        for label, directory in directories:
            path = find_csv(directory, name, match_prefix)
            if path:
                periods = scan_periods(path, spec["periods"])
                print(f"\n  {label}:")
                for period, count in periods.most_common(15):
                    print(f"    {period}: {count:,} rows")

    # 4. Measure ID stability
    if spec.get("measure_id"):
        print(f"\n  --- Measure IDs ---")
        all_ids: dict[str, set[str]] = {}
        for label, directory in directories:
            path = find_csv(directory, name, match_prefix)
            if path:
                all_ids[label] = scan_measure_ids(path, spec["measure_id"])

        labels = list(all_ids.keys())
        if len(labels) > 1:
            union = set()
            for ids in all_ids.values():
                union.update(ids)
            print(f"  Total unique measure IDs across all vintages: {len(union)}")

            # Find IDs present in some but not all
            for mid in sorted(union):
                present_in = [l for l in labels if mid in all_ids[l]]
                if len(present_in) < len(labels):
                    missing_from = [l for l in labels if mid not in all_ids[l]]
                    print(f"    {mid}: present in {present_in}, MISSING from {missing_from}")


def main():
    # Discover all hospital directories
    hosp_base = DATA_DIR / "hospitals"
    hosp_dirs: list[tuple[str, Path]] = [("current", hosp_base)]
    for d in sorted(hosp_base.iterdir()):
        if d.is_dir() and d.name.startswith("hospitals_"):
            hosp_dirs.append((d.name, d))

    # Discover all NH directories
    nh_base = DATA_DIR / "nursing_homes"
    nh_dirs: list[tuple[str, Path]] = [("current", nh_base)]
    for d in sorted(nh_base.iterdir()):
        if d.is_dir():
            nh_dirs.append((d.name, d))

    print("Hospital directories:", [l for l, _ in hosp_dirs])
    print("Nursing home directories:", [l for l, _ in nh_dirs])

    print("\n" + "#" * 80)
    print("# HOSPITAL DATASETS")
    print("#" * 80)

    for name, spec in HOSPITAL_FILES.items():
        audit_dataset(name, spec, hosp_dirs)

    print("\n" + "#" * 80)
    print("# NURSING HOME DATASETS")
    print("#" * 80)

    for name, spec in NH_FILES.items():
        audit_dataset(name, spec, nh_dirs)


if __name__ == "__main__":
    main()
