"""Tests for pipeline.normalize.readmissions — Unplanned Hospital Visits."""

from __future__ import annotations

from decimal import Decimal

import pytest

from pipeline.normalize.readmissions import (
    DATASET_ID,
    MEASURE_ID_ALIASES,
    MEASURE_IDS,
    normalize_dataset,
    normalize_row,
)


def _make_row(**overrides: str) -> dict[str, str]:
    """Build a minimal Readmissions row."""
    base = {
        "facility_id": "010001",
        "measure_id": "READM_30_AMI",
        "measure_name": "Rate of readmission for AMI patients",
        "score": "15.9",
        "denominator": "523",
        "lower_estimate": "13.8",
        "higher_estimate": "18.2",
        "compared_to_national": "No Different Than the National Rate",
        "number_of_patients": "",
        "number_of_patients_returned": "",
        "footnote": "",
        "start_date": "07/01/2021",
        "end_date": "06/30/2024",
    }
    base.update(overrides)
    return base


class TestNormalizeRow:

    def test_normal_readm_row(self) -> None:
        result = normalize_row(_make_row())
        assert result is not None
        assert result["measure_id"] == "READM_30_AMI"
        assert result["numeric_value"] == Decimal("15.9")
        assert result["confidence_interval_lower"] == Decimal("13.8")
        assert result["compared_to_national"] == "NO_DIFFERENT"
        assert result["source_dataset_id"] == DATASET_ID

    def test_suppressed(self) -> None:
        result = normalize_row(_make_row(
            score="Not Available",
            denominator="Not Available",
            lower_estimate="Not Available",
            higher_estimate="Not Available",
            compared_to_national="Number of Cases Too Small",
            footnote="1",
        ))
        assert result["suppressed"] is True
        assert result["numeric_value"] is None

    def test_edac_days_better(self) -> None:
        result = normalize_row(_make_row(
            measure_id="EDAC_30_AMI",
            score="-15.6",
            compared_to_national="Fewer Days Than Average per 100 Discharges",
        ))
        assert result["compared_to_national"] == "BETTER"
        assert result["numeric_value"] == Decimal("-15.6")

    def test_edac_days_worse(self) -> None:
        result = normalize_row(_make_row(
            measure_id="EDAC_30_HF",
            compared_to_national="More Days Than Average per 100 Discharges",
        ))
        assert result["compared_to_national"] == "WORSE"

    def test_edac_days_no_different(self) -> None:
        result = normalize_row(_make_row(
            measure_id="EDAC_30_PN",
            compared_to_national="Average Days per 100 Discharges",
        ))
        assert result["compared_to_national"] == "NO_DIFFERENT"

    def test_edac_2019_lowercase_days(self) -> None:
        """2019 archives use lowercase: 'Average days per 100 discharges'."""
        result = normalize_row(_make_row(
            measure_id="EDAC_30_AMI",
            compared_to_national="Average days per 100 discharges",
        ))
        assert result["compared_to_national"] == "NO_DIFFERENT"

    def test_op36_expected_phrasing(self) -> None:
        result = normalize_row(_make_row(
            measure_id="OP_36",
            compared_to_national="No Different than expected",
        ))
        assert result["compared_to_national"] == "NO_DIFFERENT"

    def test_op36_better_expected(self) -> None:
        result = normalize_row(_make_row(
            measure_id="OP_36",
            compared_to_national="Better than expected",
        ))
        assert result["compared_to_national"] == "BETTER"

    def test_op36_worse_expected(self) -> None:
        result = normalize_row(_make_row(
            measure_id="OP_36",
            compared_to_national="Worse than expected",
        ))
        assert result["compared_to_national"] == "WORSE"

    def test_case_inconsistency_too_few(self) -> None:
        """CMS uses both capitalizations in the same snapshot (AMB-3)."""
        r1 = normalize_row(_make_row(
            compared_to_national="Number of Cases Too Small",
            score="Not Available", footnote="1",
        ))
        r2 = normalize_row(_make_row(
            compared_to_national="Number of cases too small",
            score="Not Available", footnote="1",
        ))
        assert r1["compared_to_national"] == "TOO_FEW_CASES"
        assert r2["compared_to_national"] == "TOO_FEW_CASES"

    def test_number_of_patients_as_sample_size(self) -> None:
        """2021+ has number_of_patients which should be used as sample_size."""
        result = normalize_row(_make_row(
            number_of_patients="264",
            denominator="273",
        ))
        assert result["sample_size"] == 264
        assert result["denominator"] == 273

    def test_no_number_of_patients_falls_back_to_denominator(self) -> None:
        """2019 has no number_of_patients — sample_size from denominator."""
        result = normalize_row(_make_row(
            number_of_patients="",
            denominator="523",
        ))
        assert result["sample_size"] == 523


class TestMeasureIdAliases:

    @pytest.mark.parametrize("old_id,new_id", list(MEASURE_ID_ALIASES.items()))
    def test_alias_mapped(self, old_id: str, new_id: str) -> None:
        result = normalize_row(_make_row(measure_id=old_id))
        assert result is not None
        assert result["measure_id"] == new_id

    def test_retired_hosp_wide(self) -> None:
        result = normalize_row(_make_row(measure_id="READM_30_HOSP_WIDE"))
        assert result is None

    def test_retired_stk(self) -> None:
        result = normalize_row(_make_row(measure_id="READM_30_STK"))
        assert result is None

    def test_hybrid_hwr_passes(self) -> None:
        result = normalize_row(_make_row(measure_id="Hybrid_HWR"))
        assert result is not None
        assert result["measure_id"] == "Hybrid_HWR"


class TestNormalizeDataset:

    def test_empty(self) -> None:
        assert normalize_dataset([]) == []

    def test_mixed_with_retired(self) -> None:
        rows = [
            _make_row(measure_id="READM_30_AMI"),
            _make_row(measure_id="READM_30_HOSP_WIDE"),
            _make_row(measure_id="READM_30_STK"),
            _make_row(measure_id="EDAC_30_HF"),
        ]
        results = normalize_dataset(rows)
        assert len(results) == 2
        ids = {r["measure_id"] for r in results}
        assert ids == {"READM_30_AMI", "EDAC_30_HF"}

    def test_all_current_measures_recognized(self) -> None:
        rows = [_make_row(measure_id=mid) for mid in sorted(MEASURE_IDS)]
        results = normalize_dataset(rows)
        assert len(results) == len(MEASURE_IDS)
