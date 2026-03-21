"""Tests for pipeline.normalize.complications_deaths.

Tests the Complications and Deaths normalizer against synthetic edge cases
and (where available) real CMS CSV archive data.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from pipeline.normalize.complications_deaths import (
    DATASET_ID,
    MEASURE_ID_ALIASES,
    MEASURE_IDS,
    normalize_dataset,
    normalize_row,
)


def _make_row(**overrides: str) -> dict[str, str]:
    """Build a minimal CompDeaths row with defaults."""
    base = {
        "facility_id": "010001",
        "facility_name": "SOUTHEAST HEALTH MEDICAL CENTER",
        "measure_id": "MORT_30_AMI",
        "measure_name": "Death rate for heart attack patients",
        "score": "12.5",
        "denominator": "523",
        "lower_estimate": "10.1",
        "higher_estimate": "15.3",
        "compared_to_national": "No Different Than the National Rate",
        "footnote": "",
        "start_date": "07/01/2022",
        "end_date": "06/30/2024",
    }
    base.update(overrides)
    return base


class TestNormalizeRow:

    def test_normal_mortality_row(self) -> None:
        result = normalize_row(_make_row())
        assert result is not None
        assert result["provider_id"] == "010001"
        assert result["measure_id"] == "MORT_30_AMI"
        assert result["numeric_value"] == Decimal("12.5")
        assert result["confidence_interval_lower"] == Decimal("10.1")
        assert result["confidence_interval_upper"] == Decimal("15.3")
        assert result["compared_to_national"] == "NO_DIFFERENT"
        assert result["source_dataset_id"] == DATASET_ID

    def test_suppressed_row(self) -> None:
        result = normalize_row(_make_row(
            score="Not Available",
            denominator="Not Available",
            lower_estimate="Not Available",
            higher_estimate="Not Available",
            compared_to_national="Number of Cases Too Small",
            footnote="1",
        ))
        assert result is not None
        assert result["suppressed"] is True
        assert result["numeric_value"] is None
        assert result["confidence_interval_lower"] is None

    def test_psi90_not_applicable_denominator(self) -> None:
        """PSI_90 denominator = 'Not Applicable' is not suppression."""
        result = normalize_row(_make_row(
            measure_id="PSI_90",
            score="0.95",
            denominator="Not Applicable",
            compared_to_national="No Different Than the National Value",
        ))
        assert result is not None
        assert result["suppressed"] is False
        assert result["numeric_value"] == Decimal("0.95")
        assert result["denominator"] is None  # Null, not suppressed
        assert result["compared_to_national"] == "NO_DIFFERENT"

    def test_compared_to_national_value_phrasing(self) -> None:
        """PSI_90 uses 'Value' not 'Rate' phrasing."""
        result = normalize_row(_make_row(
            measure_id="PSI_90",
            compared_to_national="Worse Than the National Value",
        ))
        assert result["compared_to_national"] == "WORSE"

    def test_compared_to_national_better(self) -> None:
        result = normalize_row(_make_row(
            compared_to_national="Better Than the National Rate",
        ))
        assert result["compared_to_national"] == "BETTER"

    def test_worse(self) -> None:
        result = normalize_row(_make_row(
            compared_to_national="Worse Than the National Rate",
        ))
        assert result["compared_to_national"] == "WORSE"


class TestMeasureIdAliases:
    """2019 archive uses different PSI measure IDs."""

    @pytest.mark.parametrize("old_id,new_id", list(MEASURE_ID_ALIASES.items()))
    def test_alias_mapped(self, old_id: str, new_id: str) -> None:
        result = normalize_row(_make_row(measure_id=old_id, score="1.5"))
        assert result is not None
        assert result["measure_id"] == new_id

    def test_current_ids_unchanged(self) -> None:
        result = normalize_row(_make_row(measure_id="PSI_90"))
        assert result["measure_id"] == "PSI_90"

    def test_retired_measure_skipped(self) -> None:
        result = normalize_row(_make_row(measure_id="READM_30_HOSP_WIDE"))
        assert result is None


class TestNormalizeDataset:

    def test_empty_input(self) -> None:
        assert normalize_dataset([]) == []

    def test_mixed_rows(self) -> None:
        rows = [
            _make_row(measure_id="MORT_30_AMI", score="12.5"),
            _make_row(measure_id="READM_30_HOSP_WIDE", score="15.0"),  # retired
            _make_row(measure_id="MORT_30_HF", score="Not Available", footnote="1"),
        ]
        results = normalize_dataset(rows)
        assert len(results) == 2  # retired row skipped
        assert results[0]["measure_id"] == "MORT_30_AMI"
        assert results[1]["measure_id"] == "MORT_30_HF"
        assert results[1]["suppressed"] is True

    def test_all_measures_recognized(self) -> None:
        """Every measure in MEASURE_IDS should normalize without warnings."""
        rows = [_make_row(measure_id=mid) for mid in sorted(MEASURE_IDS)]
        results = normalize_dataset(rows)
        assert len(results) == len(MEASURE_IDS)


class TestDateParsing:

    def test_csv_date_format(self) -> None:
        """Current CSV: MM/DD/YYYY."""
        result = normalize_row(_make_row(
            start_date="07/01/2022", end_date="06/30/2024"
        ))
        assert result["period_label"] == "2022-07 to 2024-06"

    def test_2019_date_fields(self) -> None:
        """2019 CSV uses 'measure_start_date' / 'measure_end_date' which
        csv_reader maps to 'start_date' / 'end_date'."""
        result = normalize_row(_make_row(
            start_date="04/01/2014", end_date="03/31/2017"
        ))
        assert result["period_label"] == "2014-04 to 2017-03"


class TestFootnotes:

    def test_footnote_29_methodology_change(self) -> None:
        """Footnote 29 signals methodology change — relevant for Rule 11."""
        result = normalize_row(_make_row(footnote="29"))
        assert 29 in result["footnote_codes"]
        assert "partial performance" in result["footnote_text"][0].lower()

    def test_compound_footnote(self) -> None:
        result = normalize_row(_make_row(footnote="1, 28"))
        assert result["footnote_codes"] == [1, 28]
        assert len(result["footnote_text"]) == 2

    def test_empty_footnote(self) -> None:
        result = normalize_row(_make_row(footnote=""))
        assert result["footnote_codes"] is None
