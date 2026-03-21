"""Tests for the simpler normalizers: imaging, mspb, hospital_info, hrrp, hacrp, vbp.

These are grouped together because they're straightforward datasets with fewer
edge cases than the complex normalizers (CompDeaths, HAI, Readmissions, HCAHPS, T&E).
"""

from __future__ import annotations

from decimal import Decimal

import pytest

# =========================================================================
# Imaging
# =========================================================================

from pipeline.normalize.imaging import normalize_dataset as imaging_normalize
from pipeline.normalize.imaging import normalize_row as imaging_row


class TestImaging:

    def _make_row(self, **kw: str) -> dict[str, str]:
        base = {"facility_id": "010001", "measure_id": "OP-8", "score": "5.2",
                "footnote": "", "start_date": "07/01/2023", "end_date": "06/30/2024"}
        base.update(kw)
        return base

    def test_normal(self) -> None:
        r = imaging_row(self._make_row())
        assert r is not None
        assert r["numeric_value"] == Decimal("5.2")
        assert r["source_dataset_id"] == "wkfw-kthe"

    def test_retired_measure_skipped(self) -> None:
        assert imaging_row(self._make_row(measure_id="OP-9")) is None
        assert imaging_row(self._make_row(measure_id="OP-11")) is None
        assert imaging_row(self._make_row(measure_id="OP-14")) is None

    def test_current_measures_pass(self) -> None:
        for mid in ["OP-8", "OP-10", "OP-13", "OP-39"]:
            r = imaging_row(self._make_row(measure_id=mid))
            assert r is not None

    def test_no_ci_fields(self) -> None:
        r = imaging_row(self._make_row())
        assert r["confidence_interval_lower"] is None
        assert r["confidence_interval_upper"] is None

    def test_no_compared_to_national(self) -> None:
        r = imaging_row(self._make_row())
        assert r["compared_to_national"] is None


# =========================================================================
# MSPB
# =========================================================================

from pipeline.normalize.mspb import normalize_dataset as mspb_normalize
from pipeline.normalize.mspb import normalize_row as mspb_row


class TestMSPB:

    def _make_row(self, **kw: str) -> dict[str, str]:
        base = {"facility_id": "010001", "measure_id": "MSPB-1", "score": "0.97",
                "footnote": "", "start_date": "01/01/2024", "end_date": "12/31/2024"}
        base.update(kw)
        return base

    def test_normal(self) -> None:
        r = mspb_row(self._make_row())
        assert r is not None
        assert r["numeric_value"] == Decimal("0.97")
        assert r["source_dataset_id"] == "rrqw-56er"

    def test_suppressed(self) -> None:
        r = mspb_row(self._make_row(score="Not Available", footnote="1"))
        assert r["suppressed"] is True
        assert r["numeric_value"] is None


# =========================================================================
# Hospital Info
# =========================================================================

from pipeline.normalize.hospital_info import normalize_row as info_row


class TestHospitalInfo:

    def _make_row(self, **kw: str) -> dict[str, str]:
        base = {
            "facility_id": "010001", "facility_name": "TEST HOSPITAL",
            "address": "123 Main St", "city_town": "DOTHAN", "state": "AL",
            "zip_code": "36301", "telephone_number": "3347938701",
            "hospital_type": "Acute Care Hospitals",
            "hospital_ownership": "Voluntary non-profit - Private",
            "emergency_services": "Yes",
            "meets_criteria_for_birthing_friendly_designation": "Y",
            "hospital_overall_rating": "4",
            "hospital_overall_rating_footnote": "",
            "count_of_facility_mort_measures": "7",
            "mort_group_footnote": "",
            "count_of_facility_safety_measures": "12",
            "safety_group_footnote": "",
            "count_of_facility_readm_measures": "11",
            "readm_group_footnote": "",
            "count_of_facility_pt_exp_measures": "8",
            "pt_exp_group_footnote": "",
            "count_of_facility_te_measures": "15",
            "te_group_footnote": "",
        }
        base.update(kw)
        return base

    def test_normal(self) -> None:
        r = info_row(self._make_row())
        assert r["provider_id"] == "010001"
        assert r["provider_type"] == "HOSPITAL"
        assert r["name"] == "TEST HOSPITAL"
        assert r["hospital_overall_rating"] == 4
        assert r["is_critical_access"] is False
        assert r["is_emergency_services"] is True
        assert r["birthing_friendly_designation"] is True

    def test_critical_access(self) -> None:
        r = info_row(self._make_row(hospital_type="Critical Access Hospitals"))
        assert r["is_critical_access"] is True

    def test_rating_not_available(self) -> None:
        r = info_row(self._make_row(hospital_overall_rating="Not Available",
                                     hospital_overall_rating_footnote="16"))
        assert r["hospital_overall_rating"] is None

    def test_group_counts(self) -> None:
        r = info_row(self._make_row())
        assert r["count_of_facility_mort_measures"] == 7
        assert r["count_of_facility_safety_measures"] == 12

    def test_address_structure(self) -> None:
        r = info_row(self._make_row())
        assert r["address"]["city"] == "DOTHAN"
        assert r["address"]["state"] == "AL"

    def test_zero_padding(self) -> None:
        r = info_row(self._make_row(facility_id="1001"))
        assert r["provider_id"] == "001001"


# =========================================================================
# HRRP
# =========================================================================

from pipeline.normalize.hrrp import normalize_row as hrrp_row


class TestHRRP:

    def _make_row(self, **kw: str) -> dict[str, str]:
        base = {
            "facility_id": "010001", "facility_name": "TEST", "state": "AL",
            "measure_name": "READM-30-AMI-HRRP",
            "number_of_discharges": "523",
            "excess_readmission_ratio": "0.9875",
            "predicted_readmission_rate": "15.2",
            "expected_readmission_rate": "15.4",
            "number_of_readmissions": "79",
            "footnote": "",
            "start_date": "07/01/2021", "end_date": "06/30/2024",
        }
        base.update(kw)
        return base

    def test_normal(self) -> None:
        r = hrrp_row(self._make_row())
        assert r["measure_id"] == "HRRP_AMI"
        assert r["numeric_value"] == Decimal("0.9875")
        assert r["suppressed"] is False
        assert r["count_suppressed"] is False
        assert r["sample_size"] == 523

    def test_count_suppressed(self) -> None:
        """DEC-023: ratio exists but counts hidden."""
        r = hrrp_row(self._make_row(
            number_of_discharges="N/A",
            number_of_readmissions="Too Few to Report",
        ))
        assert r["count_suppressed"] is True
        assert r["suppressed"] is False
        assert r["numeric_value"] == Decimal("0.9875")  # Ratio still populated
        assert r["sample_size"] is None

    def test_full_suppression(self) -> None:
        r = hrrp_row(self._make_row(
            excess_readmission_ratio="N/A",
            number_of_discharges="N/A",
            number_of_readmissions="N/A",
            footnote="1",
        ))
        assert r["suppressed"] is True
        assert r["count_suppressed"] is False
        assert r["numeric_value"] is None

    def test_not_reported(self) -> None:
        r = hrrp_row(self._make_row(
            excess_readmission_ratio="N/A",
            number_of_discharges="N/A",
            number_of_readmissions="N/A",
            footnote="5",
        ))
        assert r["not_reported"] is True
        assert r["suppressed"] is False

    def test_2019_era_measure_name(self) -> None:
        r = hrrp_row(self._make_row(measure_name="READM_30_AMI_HRRP"))
        assert r["measure_id"] == "HRRP_AMI"

    def test_all_current_measures(self) -> None:
        for name in ["READM-30-AMI-HRRP", "READM-30-CABG-HRRP", "READM-30-COPD-HRRP",
                      "READM-30-HF-HRRP", "READM-30-HIP-KNEE-HRRP", "READM-30-PN-HRRP"]:
            r = hrrp_row(self._make_row(measure_name=name))
            assert r is not None
            assert r["measure_id"].startswith("HRRP_")


# =========================================================================
# HACRP
# =========================================================================

from pipeline.normalize.hacrp import normalize_row as hacrp_row


class TestHACRP:

    def _make_row(self, **kw: str) -> dict[str, str]:
        base = {"facility_id": "010001", "fiscal_year": "2026",
                "total_hac_score": "3.5", "payment_reduction": "No",
                "payment_reduction_footnote": ""}
        base.update(kw)
        return base

    def test_no_penalty(self) -> None:
        r = hacrp_row(self._make_row())
        assert r["penalty_flag"] is False
        assert r["program"] == "HACRP"
        assert r["program_year"] == 2026

    def test_penalty(self) -> None:
        r = hacrp_row(self._make_row(payment_reduction="Yes"))
        assert r["penalty_flag"] is True

    def test_na_excluded(self) -> None:
        r = hacrp_row(self._make_row(payment_reduction="N/A"))
        assert r["penalty_flag"] is None

    def test_total_hac_score(self) -> None:
        r = hacrp_row(self._make_row(total_hac_score="4.75"))
        assert r["total_score"] == Decimal("4.75")


# =========================================================================
# VBP
# =========================================================================

from pipeline.normalize.vbp import normalize_row as vbp_row


class TestVBP:

    def _make_row(self, **kw: str) -> dict[str, str]:
        base = {"facility_id": "010001", "fiscal_year": "2026",
                "total_performance_score": "42.5",
                "unweighted_normalized_clinical_outcomes_domain_score": "15.2",
                "weighted_normalized_clinical_outcomes_domain_score": "6.08",
                "unweighted_person_and_community_engagement_domain_score": "30.1",
                "weighted_person_and_community_engagement_domain_score": "7.525",
                "unweighted_normalized_safety_domain_score": "55.0",
                "weighted_safety_domain_score": "13.75",
                "unweighted_normalized_efficiency_and_cost_reduction_domain_score": "20.0",
                "weighted_efficiency_and_cost_reduction_domain_score": "5.0"}
        base.update(kw)
        return base

    def test_normal(self) -> None:
        r = vbp_row(self._make_row())
        assert r["program"] == "VBP"
        assert r["program_year"] == 2026
        assert r["total_performance_score"] == Decimal("42.5")

    def test_domain_scores(self) -> None:
        r = vbp_row(self._make_row())
        assert r["unweighted_normalized_clinical_outcomes_domain_score"] == Decimal("15.2")
        assert r["weighted_safety_domain_score"] == Decimal("13.75")

    def test_suppressed_tps(self) -> None:
        r = vbp_row(self._make_row(total_performance_score="Not Available"))
        assert r["total_performance_score"] is None
