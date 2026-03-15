"""
Recon script: analyze suppression encodings, footnote formats, and missingness
across all raw CMS sample files in scripts/recon/raw_samples/.

Phase 0 throwaway code — do not import from pipeline modules.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from collections import defaultdict
from typing import Any

RAW_SAMPLES_DIR = Path(__file__).parent / "raw_samples"

# Known CMS suppression indicators to scan for.
# "number of cases too small" appears in compared_to_national (Complications dataset).
# "too few to report" appears in number_of_readmissions (HRRP dataset).
# Both are confirmed suppression signals — confirmed 2026-03-14 via manual row inspection.
#
# "n/a" is confirmed as the suppression sentinel in HACRP (yq43-i98g) across all SIR
# fields and total_hac_score — this dataset does NOT use "Not Available". Confirmed in
# 1000-row sample 2026-03-14. "n/a" also appears in HRRP (9n3s-kdb3) for fully
# suppressed rows, and in HAI (77hc-ibv8) for CI sub-measures (CILOWER/CIUPPER) where
# zero infections were observed (footnote 8 = "no cases meeting inclusion criteria").
# The HAI "N/A" + footnote 8 case is semantically distinct from suppression — the
# hospital was evaluated but the CI bound is mathematically undefined. The normalizer
# must handle this as a separate state. See fixture_gaps.md §77hc-ibv8.
#
# NOTE on not_reported vs suppressed: footnote code "19" (results cannot be calculated
# for this reporting period) represents a distinct not_reported state, separate from
# standard suppression (footnote "1" = too few cases, footnote "5" = not participating).
# Confirmed present in xubh-q36u (Rural Emergency Hospitals), wkfw-kthe (48/1000 rows),
# rrqw-56er (37/1000 rows). The normalize layer must store these as distinct states.
SUPPRESSION_STRING_INDICATORS: set[str] = {
    "not available",
    "not applicable",
    "n/a",
    "*",
    "",
    "none",
    "–",
    "-",
    "null",
    "number of cases too small",
    "too few to report",
}

SUPPRESSION_NUMERIC_SENTINELS: set[float] = {-1.0, 999.0, 9999.0, 99999.0}

# Footnote delimiter patterns.
# CMS uses comma-space (", ") as the multi-code delimiter in API responses —
# confirmed in HAI (77hc-ibv8) and Timely & Effective Care (yv7e-xc69) samples
# (e.g., "3, 13", "2, 3, 29"). Pipe ("|") has not been observed in any sample.
COMMA_FOOTNOTE_RE = re.compile(r"^\d+(?:,\s*\d+)+$")   # "1, 3", "1, 28", "3, 13", "8, 29", "13, 29", "1, 3, 29"
PIPE_FOOTNOTE_RE = re.compile(r"^\d+(?:\|\d+)+$")       # "3|13" (not yet observed in any 1000-row sample)
# Matches a single integer string
INT_RE = re.compile(r"^\d+$")

# Fields that look numeric but are NOT footnote fields — skip from footnote detection
NON_FOOTNOTE_NUMERIC_FIELDS: set[str] = {
    "facility_id", "provider_id", "ccn", "zip_code", "zip",
    "telephone_number", "fiscal_year", "payment_year",
    "number_of_discharges", "number_of_readmissions",
    "number_of_patients", "number_of_patients_returned",
    "number_of_completed_surveys", "survey_response_rate_percent",
    "mort_group_measure_count", "safety_group_measure_count",
    "readm_group_measure_count", "pt_exp_group_measure_count",
    "te_group_measure_count",
    "count_of_facility_mort_measures", "count_of_facility_safety_measures",
    "count_of_facility_readm_measures", "count_of_facility_pt_exp_measures",
    "count_of_facility_te_measures",
}


def load_rows(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Load metadata and flattened row list from a raw sample file."""
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    for page in data.get("pages", []):
        rows.extend(page.get("results", []))
    return data, rows


def is_suppression_value(value: Any) -> bool:
    """Return True if value matches a known CMS suppression indicator."""
    if value is None:
        return True
    if isinstance(value, str) and value.strip().lower() in SUPPRESSION_STRING_INDICATORS:
        return True
    if isinstance(value, (int, float)):
        try:
            if float(value) in SUPPRESSION_NUMERIC_SENTINELS:
                return True
        except (ValueError, TypeError):
            pass
    return False


def classify_footnote_format(values: list[Any]) -> str | None:
    """
    Given the non-null values from a field, return the likely footnote format:
    'array', 'comma_delimited', 'pipe_delimited', 'single_integer', or None.

    CMS API footnote delimiter is comma-space (', ') — confirmed in HAI and T&E
    samples (e.g., "3, 13", "2, 3, 29"). Pipe has not been observed.
    """
    non_empty = [v for v in values if v is not None and v != ""]
    if not non_empty:
        return None
    if any(isinstance(v, list) for v in non_empty):
        return "array"
    if all(isinstance(v, str) for v in non_empty):
        has_comma = sum(1 for v in non_empty if COMMA_FOOTNOTE_RE.match(v.strip()))
        has_pipe = sum(1 for v in non_empty if "|" in v)
        all_int = sum(1 for v in non_empty if INT_RE.match(v.strip()))
        all_pipe = sum(1 for v in non_empty if PIPE_FOOTNOTE_RE.match(v.strip()))
        if has_comma > 0:
            # Mixed single + comma-delimited codes — report as comma_delimited
            return "comma_delimited"
        if has_pipe > 0:
            return "pipe_delimited"
        if all_int == len(non_empty):
            return "single_integer"
        if all_pipe == len(non_empty):
            return "pipe_delimited"
    return None


def looks_like_footnote_field(field_name: str, values: list[Any]) -> bool:
    """Heuristic: field name contains 'footnote' or values look like footnote codes."""
    if field_name.lower() in NON_FOOTNOTE_NUMERIC_FIELDS:
        return False
    if "footnote" in field_name.lower():
        return True
    # Only flag non-named fields if they have content that looks like codes
    # and the field name suggests it might carry supplementary info
    fmt = classify_footnote_format(values)
    return fmt in ("single_integer", "pipe_delimited", "comma_delimited", "array")


def analyze_dataset(path: Path) -> None:
    meta, rows = load_rows(path)
    dataset_id: str = meta.get("dataset_id", path.stem)
    dataset_name: str = meta.get("dataset_name", "")
    total_rows = len(rows)

    print(f"\n{'=' * 72}")
    print(f"DATASET: {dataset_id}  —  {dataset_name}")
    print(f"  Rows in sample: {total_rows}  |  Total in dataset: {meta.get('total_count_reported', '?')}")
    print(f"{'=' * 72}")

    if total_rows == 0:
        print("  (no rows — skipping)")
        return

    all_fields = list(rows[0].keys()) if rows else meta.get("field_names", [])

    # ── 1. Suppression indicators per field ──────────────────────────────────
    # Map: field -> {indicator_string -> count}
    suppression_hits: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    null_counts: dict[str, int] = defaultdict(int)

    for row in rows:
        for field in all_fields:
            val = row.get(field)
            if val is None:
                null_counts[field] += 1
                suppression_hits[field]["(null/missing)"] += 1
            elif isinstance(val, str) and val.strip().lower() in SUPPRESSION_STRING_INDICATORS:
                key = repr(val) if val == "" else val.strip()
                suppression_hits[field][key] += 1
            elif isinstance(val, (int, float)):
                try:
                    if float(val) in SUPPRESSION_NUMERIC_SENTINELS:
                        suppression_hits[field][str(val)] += 1
                except (ValueError, TypeError):
                    pass

    # ── 2. Footnote field detection ──────────────────────────────────────────
    footnote_fields: dict[str, str] = {}
    for field in all_fields:
        values = [row.get(field) for row in rows]
        if looks_like_footnote_field(field, values):
            fmt = classify_footnote_format([v for v in values if v is not None and v != ""])
            footnote_fields[field] = fmt or "unknown"

    # ── 3. Fields with partial missingness ───────────────────────────────────
    partial_missing: dict[str, tuple[int, float]] = {}
    for field in all_fields:
        count = null_counts.get(field, 0)
        # Also count empty strings as missing for display
        empty_count = sum(
            1 for row in rows
            if row.get(field) is None or (isinstance(row.get(field), str) and row[field].strip() == "")
        )
        if 0 < empty_count < total_rows:
            partial_missing[field] = (empty_count, empty_count / total_rows)

    # ── 4. Example rows ──────────────────────────────────────────────────────
    example_suppressed: dict[str, Any] | None = None
    example_not_reported: dict[str, Any] | None = None
    example_footnote: dict[str, Any] | None = None

    # NOTE: "not_reported" here is a heuristic based on value strings alone. In this
    # project, the true not_reported/suppressed distinction is determined by footnote
    # code semantics, not raw values (e.g., footnote 19 vs footnote 1 both co-occur
    # with score = "Not Available"). The example rows printed below show rows that
    # CONTAIN any of these phrases, not rows verified to be in a not_reported state.
    not_reported_phrases = {"not available", "not applicable", "n/a"}

    for row in rows:
        vals = list(row.values())
        str_vals_lower = [str(v).strip().lower() for v in vals if v is not None]

        if example_not_reported is None and any(v in not_reported_phrases for v in str_vals_lower):
            example_not_reported = row

        if example_suppressed is None and any(
            (isinstance(v, str) and v.strip() == "*") or v == "" for v in vals
        ):
            # Prefer rows where star (*) appears
            if any(isinstance(v, str) and v.strip() == "*" for v in vals):
                example_suppressed = row
            elif example_suppressed is None:
                example_suppressed = row  # empty string counts too

        if example_footnote is None and footnote_fields:
            # Prefer fields whose name contains "footnote" to avoid false positives
            named_fn_fields = [f for f in footnote_fields if "footnote" in f.lower()]
            candidate_fields = named_fn_fields or list(footnote_fields.keys())
            for fn_field in candidate_fields:
                v = row.get(fn_field)
                if v is not None and str(v).strip() not in ("", "0"):
                    example_footnote = row
                    break

    # ─── Print Results ───────────────────────────────────────────────────────

    # Suppression summary
    print("\n  [1] SUPPRESSION INDICATORS")
    fields_with_suppression = {f: d for f, d in suppression_hits.items() if d}
    if not fields_with_suppression:
        print("      None detected.")
    else:
        for field, indicators in sorted(fields_with_suppression.items()):
            for indicator, count in sorted(indicators.items(), key=lambda x: -x[1]):
                pct = count / total_rows * 100
                print(f"      {field}: {indicator!r}  => {count}/{total_rows} rows ({pct:.1f}%)")

    # Footnote fields
    print("\n  [2] FOOTNOTE FIELDS")
    if not footnote_fields:
        print("      None detected.")
    else:
        for field, fmt in sorted(footnote_fields.items()):
            non_empty = sum(
                1 for row in rows
                if row.get(field) is not None and str(row.get(field)).strip() not in ("", "0")
            )
            print(f"      {field}: format={fmt}, populated in {non_empty}/{total_rows} rows")

    # Partial missingness
    print("\n  [3] FIELDS WITH PARTIAL MISSINGNESS (null or empty in some rows)")
    if not partial_missing:
        print("      None.")
    else:
        for field, (count, pct) in sorted(partial_missing.items(), key=lambda x: -x[1][1]):
            print(f"      {field}: {count}/{total_rows} missing ({pct*100:.1f}%)")

    # Example rows
    print("\n  [4] EXAMPLE ROWS")

    def _print_row(label: str, row: dict[str, Any] | None) -> None:
        if row is None:
            print(f"      {label}: (no example found in sample)")
            return
        # Print only fields with non-trivial values (limit output width)
        id_val = row.get("facility_id") or row.get("provider_id") or row.get("ccn") or "?"
        name_val = row.get("facility_name") or row.get("hospital_name") or ""
        print(f"      {label}: id={id_val!r}  name={name_val!r}")
        # Show fields that carry the interesting value
        named_fn_fields = {f for f in footnote_fields if "footnote" in f.lower()}
        for k, v in row.items():
            sv = str(v).strip() if v is not None else ""
            if (
                sv.lower() in not_reported_phrases
                or sv == "*"
                or (k in named_fn_fields and sv not in ("", "0"))
                or (label == "SUPPRESSED" and sv == "" and k in named_fn_fields)
            ):
                print(f"        {k} = {v!r}")

    _print_row("SUPPRESSED", example_suppressed)
    _print_row("NOT_REPORTED", example_not_reported)
    _print_row("HAS_FOOTNOTE", example_footnote)


def main() -> None:
    sample_files = sorted(RAW_SAMPLES_DIR.glob("*.json"))
    if not sample_files:
        print(f"No .json files found in {RAW_SAMPLES_DIR}")
        return

    print(f"Analyzing {len(sample_files)} dataset sample(s) in {RAW_SAMPLES_DIR}")
    for path in sample_files:
        analyze_dataset(path)

    print(f"\n{'=' * 72}")
    print("Analysis complete.")


if __name__ == "__main__":
    main()
