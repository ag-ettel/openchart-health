# Measure Group Misclassification Fix

## Problem

25 HCAHPS patient experience measures are assigned to the `SPENDING` measure_group
in the pipeline. They should be in `PATIENT_EXPERIENCE`. Only `MSPB-1` belongs in
`SPENDING`.

## Affected Measures

All measures with IDs starting with `H_BATH_HELP_*`, `H_CALL_BUTTON_*`, `H_COMP_3_*`,
`H_COMP_7_*`, `H_CT_MED_*`, `H_CT_PREFER_*`, `H_CT_UNDER_*` are currently in
`SPENDING` but are HCAHPS survey measures that belong in `PATIENT_EXPERIENCE`.

## How to Verify

```python
from pipeline.export.build_json import export_all
import json

with open("build/data/010001.json") as f:
    data = json.load(f)

spending = [m for m in data["measures"] if m["measure_group"] == "SPENDING"]
for m in spending:
    print(m["measure_id"], m["measure_name"])
```

Expected: only `MSPB-1` in SPENDING. All `H_*` measures should be PATIENT_EXPERIENCE.

## Root Cause

Likely in the normalizer for the Medicare Spending dataset or in MEASURE_REGISTRY
entries in `pipeline/config.py`. The `H_*` measures probably come from a dataset that
was bulk-assigned to `SPENDING` when some of its measures are actually HCAHPS items
that CMS bundles into the same download file.

## Fix

1. Check `pipeline/config.py` MEASURE_REGISTRY — find the entries for these `H_*`
   measure IDs and change their `group` from `MeasureGroup.SPENDING` to
   `MeasureGroup.PATIENT_EXPERIENCE`
2. Run `make check` to verify tests pass
3. After fix, re-run the export to regenerate JSON files
4. Use the cross-cutting change checklist if group enum values or display names change

## Scope

This is a data correction in MEASURE_REGISTRY, not a schema change. No migration
needed. No new enum values. Just reassigning existing measures to the correct group.
