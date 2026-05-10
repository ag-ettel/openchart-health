# Trend Period Enrichment: Add CI and Sample Size to Historical Periods

## Summary

Add `sample_size`, `ci_lower`, and `ci_upper` to each `TrendPeriod` entry in the
JSON export. CMS provides `denominator`, `lower_estimate`, and `higher_estimate`
on every historical row — we currently discard them when building the trend array.

The frontend is being updated to consume these fields (nullable) for:
- Shaded CI band across all trend periods on the chart
- Cases + interval in trend chart tooltip hovers

## Cross-Cutting Change Checklist

This change adds new fields to an existing type that crosses pipeline → export →
types → frontend. Use `.claude/rules/cross-cutting-change-checklist.md`.

## What CMS Provides Per Row

From the Complications and Deaths dataset (ynj2-r877) fixture:
```json
{
  "score": "3.24",
  "lower_estimate": "1.13",
  "higher_estimate": "5.36",
  "denominator": "1341"
}
```

These fields exist on every historical row across all datasets that report them.
The pipeline already parses them for the current period into `confidence_interval_lower`,
`confidence_interval_upper`, and `sample_size` on the `Measure` object. The trend
builder discards them.

## Changes Required

### 1. TypeScript Type: `frontend/types/provider.ts`

Add to `TrendPeriod`:
```typescript
export interface TrendPeriod {
  period_label:            string;
  numeric_value:           number | null;
  suppressed:              boolean;
  not_reported:            boolean;
  methodology_change_flag: boolean;
  // NEW — nullable because some datasets/periods may not have these
  sample_size:             number | null;
  ci_lower:                number | null;
  ci_upper:                number | null;
}
```

### 2. Pipeline Normalize Layer

In the normalizer that builds trend entries (likely in `pipeline/normalize/common.py`
or the per-dataset normalizers), include `sample_size`, `ci_lower`, `ci_upper` in the
trend dict. Map from CMS fields:

| TrendPeriod field | CMS API field | Notes |
|---|---|---|
| `sample_size` | `denominator` | Parse to int, null if "Not Available" |
| `ci_lower` | `lower_estimate` | Parse to Decimal, null if "Not Available" |
| `ci_upper` | `higher_estimate` | Parse to Decimal, null if "Not Available" |

Use the same suppression/not-available parsing logic already used for the main
measure values. These fields are null when the period is suppressed or not reported.

### 3. Pipeline Export Layer: `pipeline/export/build_json.py`

Include the three new fields in the trend array dicts. They should already flow
through if the normalize layer produces them — verify the trend builder doesn't
filter to a whitelist of keys.

### 4. JSON Export Schema: `.claude/rules/json-export.md`

Add to the TrendPeriod table:

| Field | Type | Nullable | Source |
|---|---|---|---|
| `sample_size` | integer | yes | CMS `denominator` field |
| `ci_lower` | number | yes | CMS `lower_estimate` field |
| `ci_upper` | number | yes | CMS `higher_estimate` field |

### 5. Database Schema

If trend data is stored in a DB table (check `database-schema.md`), add the three
columns. If trend is built at export time from `provider_measure_values` rows across
periods, the data is already in those rows — just include it in the trend builder
query.

### 6. Tests

- Update `tests/pipeline/test_export_contract.py` — add the three fields to
  `TREND_PERIOD_FIELDS` or equivalent
- Verify fixture-based tests still pass after normalize changes

### 7. Re-run Pipeline

After changes, re-run the pipeline and export to regenerate `build/data/*.json`
with enriched trend data. The frontend will pick up the new fields automatically.

## Frontend Status

The frontend `TrendChart` component already accepts `ciLower`/`ciUpper` props and
renders a CI band. Once the trend data includes per-period CI, the chart will be
updated to render the full shaded band and show cases + interval in tooltips.
The `TrendPeriod` type change in `provider.ts` must happen in the same commit as
the pipeline export change per the architectural contract.
