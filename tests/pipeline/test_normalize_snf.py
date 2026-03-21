"""Tests for SNF QRP and SNF VBP normalizers."""

from __future__ import annotations

from decimal import Decimal

import pytest

# =========================================================================
# SNF QRP — compound measure_code parsing
# =========================================================================

from pipeline.normalize.snf_qrp import _parse_measure_code, normalize_dataset


class TestParseMeasureCode:

    def test_rsrr(self) -> None:
        assert _parse_measure_code("S_004_01_PPR_PD_RSRR") == ("S_004_01", "RSRR")

    def test_rsrr_2_5(self) -> None:
        assert _parse_measure_code("S_004_01_PPR_PD_RSRR_2_5") == ("S_004_01", "RSRR_2_5")

    def test_rsrr_97_5(self) -> None:
        assert _parse_measure_code("S_004_01_PPR_PD_RSRR_97_5") == ("S_004_01", "RSRR_97_5")

    def test_comp_perf(self) -> None:
        assert _parse_measure_code("S_005_02_DTC_COMP_PERF") == ("S_005_02", "COMP_PERF")

    def test_obs_rate(self) -> None:
        assert _parse_measure_code("S_005_02_DTC_OBS_RATE") == ("S_005_02", "OBS_RATE")

    def test_volume(self) -> None:
        assert _parse_measure_code("S_004_01_PPR_PD_VOLUME") == ("S_004_01", "VOLUME")

    def test_denominator(self) -> None:
        assert _parse_measure_code("S_007_02_DENOMINATOR") == ("S_007_02", "DENOMINATOR")

    def test_numerator(self) -> None:
        assert _parse_measure_code("S_007_02_NUMERATOR") == ("S_007_02", "NUMERATOR")

    def test_score(self) -> None:
        assert _parse_measure_code("S_006_01_MSPB_SCORE") == ("S_006_01", "SCORE")

    def test_numb(self) -> None:
        assert _parse_measure_code("S_006_01_MSPB_NUMB") == ("S_006_01", "NUMB")

    def test_rs_rate(self) -> None:
        assert _parse_measure_code("S_005_02_DTC_RS_RATE") == ("S_005_02", "RS_RATE")

    def test_rs_rate_2_5(self) -> None:
        assert _parse_measure_code("S_005_02_DTC_RS_RATE_2_5") == ("S_005_02", "RS_RATE_2_5")

    def test_obs(self) -> None:
        assert _parse_measure_code("S_004_01_PPR_PD_OBS") == ("S_004_01", "OBS")


class TestSNFQRPNormalize:

    def _make_group(self, base: str = "S_004_01", provider: str = "015009") -> list[dict[str, str]]:
        """Build a set of sub-code rows for one SNF QRP measure."""
        common = {"facility_id": provider, "start_date": "10/01/2022", "end_date": "09/30/2024", "footnote": "-"}
        return [
            {**common, "measure_code": f"{base}_PPR_PD_RSRR", "score": "9.30"},
            {**common, "measure_code": f"{base}_PPR_PD_RSRR_2_5", "score": "6.46"},
            {**common, "measure_code": f"{base}_PPR_PD_RSRR_97_5", "score": "13.07"},
            {**common, "measure_code": f"{base}_PPR_PD_OBS", "score": "5.66"},
            {**common, "measure_code": f"{base}_PPR_PD_VOLUME", "score": "106"},
            {**common, "measure_code": f"{base}_PPR_PD_COMP_PERF", "score": "No Different than the National Rate"},
        ]

    def test_groups_into_one_row(self) -> None:
        rows = self._make_group()
        results = normalize_dataset(rows)
        assert len(results) == 1

    def test_measure_id(self) -> None:
        results = normalize_dataset(self._make_group())
        assert results[0]["measure_id"] == "S_004_01"

    def test_primary_value(self) -> None:
        results = normalize_dataset(self._make_group())
        assert results[0]["numeric_value"] == Decimal("9.30")

    def test_ci_bounds(self) -> None:
        results = normalize_dataset(self._make_group())
        assert results[0]["confidence_interval_lower"] == Decimal("6.46")
        assert results[0]["confidence_interval_upper"] == Decimal("13.07")

    def test_observed_value(self) -> None:
        results = normalize_dataset(self._make_group())
        assert results[0]["observed_value"] == Decimal("5.66")

    def test_sample_size(self) -> None:
        results = normalize_dataset(self._make_group())
        assert results[0]["sample_size"] == 106

    def test_compared_to_national(self) -> None:
        results = normalize_dataset(self._make_group())
        assert results[0]["compared_to_national"] == "NO_DIFFERENT"

    def test_dash_footnote_treated_as_empty(self) -> None:
        results = normalize_dataset(self._make_group())
        assert results[0]["footnote_codes"] is None

    def test_empty_input(self) -> None:
        assert normalize_dataset([]) == []


# =========================================================================
# SNF VBP — fuzzy column matching
# =========================================================================

from pipeline.normalize.snf_vbp import normalize_row as vbp_row


class TestSNFVBPColumnMatching:

    def test_2026_columns(self) -> None:
        r = vbp_row({
            "facility_id": "015009",
            "snf_vbp_program_ranking": "5000",
            "incentive_payment_multiplier": "1.0123",
            "baseline_period:_fy_2022_risk_standardized_readmission_rate": "18.5",
            "performance_period:_fy_2024_risk_standardized_readmission_rate": "17.2",
            "snfrm_achievement_score": "55",
            "snfrm_improvement_score": "40",
            "snfrm_measure_score": "55",
        })
        assert r is not None
        assert r["incentive_payment_multiplier"] == Decimal("1.0123")
        assert r["baseline_rate"] == Decimal("18.5")
        assert r["performance_rate"] == Decimal("17.2")
        assert r["achievement_score"] == Decimal("55")
        assert r["improvement_score"] == Decimal("40")
        assert r["measure_score"] == Decimal("55")

    def test_2019_columns(self) -> None:
        r = vbp_row({
            "provider_number_ccn": "015009",
            "baseline_period:_cy_2015_risk_standardized_readmission_rate": "20.1",
            "performance_period:_cy_2017_risk_standardized_readmission_rate": "18.5",
        })
        assert r is not None
        assert r["provider_id"] == "015009"
        assert r["baseline_rate"] == Decimal("20.1")
        assert r["performance_rate"] == Decimal("18.5")

    def test_missing_provider_returns_none(self) -> None:
        r = vbp_row({"some_field": "value"})
        assert r is None

    def test_suppressed_values(self) -> None:
        r = vbp_row({
            "facility_id": "015009",
            "incentive_payment_multiplier": "---",
        })
        assert r is not None
        assert r["incentive_payment_multiplier"] is None


# =========================================================================
# NH Ownership — percentage parsing edge cases
# =========================================================================

from pipeline.normalize.nh_ownership import _parse_ownership_percentage, normalize_row as own_row


class TestOwnershipPercentageParsing:

    def test_with_percent_sign(self) -> None:
        assert _parse_ownership_percentage("50%") == (50, False)

    def test_without_percent_sign(self) -> None:
        assert _parse_ownership_percentage("50") == (50, False)

    def test_hundred_percent(self) -> None:
        assert _parse_ownership_percentage("100%") == (100, False)

    def test_five_percent(self) -> None:
        assert _parse_ownership_percentage("5%") == (5, False)

    def test_not_applicable(self) -> None:
        pct, not_provided = _parse_ownership_percentage("NOT APPLICABLE")
        assert pct is None
        assert not_provided is False

    def test_no_percentage_provided(self) -> None:
        pct, not_provided = _parse_ownership_percentage("NO PERCENTAGE PROVIDED")
        assert pct is None
        assert not_provided is True

    def test_empty(self) -> None:
        pct, not_provided = _parse_ownership_percentage("")
        assert pct is None
        assert not_provided is False

    def test_none(self) -> None:
        pct, not_provided = _parse_ownership_percentage(None)
        assert pct is None
        assert not_provided is False
