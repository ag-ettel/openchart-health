"""
One-time script to generate test fixture files from raw recon samples.
Run from the repo root: python scripts/gen_fixtures.py
"""
import json
import os

BASE = "e:/openchart-health"
RAW = f"{BASE}/scripts/recon/raw_samples"
OUT = f"{BASE}/tests/pipeline/fixtures/hospital"


def load(dataset_id):
    with open(f"{RAW}/{dataset_id}.json") as fh:
        d = json.load(fh)
    rows = []
    for page in d["pages"]:
        rows.extend(page["results"])
    return d, rows


def write_fixture(dataset_id, fixture):
    path = f"{OUT}/{dataset_id}_fixtures.json"
    with open(path, "w") as fh:
        json.dump(fixture, fh, indent=2)
    print(f"wrote {dataset_id}_fixtures.json")


os.makedirs(OUT, exist_ok=True)

gaps = {}

# ============================================================
# 1. xubh-q36u  Hospital General Information
# ============================================================
d, rows = load("xubh-q36u")
reported = next((r for r in rows if r.get("hospital_overall_rating") not in ("Not Available", "", None)), None)
suppressed = next((r for r in rows if r.get("hospital_overall_rating") == "Not Available"), None)
fn_fields = [
    "hospital_overall_rating_footnote",
    "mort_group_footnote",
    "safety_group_footnote",
    "readm_group_footnote",
    "pt_exp_group_footnote",
    "te_group_footnote",
]
footnote = next((r for r in rows if any(r.get(f, "") not in ("", "None", None) for f in fn_fields)), None)

write_fixture("xubh-q36u", {
    "dataset_id": "xubh-q36u",
    "dataset_name": "Hospital General Information",
    "reported": reported,
    "suppressed": suppressed,
    "not_reported": None,
    "footnote": footnote,
    "null_denominator": None,
})
gaps["xubh-q36u"] = {
    "not_reported": (
        "This dataset has no per-measure not_reported state; only suppressed via "
        "Not Available with footnote 16. No separate not_reported encoding confirmed."
    ),
    "null_denominator": (
        "Not applicable - this dataset contains provider metadata, not measure rate values."
    ),
}

# ============================================================
# 2. yv7e-xc69  Timely and Effective Care
# ============================================================
d, rows = load("yv7e-xc69")
reported = next(
    (r for r in rows if r.get("score") not in ("Not Available", "", "very high", "high", None)), None
)
suppressed = next((r for r in rows if r.get("score") == "Not Available"), None)
footnote = next((r for r in rows if r.get("footnote", "") not in ("", "None", None)), None)
# null_denominator: score present but sample is empty string (EDV categorical measure)
null_denom = next(
    (r for r in rows if r.get("sample", "") == "" and r.get("score") not in ("Not Available", None, "")), None
)

write_fixture("yv7e-xc69", {
    "dataset_id": "yv7e-xc69",
    "dataset_name": "Timely and Effective Care",
    "reported": reported,
    "suppressed": suppressed,
    "not_reported": None,
    "footnote": footnote,
    "null_denominator": null_denom,
})
gaps["yv7e-xc69"] = {
    "not_reported": (
        "No explicit not_reported state found in 200-row sample. Suppressed rows use "
        "Not Available in score. EDV measure has empty sample field (not a not_reported "
        "case - it is a categorical measure with no denominator, represented in "
        "null_denominator)."
    ),
}

# ============================================================
# 3. dgck-syfz  HCAHPS Patient Survey
# ============================================================
d, rows = load("dgck-syfz")
reported = next(
    (r for r in rows if r.get("hcahps_answer_percent", "").strip() not in ("Not Applicable", "Not Available", "", None)),
    None,
)
suppressed = next((r for r in rows if r.get("hcahps_answer_percent") == "Not Applicable"), None)

write_fixture("dgck-syfz", {
    "dataset_id": "dgck-syfz",
    "dataset_name": "HCAHPS Patient Survey",
    "reported": reported,
    "suppressed": suppressed,
    "not_reported": None,
    "footnote": None,
    "null_denominator": None,
})
gaps["dgck-syfz"] = {
    "not_reported": (
        "No not_reported-specific encoding found; suppression is Not Applicable in value fields."
    ),
    "footnote": (
        "No rows with footnote codes found in 200-row sample. Phase 0 findings confirm "
        "footnote codes (5, 19, 29) exist in the dataset but were not present in the "
        "primary 200-row sample (sampling artifact - only 3 hospitals represented). "
        "A targeted pull at offset ~50,000 is needed for a live footnote fixture."
    ),
    "null_denominator": "Not applicable for this survey dataset structure.",
}

# ============================================================
# 4. ynj2-r877  Complications and Deaths
# ============================================================
d, rows = load("ynj2-r877")
reported = next((r for r in rows if r.get("score") not in ("Not Available", "", None)), None)
suppressed = next(
    (
        r for r in rows
        if r.get("score") == "Not Available"
        and r.get("compared_to_national", "").lower() == "number of cases too small"
    ),
    None,
)
footnote = next((r for r in rows if r.get("footnote", "") not in ("", "None", None)), None)
# null_denominator: PSI_90 composite has denominator=Not Applicable but score IS populated
null_denom = next((r for r in rows if r.get("denominator") == "Not Applicable"), None)

write_fixture("ynj2-r877", {
    "dataset_id": "ynj2-r877",
    "dataset_name": "Complications and Deaths",
    "reported": reported,
    "suppressed": suppressed,
    "not_reported": None,
    "footnote": footnote,
    "null_denominator": null_denom,
})
gaps["ynj2-r877"] = {
    "not_reported": (
        "No separate not_reported encoding found. Number of Cases Too Small in "
        "compared_to_national co-occurs with score=Not Available and is treated as "
        "suppressed, not not_reported (AMB-3 in pipeline_decisions.md)."
    ),
}

# ============================================================
# 5. 77hc-ibv8  Healthcare-Associated Infections
# ============================================================
d, rows = load("77hc-ibv8")
# reported: numeric SIR value
reported = next((r for r in rows if r.get("score", "") not in ("Not Available", "N/A", "", None)), None)
# suppressed: Not Available (predicted < 1 case, footnote 13)
suppressed = next((r for r in rows if r.get("score") == "Not Available"), None)
footnote = next((r for r in rows if r.get("footnote", "") not in ("", "None", None)), None)
# null_denominator: score=N/A on CILOWER when zero infections observed (footnote 8)
# This is structurally inapplicable, not suppressed - distinct state per Phase 0
not_applicable_row = next((r for r in rows if r.get("score") == "N/A"), None)

write_fixture("77hc-ibv8", {
    "dataset_id": "77hc-ibv8",
    "dataset_name": "Healthcare-Associated Infections",
    "reported": reported,
    "suppressed": suppressed,
    "not_reported": None,
    "footnote": footnote,
    "null_denominator": not_applicable_row,
})
gaps["77hc-ibv8"] = {
    "not_reported": (
        "No separate not_reported encoding confirmed in HAI dataset. "
        "null_denominator field contains a row with score=N/A on a CILOWER sub-measure "
        "(structurally inapplicable when zero infections observed, footnote 8). "
        "This is distinct from suppressed (Not Available + footnote 13)."
    ),
}

# ============================================================
# 6. 632h-zaca  Unplanned Hospital Visits (Readmissions)
# ============================================================
d, rows = load("632h-zaca")
reported = next((r for r in rows if r.get("score") not in ("Not Available", "", None)), None)
suppressed = next((r for r in rows if r.get("score") == "Not Available"), None)
footnote = next((r for r in rows if r.get("footnote", "") not in ("", "None", None)), None)
# null_denominator: number_of_patients=Not Applicable (EDAC measures) but score present
null_denom = next(
    (
        r for r in rows
        if r.get("number_of_patients") == "Not Applicable"
        and r.get("score") not in ("Not Available", None, "")
    ),
    None,
)

write_fixture("632h-zaca", {
    "dataset_id": "632h-zaca",
    "dataset_name": "Unplanned Hospital Visits (Readmissions)",
    "reported": reported,
    "suppressed": suppressed,
    "not_reported": None,
    "footnote": footnote,
    "null_denominator": null_denom,
})
gaps["632h-zaca"] = {
    "not_reported": (
        "Number of Cases Too Small in compared_to_national co-occurs with score=Not Available "
        "and is treated as suppressed. No separate not_reported encoding confirmed distinct "
        "from suppressed."
    ),
}

# ============================================================
# 7. wkfw-kthe  Outpatient Imaging Efficiency
# ============================================================
d, rows = load("wkfw-kthe")
reported = next((r for r in rows if r.get("score") not in ("Not Available", "", None)), None)
suppressed = next((r for r in rows if r.get("score") == "Not Available"), None)
footnote = next((r for r in rows if r.get("footnote", "") not in ("", "None", None)), None)

write_fixture("wkfw-kthe", {
    "dataset_id": "wkfw-kthe",
    "dataset_name": "Outpatient Imaging Efficiency",
    "reported": reported,
    "suppressed": suppressed,
    "not_reported": None,
    "footnote": footnote,
    "null_denominator": None,
})
gaps["wkfw-kthe"] = {
    "not_reported": "No not_reported encoding confirmed in sample. No denominator field in this dataset.",
    "null_denominator": "No denominator field present in this dataset.",
}

# ============================================================
# 8. rrqw-56er  Medicare Hospital Spending Per Patient
# ============================================================
d, rows = load("rrqw-56er")
reported = next((r for r in rows if r.get("score") not in ("Not Available", "", None)), None)
suppressed = next((r for r in rows if r.get("score") == "Not Available"), None)
footnote = next((r for r in rows if r.get("footnote", "") not in ("", "None", None)), None)

write_fixture("rrqw-56er", {
    "dataset_id": "rrqw-56er",
    "dataset_name": "Medicare Hospital Spending Per Patient",
    "reported": reported,
    "suppressed": suppressed,
    "not_reported": None,
    "footnote": footnote,
    "null_denominator": None,
})
gaps["rrqw-56er"] = {
    "not_reported": "No not_reported encoding confirmed in sample. Single MSPB_1 measure; no denominator field.",
    "null_denominator": "No denominator field present in this dataset.",
}

# ============================================================
# 9. 9n3s-kdb3  HRRP
# ============================================================
d, rows = load("9n3s-kdb3")
# reported: all count fields numeric, ratio populated
reported = next(
    (
        r for r in rows
        if r.get("number_of_readmissions") not in ("Too Few to Report", "N/A", "", None)
        and r.get("excess_readmission_ratio") not in ("N/A", "", None)
    ),
    None,
)
# count_suppressed: Too Few to Report in number_of_readmissions but ratio still populated
# This is count-field disclosure suppression per AMB-4
count_suppressed = next(
    (
        r for r in rows
        if r.get("number_of_readmissions") == "Too Few to Report"
        and r.get("excess_readmission_ratio") not in ("N/A", "", None)
    ),
    None,
)
# suppressed (full): N/A in excess_readmission_ratio - measure was not calculated at all
full_suppressed = next((r for r in rows if r.get("excess_readmission_ratio") == "N/A"), None)
footnote = next((r for r in rows if r.get("footnote", "") not in ("", "None", None)), None)

write_fixture("9n3s-kdb3", {
    "dataset_id": "9n3s-kdb3",
    "dataset_name": "Hospital Readmissions Reduction Program (HRRP)",
    "reported": reported,
    "suppressed": full_suppressed,
    "not_reported": None,
    "footnote": footnote,
    "null_denominator": None,
    "count_suppressed": count_suppressed,
})
gaps["9n3s-kdb3"] = {
    "not_reported": (
        "No separate not_reported encoding in this dataset. "
        "count_suppressed key added as a special HRRP fixture: "
        "number_of_readmissions=Too Few to Report co-occurring with a populated "
        "excess_readmission_ratio. This is count-field disclosure suppression, "
        "not measure suppression (AMB-4 in pipeline_decisions.md)."
    ),
    "null_denominator": "No denominator field in this dataset.",
}

# ============================================================
# 10. yq43-i98g  HACRP
# ============================================================
d, rows = load("yq43-i98g")
reported = next((r for r in rows if r.get("total_hac_score") not in ("", "N/A", None)), None)
hacrp_fn_cols = [
    "psi_90_composite_value_footnote",
    "psi_90_w_z_footnote",
    "clabsi_sir_footnote",
    "clabsi_w_z_footnote",
    "cauti_sir_footnote",
    "cauti_w_z_footnote",
    "ssi_sir_footnote",
    "ssi_w_z_footnote",
    "cdi_sir_footnote",
    "cdi_w_z_footnote",
    "mrsa_sir_footnote",
    "mrsa_w_z_footnote",
    "total_hac_score_footnote",
    "payment_reduction_footnote",
]
footnote = next(
    (r for r in rows if any(r.get(f, "") not in ("", "None", None) for f in hacrp_fn_cols)), None
)

write_fixture("yq43-i98g", {
    "dataset_id": "yq43-i98g",
    "dataset_name": "Hospital-Acquired Condition Reduction Program (HACRP)",
    "reported": reported,
    "suppressed": None,
    "not_reported": None,
    "footnote": footnote,
    "null_denominator": None,
})
gaps["yq43-i98g"] = {
    "suppressed": (
        "No suppressed rows found in 200-row sample. Phase 0 findings confirm no "
        "Not Available sentinel values in HACRP; footnotes (e.g., 13 = not enough cases) "
        "appear alongside populated numeric or empty-string cell values. Suppression state "
        "is communicated via per-field footnote codes, not via a sentinel value in the score field."
    ),
    "not_reported": "No separate not_reported encoding confirmed in HACRP.",
    "null_denominator": (
        "Wide-format dataset; no denominator field. Individual SIR scores may be absent "
        "(empty string) but no confirmed null_denominator pattern from sample."
    ),
}

# ============================================================
# 11. ypbt-wvdk  VBP
# ============================================================
d, rows = load("ypbt-wvdk")
reported = next((r for r in rows if r.get("total_performance_score") not in ("", "N/A", None)), None)

write_fixture("ypbt-wvdk", {
    "dataset_id": "ypbt-wvdk",
    "dataset_name": "Hospital Value-Based Purchasing Program (VBP)",
    "reported": reported,
    "suppressed": None,
    "not_reported": None,
    "footnote": None,
    "null_denominator": None,
})
gaps["ypbt-wvdk"] = {
    "suppressed": (
        "No suppression observed in 200-row sample. Phase 0 findings confirm no "
        "suppression state and no footnote fields in this API dataset."
    ),
    "not_reported": "No not_reported encoding confirmed. All rows in sample have TPS populated.",
    "footnote": "No footnote fields present in this API dataset (confirmed Phase 0).",
    "null_denominator": "No denominator field in this dataset.",
}

# ============================================================
# Write fixture_gaps.md
# ============================================================
gap_lines = [
    "# Fixture Gaps",
    "",
    "This document records missing fixture categories per dataset and the reason each gap exists.",
    "A `null` value in a fixture key means no example row for that category was found in the",
    "raw recon sample. The reason is documented below.",
    "",
    "---",
    "",
]

dataset_names = {
    "xubh-q36u": "Hospital General Information",
    "yv7e-xc69": "Timely and Effective Care",
    "dgck-syfz": "HCAHPS Patient Survey",
    "ynj2-r877": "Complications and Deaths",
    "77hc-ibv8": "Healthcare-Associated Infections",
    "632h-zaca": "Unplanned Hospital Visits (Readmissions)",
    "wkfw-kthe": "Outpatient Imaging Efficiency",
    "rrqw-56er": "Medicare Hospital Spending Per Patient",
    "9n3s-kdb3": "Hospital Readmissions Reduction Program (HRRP)",
    "yq43-i98g": "Hospital-Acquired Condition Reduction Program (HACRP)",
    "ypbt-wvdk": "Hospital Value-Based Purchasing Program (VBP)",
}

for dataset_id, gap_dict in gaps.items():
    name = dataset_names.get(dataset_id, dataset_id)
    gap_lines.append(f"## {dataset_id} - {name}")
    gap_lines.append("")
    for cat, reason in gap_dict.items():
        gap_lines.append(f"**{cat}:** {reason}")
        gap_lines.append("")
    gap_lines.append("---")
    gap_lines.append("")

with open(f"{OUT}/fixture_gaps.md", "w") as fh:
    fh.write("\n".join(gap_lines))
print("wrote fixture_gaps.md")

print("\nDone.")
