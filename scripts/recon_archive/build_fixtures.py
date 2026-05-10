"""
Script to build expanded fixture files (1000-2000 rows) from raw CMS sample data.
Run from project root: python scripts/build_fixtures.py
"""
import json
import os
from typing import Any, Optional

raw_dir = 'e:/openchart-health/scripts/recon/raw_samples'
fixtures_dir = 'e:/openchart-health/tests/pipeline/fixtures/hospital'


def is_numeric(val: Any) -> bool:
    if val is None or val == '':
        return False
    try:
        float(str(val))
        return True
    except (ValueError, TypeError):
        return False


def get_rows(ds_id: str) -> tuple[list[dict], dict]:
    with open(f'{raw_dir}/{ds_id}.json') as f:
        data = json.load(f)
    rows: list[dict] = []
    for page in data.get('pages', []):
        rows.extend(page.get('results', []))
    return rows, data


def find_reported(rows: list[dict], score_fields: list[str]) -> Optional[dict]:
    """Find a representative reported row with a valid numeric score (median-ish)."""
    candidates = []
    for r in rows:
        for sf in score_fields:
            v = r.get(sf, '')
            if is_numeric(v):
                candidates.append((r, float(v)))
                break
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[1])
    return candidates[len(candidates) // 2][0]


def find_suppressed(
    rows: list[dict],
    score_fields: list[str],
    footnote_fields: Optional[list[str]] = None,
    suppression_value: str = 'Not Available',
) -> Optional[dict]:
    """Find a row where primary score is suppression_value, prefer one with footnote code."""
    suppressed = []
    for r in rows:
        sf_val = r.get(score_fields[0], '')
        if sf_val == suppression_value:
            has_fn = False
            if footnote_fields:
                for ff in footnote_fields:
                    if r.get(ff, ''):
                        has_fn = True
                        break
            suppressed.append((r, has_fn))

    with_fn = [r for r, has_fn in suppressed if has_fn]
    without_fn = [r for r, has_fn in suppressed if not has_fn]

    if with_fn:
        return with_fn[0]
    if without_fn:
        return without_fn[0]
    return None


def find_footnote(rows: list[dict], footnote_fields: list[str]) -> Optional[dict]:
    """Find any row with a non-empty footnote field."""
    for r in rows:
        for ff in footnote_fields:
            v = r.get(ff, '')
            if v and v != '':
                return r
    return None


def find_not_reported_by_footnote(
    rows: list[dict],
    score_fields: list[str],
    footnote_fields: list[str],
    not_reported_fn_codes: Optional[list[str]] = None,
) -> Optional[dict]:
    """Find a row where score is Not Available AND footnote code indicates not-reported (e.g. code 19)."""
    if not_reported_fn_codes is None:
        not_reported_fn_codes = ['19']
    for r in rows:
        sf_val = r.get(score_fields[0], '')
        if sf_val == 'Not Available' and footnote_fields:
            for ff in footnote_fields:
                fn_val = r.get(ff, '')
                for code in not_reported_fn_codes:
                    if fn_val == code or fn_val.startswith(code + ',') or (', ' + code) in fn_val:
                        return r
    return None


def find_null_denominator(rows: list[dict], denom_fields: list[str]) -> Optional[dict]:
    """Find a row where a denominator/case-count field is Not Available, Not Applicable, empty, or 0."""
    for r in rows:
        for df in denom_fields:
            v = r.get(df, 'NOTPRESENT')
            if v == 'NOTPRESENT':
                continue
            if v in ('Not Available', 'Not Applicable', '', None, '0', 0):
                return r
    return None


def collect_suppression_values(rows: list[dict], score_fields: list[str]) -> list[str]:
    """Collect all distinct non-numeric values in score fields."""
    values: set[str] = set()
    for r in rows:
        for sf in score_fields:
            v = r.get(sf, '')
            if v and not is_numeric(v):
                values.add(str(v))
    return sorted(values)


def collect_footnote_codes(rows: list[dict], footnote_fields: list[str]) -> list[str]:
    """Collect all distinct footnote code values, handling comma-separated codes."""
    codes: set[str] = set()
    for r in rows:
        for ff in footnote_fields:
            v = r.get(ff, '')
            if v and v != '':
                for c in str(v).split(','):
                    c = c.strip()
                    if c:
                        codes.add(c)
    return sorted(codes, key=lambda x: int(x) if x.isdigit() else 999)


# ===== DATASET DEFINITIONS =====
datasets = [
    {
        'id': 'xubh-q36u',
        'score_fields': ['hospital_overall_rating'],
        'footnote_fields': ['hospital_overall_rating_footnote', 'mort_group_footnote', 'safety_group_footnote', 'readm_group_footnote'],
        'denom_fields': None,
    },
    {
        'id': 'yv7e-xc69',
        'score_fields': ['score'],
        'footnote_fields': ['footnote'],
        'denom_fields': ['sample'],
    },
    {
        'id': 'dgck-syfz',
        'score_fields': ['hcahps_answer_percent'],
        'footnote_fields': ['hcahps_answer_percent_footnote', 'patient_survey_star_rating_footnote', 'number_of_completed_surveys_footnote'],
        'denom_fields': ['number_of_completed_surveys'],
    },
    {
        'id': 'ynj2-r877',
        'score_fields': ['score'],
        'footnote_fields': ['footnote'],
        'denom_fields': ['denominator'],
    },
    {
        'id': '77hc-ibv8',
        'score_fields': ['score'],
        'footnote_fields': ['footnote'],
        'denom_fields': None,
    },
    {
        'id': '632h-zaca',
        'score_fields': ['score'],
        'footnote_fields': ['footnote'],
        'denom_fields': ['number_of_patients', 'denominator'],
    },
    {
        'id': 'wkfw-kthe',
        'score_fields': ['score'],
        'footnote_fields': ['footnote'],
        'denom_fields': None,
    },
    {
        'id': 'rrqw-56er',
        'score_fields': ['score'],
        'footnote_fields': ['footnote'],
        'denom_fields': None,
    },
    {
        'id': '9n3s-kdb3',
        'score_fields': ['excess_readmission_ratio', 'number_of_readmissions'],
        'footnote_fields': ['footnote'],
        'denom_fields': None,
        'count_suppressed': True,
    },
    {
        'id': 'yq43-i98g',
        'score_fields': ['psi_90_composite_value', 'clabsi_sir', 'total_hac_score'],
        'footnote_fields': [
            'psi_90_composite_value_footnote', 'clabsi_sir_footnote', 'cauti_sir_footnote',
            'ssi_sir_footnote', 'cdi_sir_footnote', 'mrsa_sir_footnote',
            'total_hac_score_footnote', 'payment_reduction_footnote',
        ],
        'denom_fields': None,
        'hacrp_suppressed': True,
    },
    {
        'id': 'ypbt-wvdk',
        'score_fields': ['total_performance_score'],
        'footnote_fields': [],
        'denom_fields': None,
    },
]

gaps_data = []

for ds_config in datasets:
    ds_id = ds_config['id']
    rows, raw_data = get_rows(ds_id)
    dataset_name = raw_data.get('dataset_name', ds_id)

    score_fields = ds_config['score_fields']
    footnote_fields = ds_config.get('footnote_fields', [])
    denom_fields = ds_config.get('denom_fields') or []

    print(f'\nProcessing {ds_id} ({dataset_name}), {len(rows)} rows...')

    # === reported ===
    reported = find_reported(rows, score_fields)

    # === suppressed ===
    if ds_id == 'yq43-i98g':
        # HACRP uses N/A not "Not Available"; find row where any SIR field is N/A with footnote code 13
        hacrp_suppressed = None
        for r in rows:
            for sf in ['psi_90_composite_value', 'clabsi_sir', 'cauti_sir', 'ssi_sir', 'cdi_sir', 'mrsa_sir']:
                if r.get(sf) == 'N/A':
                    fn_field = sf + '_footnote'
                    if r.get(fn_field, ''):
                        hacrp_suppressed = r
                        break
            if hacrp_suppressed:
                break
        suppressed = hacrp_suppressed
    elif ds_id == '9n3s-kdb3':
        # HRRP: 'N/A' is the suppression marker for the ratio
        suppressed = find_suppressed(rows, ['excess_readmission_ratio'], footnote_fields, suppression_value='N/A')
    else:
        suppressed = find_suppressed(rows, score_fields, footnote_fields, suppression_value='Not Available')

    # === not_reported ===
    if ds_id in ('xubh-q36u', 'yv7e-xc69', 'wkfw-kthe', 'rrqw-56er'):
        # footnote code 19 = "Results cannot be calculated for this reporting period"
        not_reported = find_not_reported_by_footnote(rows, score_fields, footnote_fields, ['19'])
    elif ds_id == '77hc-ibv8':
        # HAI uses 'N/A' with footnote 8 as a distinct state (CI bounds not applicable)
        hai_na_rows = [r for r in rows if r.get('score') == 'N/A' and r.get('footnote', '') == '8']
        not_reported = hai_na_rows[0] if hai_na_rows else None
    elif ds_id == '9n3s-kdb3':
        # HRRP: 'N/A' in excess_readmission_ratio = measure not applicable for hospital/measure combo
        na_rows = [r for r in rows if r.get('excess_readmission_ratio') == 'N/A']
        not_reported = na_rows[0] if na_rows else None
    elif ds_id == 'yq43-i98g':
        # HACRP: total_hac_score = 'N/A' indicates hospital not scored overall
        na_total = [r for r in rows if r.get('total_hac_score') == 'N/A']
        not_reported = na_total[0] if na_total else None
    elif ds_id in ('ynj2-r877', '632h-zaca', 'dgck-syfz'):
        # These do not have a distinct not-reported state distinguishable from suppressed in this sample
        not_reported = None
    else:
        not_reported = None

    # === footnote ===
    footnote_row = find_footnote(rows, footnote_fields) if footnote_fields else None

    # === null_denominator ===
    null_denom = find_null_denominator(rows, denom_fields) if denom_fields else None

    # === count_suppressed (HRRP only) ===
    count_suppressed = None
    if ds_config.get('count_suppressed'):
        for r in rows:
            if r.get('number_of_readmissions') == 'Too Few to Report' and is_numeric(r.get('excess_readmission_ratio', '')):
                count_suppressed = r
                break

    # === suppression_values and footnote_codes for gaps report ===
    # Use all relevant score-like fields per dataset
    all_score_fields = {
        'xubh-q36u': ['hospital_overall_rating'],
        'yv7e-xc69': ['score'],
        'dgck-syfz': ['hcahps_answer_percent', 'patient_survey_star_rating', 'hcahps_linear_mean_value'],
        'ynj2-r877': ['score'],
        '77hc-ibv8': ['score'],
        '632h-zaca': ['score'],
        'wkfw-kthe': ['score'],
        'rrqw-56er': ['score'],
        '9n3s-kdb3': ['excess_readmission_ratio', 'number_of_readmissions', 'number_of_discharges'],
        'yq43-i98g': ['psi_90_composite_value', 'clabsi_sir', 'cauti_sir', 'ssi_sir', 'cdi_sir', 'mrsa_sir', 'total_hac_score'],
        'ypbt-wvdk': ['total_performance_score'],
    }
    suppression_values = collect_suppression_values(rows, all_score_fields.get(ds_id, score_fields))
    all_footnote_codes = collect_footnote_codes(rows, footnote_fields)

    # === Build fixture ===
    fixture = {
        'dataset_id': ds_id,
        'dataset_name': dataset_name,
        'sample_size': len(rows),
        'reported': reported,
        'suppressed': suppressed,
        'not_reported': not_reported,
        'footnote': footnote_row,
        'null_denominator': null_denom,
        'count_suppressed': count_suppressed,
    }

    out_path = f'{fixtures_dir}/{ds_id}_fixtures.json'
    with open(out_path, 'w') as f:
        json.dump(fixture, f, indent=2)
    print(f'  Written: {out_path}')

    # Track gaps
    ds_gaps = {
        'dataset_id': ds_id,
        'dataset_name': dataset_name,
        'sample_size': len(rows),
        'suppression_values_observed': suppression_values,
        'footnote_codes_observed': all_footnote_codes,
        'null_categories': [],
    }
    for category in ['reported', 'suppressed', 'not_reported', 'footnote', 'null_denominator', 'count_suppressed']:
        if fixture[category] is None:
            ds_gaps['null_categories'].append(category)

    gaps_data.append(ds_gaps)

    print(f'  reported: {"FOUND" if reported else "NULL"}')
    print(f'  suppressed: {"FOUND" if suppressed else "NULL"}')
    print(f'  not_reported: {"FOUND" if not_reported else "NULL"}')
    print(f'  footnote: {"FOUND" if footnote_row else "NULL"}')
    print(f'  null_denominator: {"FOUND" if null_denom else "NULL"} {"(field N/A)" if not denom_fields else ""}')
    print(f'  count_suppressed: {"FOUND" if count_suppressed else "NULL"} {"(N/A)" if not ds_config.get("count_suppressed") else ""}')
    print(f'  suppression_values: {suppression_values}')
    print(f'  footnote_codes: {all_footnote_codes}')

# Save gaps data for the markdown report
with open(f'{fixtures_dir}/_gaps_data.json', 'w') as f:
    json.dump(gaps_data, f, indent=2)

print('\nAll fixtures written successfully.')
