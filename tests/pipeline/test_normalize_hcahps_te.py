"""Tests for HCAHPS and Timely & Effective Care normalizers."""

from __future__ import annotations

from decimal import Decimal

import pytest

# =========================================================================
# HCAHPS
# =========================================================================

from pipeline.normalize.hcahps import normalize_row as hcahps_row, DATASET_ID as HCAHPS_DS


class TestHCAHPS:

    def _make_row(self, **kw: str) -> dict[str, str]:
        base = {
            "facility_id": "010001",
            "hcahps_measure_id": "H_COMP_1_A_P",
            "hcahps_question": "Communication with nurses",
            "hcahps_answer_description": "Always",
            "patient_survey_star_rating": "Not Applicable",
            "patient_survey_star_rating_footnote": "",
            "hcahps_answer_percent": "75",
            "hcahps_answer_percent_footnote": "",
            "hcahps_linear_mean_value": "Not Applicable",
            "number_of_completed_surveys": "312",
            "number_of_completed_surveys_footnote": "",
            "survey_response_rate_percent": "28",
            "survey_response_rate_percent_footnote": "",
            "start_date": "04/01/2024",
            "end_date": "03/31/2025",
        }
        base.update(kw)
        return base

    def test_normal_row(self) -> None:
        r = hcahps_row(self._make_row())
        assert r is not None
        assert r["measure_id"] == "H_COMP_1_A_P"
        assert r["numeric_value"] == Decimal("75")
        assert r["sample_size"] == 312
        assert r["source_dataset_id"] == HCAHPS_DS

    def test_not_applicable_score(self) -> None:
        """Star rating rows have 'Not Applicable' for answer percent — not suppression."""
        r = hcahps_row(self._make_row(
            hcahps_measure_id="H_COMP_1_STAR_RATING",
            hcahps_answer_percent="Not Applicable",
        ))
        assert r is not None
        assert r["suppressed"] is False
        assert r["numeric_value"] is None  # Not Applicable, no value

    def test_not_available_suppressed(self) -> None:
        r = hcahps_row(self._make_row(
            hcahps_answer_percent="Not Available",
            hcahps_answer_percent_footnote="1",
        ))
        assert r["suppressed"] is True
        assert r["numeric_value"] is None

    def test_not_reported(self) -> None:
        r = hcahps_row(self._make_row(
            hcahps_answer_percent="Not Available",
            hcahps_answer_percent_footnote="5",
        ))
        assert r["not_reported"] is True
        assert r["suppressed"] is False

    def test_no_ci_fields(self) -> None:
        r = hcahps_row(self._make_row())
        assert r["confidence_interval_lower"] is None
        assert r["confidence_interval_upper"] is None

    def test_no_compared_to_national(self) -> None:
        r = hcahps_row(self._make_row())
        assert r["compared_to_national"] is None

    def test_empty_measure_id_skipped(self) -> None:
        r = hcahps_row(self._make_row(hcahps_measure_id=""))
        assert r is None


# =========================================================================
# Timely & Effective Care
# =========================================================================

from pipeline.normalize.timely_effective import (
    normalize_row as te_row,
    normalize_dataset as te_normalize,
    DATASET_ID as TE_DS,
    MEASURE_IDS,
    RETIRED_MEASURE_IDS,
)


class TestTimlyEffective:

    def _make_row(self, **kw: str) -> dict[str, str]:
        base = {
            "facility_id": "010001",
            "_condition": "Sepsis Care",
            "measure_id": "SEP_1",
            "measure_name": "Sepsis Bundle",
            "score": "67",
            "sample": "185",
            "footnote": "",
            "start_date": "01/01/2024",
            "end_date": "12/31/2024",
        }
        base.update(kw)
        return base

    def test_normal_row(self) -> None:
        r = te_row(self._make_row())
        assert r is not None
        assert r["numeric_value"] == Decimal("67")
        assert r["sample_size"] == 185
        assert r["source_dataset_id"] == TE_DS

    def test_edv_categorical(self) -> None:
        """DEC-024: EDV stores categorical text, not numeric."""
        r = te_row(self._make_row(measure_id="EDV", score="very high"))
        assert r is not None
        assert r["score_text"] == "very high"
        assert r["numeric_value"] is None

    def test_edv_all_categories(self) -> None:
        for cat in ["very high", "high", "medium", "low"]:
            r = te_row(self._make_row(measure_id="EDV", score=cat))
            assert r["score_text"] == cat
            assert r["numeric_value"] is None

    def test_edv_not_available(self) -> None:
        r = te_row(self._make_row(measure_id="EDV", score="Not Available"))
        assert r["suppressed"] is True
        assert r["score_text"] is None

    def test_retired_measures_skipped(self) -> None:
        for mid in ["OP_1", "OP_2", "VTE_6", "ED_1b", "PC_01", "STK_06"]:
            r = te_row(self._make_row(measure_id=mid))
            assert r is None

    def test_2019_alias(self) -> None:
        r = te_row(self._make_row(measure_id="IMM_3_OP_27_FAC_ADHPCT"))
        assert r is not None
        assert r["measure_id"] == "IMM_3"

    def test_no_ci_or_compared(self) -> None:
        r = te_row(self._make_row())
        assert r["confidence_interval_lower"] is None
        assert r["compared_to_national"] is None

    def test_uses_sample_not_denominator(self) -> None:
        r = te_row(self._make_row(sample="500"))
        assert r["sample_size"] == 500

    def test_dataset_excludes_retired(self) -> None:
        rows = [
            self._make_row(measure_id="SEP_1"),
            self._make_row(measure_id="OP_1"),  # retired
            self._make_row(measure_id="EDV", score="low"),
        ]
        results = te_normalize(rows)
        assert len(results) == 2
        ids = {r["measure_id"] for r in results}
        assert ids == {"SEP_1", "EDV"}
