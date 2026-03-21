"""Tests for all nursing home normalizers."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

# =========================================================================
# MDS Quality
# =========================================================================

from pipeline.normalize.nh_mds_quality import normalize_row as mds_row, normalize_dataset as mds_normalize


class TestMDSQuality:

    def _make_row(self, **kw: str) -> dict[str, str]:
        base = {
            "facility_id": "015009", "measure_code": "401",
            "measure_description": "Percent of residents with UTI",
            "resident_type": "Long Stay",
            "q1_measure_score": "5.2", "footnote_for_q1_measure_score": "",
            "q2_measure_score": "4.8", "footnote_for_q2_measure_score": "",
            "q3_measure_score": "5.0", "footnote_for_q3_measure_score": "",
            "q4_measure_score": "4.5", "footnote_for_q4_measure_score": "",
            "four_quarter_average_score": "4.9",
            "footnote_for_four_quarter_average_score": "",
            "used_in_quality_measure_five_star_rating": "Y",
            "measure_period": "2024Q4-2025Q3",
        }
        base.update(kw)
        return base

    def test_produces_5_rows(self) -> None:
        """DEC-015: Q1-Q4 + average = 5 rows per measure per provider."""
        rows = mds_row(self._make_row())
        assert len(rows) == 5

    def test_average_period_label(self) -> None:
        rows = mds_row(self._make_row())
        avg = [r for r in rows if r["period_label"] == "2024Q4-2025Q3"]
        assert len(avg) == 1
        assert avg[0]["numeric_value"] == Decimal("4.9")

    def test_suppressed_quarter(self) -> None:
        rows = mds_row(self._make_row(
            q1_measure_score="", footnote_for_q1_measure_score="9"
        ))
        q1 = [r for r in rows if "Q1" in r["period_label"]]
        assert len(q1) == 1
        assert q1[0]["suppressed"] is True

    def test_measure_id_prefixed(self) -> None:
        rows = mds_row(self._make_row(measure_code="401"))
        assert all(r["measure_id"] == "NH_MDS_401" for r in rows)

    def test_empty_measure_code(self) -> None:
        rows = mds_row(self._make_row(measure_code=""))
        assert rows == []


# =========================================================================
# Claims Quality
# =========================================================================

from pipeline.normalize.nh_claims_quality import normalize_row as claims_row


class TestClaimsQuality:

    def _make_row(self, **kw: str) -> dict[str, str]:
        base = {
            "facility_id": "015009", "measure_code": "521",
            "resident_type": "Short Stay",
            "adjusted_score": "18.5", "observed_score": "20.1",
            "expected_score": "17.2", "footnote_for_score": "",
            "measure_period": "20240701-20250630",
        }
        base.update(kw)
        return base

    def test_normal(self) -> None:
        r = claims_row(self._make_row())
        assert r is not None
        assert r["numeric_value"] == Decimal("18.5")
        assert r["observed_value"] == Decimal("20.1")
        assert r["expected_value"] == Decimal("17.2")
        assert r["measure_id"] == "NH_CLAIMS_521"

    def test_suppressed(self) -> None:
        r = claims_row(self._make_row(adjusted_score="", footnote_for_score="1"))
        assert r["suppressed"] is True
        assert r["numeric_value"] is None
        # observed_score may still be populated when adjusted is suppressed
        assert r["observed_value"] == Decimal("20.1")


# =========================================================================
# Health Deficiencies
# =========================================================================

from pipeline.normalize.nh_health_deficiencies import normalize_row as deficiency_row


class TestHealthDeficiencies:

    def _make_row(self, **kw: str) -> dict[str, str]:
        base = {
            "facility_id": "015009", "survey_date": "01/15/2024",
            "survey_type": "Health", "deficiency_prefix": "F",
            "deficiency_tag_number": "0690",
            "deficiency_description": "Incontinence care",
            "deficiency_category": "Quality of Care",
            "scope_severity_code": "D",
            "deficiency_corrected": "Deficient, Provider has date of correction",
            "correction_date": "02/15/2024",
            "inspection_cycle": "1",
            "standard_deficiency": "Y", "complaint_deficiency": "N",
            "infection_control_inspection_deficiency": "N",
            "citation_under_idr": "N", "citation_under_iidr": "N",
        }
        base.update(kw)
        return base

    def test_normal(self) -> None:
        r = deficiency_row(self._make_row())
        assert r is not None
        assert r["provider_id"] == "015009"
        assert r["deficiency_tag"] == "0690"
        assert r["scope_severity_code"] == "D"
        assert r["is_immediate_jeopardy"] is False
        assert r["survey_date"] == date(2024, 1, 15)

    def test_immediate_jeopardy(self) -> None:
        for code in ["J", "K", "L"]:
            r = deficiency_row(self._make_row(scope_severity_code=code))
            assert r["is_immediate_jeopardy"] is True

    def test_complaint_deficiency(self) -> None:
        r = deficiency_row(self._make_row(complaint_deficiency="Y"))
        assert r["is_complaint_deficiency"] is True

    def test_empty_tag_skipped(self) -> None:
        r = deficiency_row(self._make_row(deficiency_tag_number=""))
        assert r is None

    def test_lifecycle_fields_initialized(self) -> None:
        """DEC-028: lifecycle fields start as None/False."""
        r = deficiency_row(self._make_row())
        assert r["originally_published_scope_severity"] is None
        assert r["is_contested"] is False


# =========================================================================
# Penalties
# =========================================================================

from pipeline.normalize.nh_penalties import normalize_row as penalty_row


class TestPenalties:

    def _make_row(self, **kw: str) -> dict[str, str]:
        base = {
            "facility_id": "015009", "penalty_date": "06/27/2023",
            "penalty_type": "Fine", "fine_amount": "47829",
            "payment_denial_start_date": "", "payment_denial_length_in_days": "",
        }
        base.update(kw)
        return base

    def test_fine(self) -> None:
        r = penalty_row(self._make_row())
        assert r is not None
        assert r["penalty_type"] == "Fine"
        assert r["fine_amount"] == Decimal("47829")
        assert r["penalty_date"] == date(2023, 6, 27)

    def test_payment_denial(self) -> None:
        r = penalty_row(self._make_row(
            penalty_type="Payment Denial", fine_amount="",
            payment_denial_start_date="07/01/2023",
            payment_denial_length_in_days="42",
        ))
        assert r["penalty_type"] == "Payment Denial"
        assert r["payment_denial_length_days"] == 42

    def test_lifecycle_fields_initialized(self) -> None:
        r = penalty_row(self._make_row())
        assert r["originally_published_fine_amount"] is None
        assert r["originally_published_vintage"] is None


# =========================================================================
# Ownership
# =========================================================================

from pipeline.normalize.nh_ownership import normalize_row as ownership_row


class TestOwnership:

    def _make_row(self, **kw: str) -> dict[str, str]:
        base = {
            "facility_id": "015009", "owner_name": "JOHN DOE",
            "owner_type": "Individual",
            "role_played_by_owner_or_manager_in_facility": "5% OR GREATER DIRECT OWNERSHIP INTEREST",
            "ownership_percentage": "50%",
            "association_date": "since 01/15/2005",
        }
        base.update(kw)
        return base

    def test_normal(self) -> None:
        r = ownership_row(self._make_row())
        assert r is not None
        assert r["owner_name"] == "JOHN DOE"
        assert r["ownership_percentage"] == 50
        assert r["ownership_percentage_not_provided"] is False
        assert r["association_date"] == date(2005, 1, 15)

    def test_no_percentage_provided(self) -> None:
        r = ownership_row(self._make_row(ownership_percentage="NO PERCENTAGE PROVIDED"))
        assert r["ownership_percentage"] is None
        assert r["ownership_percentage_not_provided"] is True

    def test_not_applicable_percentage(self) -> None:
        r = ownership_row(self._make_row(ownership_percentage="NOT APPLICABLE"))
        assert r["ownership_percentage"] is None
        assert r["ownership_percentage_not_provided"] is False

    def test_empty_owner_skipped(self) -> None:
        r = ownership_row(self._make_row(owner_name=""))
        assert r is None


# =========================================================================
# NH Provider Info
# =========================================================================

from pipeline.normalize.nh_provider_info import normalize_row as nh_info_row


class TestNHProviderInfo:

    def _make_row(self, **kw: str) -> dict[str, str]:
        base = {
            "facility_id": "015009", "facility_name": "TEST NH",
            "facility_address": "123 Main", "city_town": "DOTHAN",
            "state": "AL", "zip_code": "36301",
            "ownership_type": "For profit - Corporation",
            "provider_type": "Medicare and Medicaid",
            "overall_rating": "3",
            "special_focus_status": "",
            "abuse_icon": "N",
            "number_of_certified_beds": "120",
            "total_number_of_penalties": "2",
        }
        base.update(kw)
        return base

    def test_normal(self) -> None:
        r = nh_info_row(self._make_row())
        assert r["provider_id"] == "015009"
        assert r["provider_type"] == "NURSING_HOME"
        assert r["certified_beds"] == 120

    def test_sff(self) -> None:
        r = nh_info_row(self._make_row(special_focus_status="SFF"))
        assert r["is_special_focus_facility"] is True
        assert r["is_special_focus_facility_candidate"] is False

    def test_sff_candidate(self) -> None:
        r = nh_info_row(self._make_row(special_focus_status="SFF Candidate"))
        assert r["is_special_focus_facility"] is False
        assert r["is_special_focus_facility_candidate"] is True

    def test_abuse_icon(self) -> None:
        r = nh_info_row(self._make_row(abuse_icon="Y"))
        assert r["is_abuse_icon"] is True


# =========================================================================
# SNF VBP
# =========================================================================

from pipeline.normalize.snf_vbp import normalize_row as snf_vbp_row


class TestSNFVBP:

    def test_normal(self) -> None:
        r = snf_vbp_row({
            "facility_id": "015009",
            "snf_vbp_program_ranking": "5000",
            "incentive_payment_multiplier": "1.0123",
            "baseline_period:_fy_2022_risk_standardized_readmission_rate": "18.5",
            "performance_period:_fy_2024_risk_standardized_readmission_rate": "17.2",
        })
        assert r is not None
        assert r["program"] == "SNF_VBP"
        assert r["incentive_payment_multiplier"] == Decimal("1.0123")

    def test_2019_era(self) -> None:
        r = snf_vbp_row({
            "provider_number_ccn": "015009",
            "baseline_period:_cy_2015_risk_standardized_readmission_rate": "20.1",
        })
        assert r is not None
        assert r["provider_id"] == "015009"
