# Measure Direction Verification Checklist

Every `direction` value in MEASURE_REGISTRY must cite a CMS-published source. We
cannot assert direction on our own authority, even when it seems uncontroversial.

## Status Summary (completed 2026-03-19)

All 138 measures resolved. No outstanding items.

| `direction_source` | Count | Source |
|---|---|---|
| `CMS_API` | 44 | API `compared_to_national` or `measure_name` field contains explicit direction |
| `CMS_DATA_DICTIONARY` | 4 | CMS Hospital Data Dictionary: "Lower percentages suggest more efficient use" |
| `CMS_MEASURE_SPEC` | 12 | eCQM specs (ecqi.healthit.gov) or Joint Commission specs |
| `CMS_MEASURE_DEFINITION` | 77 | Plain language is self-descriptive; no explicit citation needed (DEC-011) |
| None (no direction) | 1 | EDV — categorical, no directional claim |
| **Total** | **138** | |

---

## VERIFIED: CMS Direction in API Data (40 measures)

`compared_to_national` field contains "Better Than the National Rate/Benchmark" or
"Worse Than the National Rate/Benchmark." Direction is implicit: lower rate + "Better
Than" = LOWER_IS_BETTER.

**Source:** CMS Provider Data API, confirmed against live data during Phase 0.

- **Complications & Deaths (ynj2-r877):** 20 measures — all LOWER_IS_BETTER
  CMS Data Dictionary (line 280): "Lower rates for surgical complications are better."
- **HAI (77hc-ibv8):** 6 SIR measures — all LOWER_IS_BETTER
  CMS Data Dictionary (line 336): "better than the national benchmark (lower)"
- **Readmissions (632h-zaca):** 14 measures — all LOWER_IS_BETTER
  CMS Data Dictionary (line 647): "Lower rates for readmission are better."
  CMS Data Dictionary (line 649): "A negative EDAC result is better"

**Note on EDAC:** Phase 0 findings show `compared_to_national` = "Not Available" for
EDAC measures in the API. Direction is verified from CMS Data Dictionary language
(line 649), not from the API field.

## VERIFIED: CMS Direction from Data Dictionary (4 measures)

**Outpatient Imaging Efficiency (wkfw-kthe):** 4 measures — all LOWER_IS_BETTER
CMS Data Dictionary (line 711): "Lower percentages suggest more efficient use of
medical imaging."

- OP-8, OP-10, OP-13, OP-39

## VERIFIED: Direction from CMS Definitions + Star Context (68 measures)

**HCAHPS (dgck-syfz):** 68 measures — direction derived from CMS topbox/bottombox
classification and star rating methodology. No explicit "higher is better" / "lower
is better" language found in CMS documentation. Direction is communicated through
the measure definitions themselves (e.g., "Always communicated well" is self-
evidently the favorable response; star ratings are intuitive).

The template sentence "CMS designates {cms_direction} values as associated with
better outcomes for this measure" should be **omitted** for HCAHPS measures, since
CMS does not make that explicit designation. Instead, display the CMS measure
definition and let the response categories speak for themselves.

---

## NEEDS CMS CITATION: 26 Measures

### Timely and Effective Care — yv7e-xc69 (25 measures)

The CMS Data Dictionary T&E section (lines 610-629) describes these as "treatments
known to get the best results" but does NOT include explicit "higher/lower is better"
language per measure. No `compared_to_national` field in the API.

**Decision needed:** Either find a CMS source with explicit direction, or handle like
HCAHPS — omit the direction sentence from the template and rely on CMS measure
definitions. Process measures like "percentage who received recommended treatment"
are self-descriptive.

**API links for manual review** (check Care Compare or CMS Measures Inventory for
each):

| | Measure ID | Registry Direction | `direction_source` | CMS Source |
|---|---|---|---|---|
| [x] | EDV | None | N/A | No directional claim to assert |
| [x] | OP_18a | LOWER_IS_BETTER | `CMS_API` | `measure_name`: "A lower number of minutes is better" |
| [x] | OP_18b | LOWER_IS_BETTER | `CMS_API` | `measure_name`: "A lower number of minutes is better" |
| [x] | OP_18c | LOWER_IS_BETTER | `CMS_API` | `measure_name`: "A lower number of minutes is better" |
| [x] | OP_18d | LOWER_IS_BETTER | `CMS_API` | `measure_name`: "A lower number of minutes is better" |
| [x] | OP_22 | LOWER_IS_BETTER | `CMS_MEASURE_DEFINITION` | "Left before being seen" — self-descriptive |
| [x] | OP_23 | HIGHER_IS_BETTER | `CMS_MEASURE_DEFINITION` | "brain scan results within 45 minutes" — self-descriptive |
| [x] | HH_HYPER | LOWER_IS_BETTER | `CMS_MEASURE_SPEC` | https://ecqi.healthit.gov/ecqm/hosp-inpt/2025/cms0871v4 |
| [x] | HH_HYPO | LOWER_IS_BETTER | `CMS_MEASURE_SPEC` | https://ecqi.healthit.gov/ecqm/hosp-inpt/2024/cms0816v3 |
| [x] | HH_ORAE | LOWER_IS_BETTER | `CMS_MEASURE_SPEC` | https://ecqi.healthit.gov/ecqm/hosp-inpt/2025/cms0819v3 |
| [x] | SAFE_USE_OF_OPIOIDS | LOWER_IS_BETTER | `CMS_MEASURE_SPEC` | https://ecqi.healthit.gov/ecqm/hosp-inpt/2024/cms0506v6 |
| [x] | SEP_1 | HIGHER_IS_BETTER | `CMS_MEASURE_DEFINITION` | "Appropriate care" — self-descriptive |
| [x] | SEP_SH_3HR | HIGHER_IS_BETTER | `CMS_MEASURE_DEFINITION` | Sepsis bundle compliance — self-descriptive |
| [x] | SEP_SH_6HR | HIGHER_IS_BETTER | `CMS_MEASURE_DEFINITION` | Sepsis bundle compliance — self-descriptive |
| [x] | SEV_SEP_3HR | HIGHER_IS_BETTER | `CMS_MEASURE_DEFINITION` | Sepsis bundle compliance — self-descriptive |
| [x] | SEV_SEP_6HR | HIGHER_IS_BETTER | `CMS_MEASURE_DEFINITION` | Sepsis bundle compliance — self-descriptive |
| [x] | STK_02 | HIGHER_IS_BETTER | `CMS_MEASURE_SPEC` | Joint Commission: https://manual.jointcommission.org/releases/TJC2025A1/MIF0128.html |
| [x] | STK_03 | HIGHER_IS_BETTER | `CMS_MEASURE_SPEC` | Joint Commission: same link |
| [x] | STK_05 | HIGHER_IS_BETTER | `CMS_MEASURE_SPEC` | Joint Commission: same link |
| [x] | VTE_1 | HIGHER_IS_BETTER | `CMS_MEASURE_SPEC` | https://ecqi.healthit.gov/ecqm/hosp-inpt/2026/cms0108v14 |
| [x] | VTE_2 | HIGHER_IS_BETTER | `CMS_MEASURE_SPEC` | Same as VTE_1 |
| [x] | OP_40 | HIGHER_IS_BETTER | `CMS_MEASURE_SPEC` | https://ecqi.healthit.gov/ecqm/hosp-outpt/2024/cms0996v4 |
| [x] | IMM_3 | HIGHER_IS_BETTER | `CMS_MEASURE_DEFINITION` | "Healthcare workers given influenza vaccination" — self-descriptive |
| [x] | OP_29 | HIGHER_IS_BETTER | `CMS_MEASURE_DEFINITION` | "appropriate follow-up interval" — self-descriptive |
| [x] | OP_31 | HIGHER_IS_BETTER | `CMS_MEASURE_SPEC` | https://qpp.cms.gov/docs/QPP_quality_measure_specifications/CQM-Measures/2020_Measure_303_MIPSCQM.pdf |

### Medicare Spending Per Patient — rrqw-56er (1 measure)

| | Measure ID | Registry Direction | `direction_source` | CMS Source |
|---|---|---|---|---|
| [x] | MSPB-1 | LOWER_IS_BETTER | `CMS_MEASURE_DEFINITION` | "spending per patient" — lower spending is self-descriptive in efficiency context |

---

## Resolution Approach (DEC-011)

For measures without explicit CMS direction language, the `plain_language` field
carries directionality through CMS's own descriptive terms ("appropriate care,"
"recommended treatment," "Hospital Harm," "improvement," "prophylaxis"). The template
direction sentence is omitted for these measures. See DEC-011 in
`docs/pipeline_decisions.md` and `[DIRECTION_NOTE]` conditional in
`text-templates.md`.
