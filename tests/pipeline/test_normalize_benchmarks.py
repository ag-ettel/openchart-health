"""
Tests for pipeline/normalize/benchmarks.py

Covers:
  - Hospital national benchmark normalization (Score and National Rate variants)
  - Hospital state benchmark normalization
  - NH StateUSAverages normalization (wide-to-long pivot)
  - SNF QRP national benchmark normalization
  - Unparseable scores skipped
  - Period label derivation from Start Date / End Date
  - HGLM measures excluded from state configs (DEC-036 constraint)
"""

from decimal import Decimal

import pytest

from pipeline.normalize.benchmarks import (
    HOSPITAL_NATIONAL_CONFIGS,
    HOSPITAL_STATE_CONFIGS,
    normalize_hospital_national_benchmarks,
    normalize_hospital_state_benchmarks,
    normalize_nh_state_us_averages,
    normalize_snf_qrp_national_benchmarks,
)


class TestHospitalNationalBenchmarks:
    """Hospital -National.csv normalization."""

    def test_score_field_parsed(self) -> None:
        """T&E national: Score field parsed to avg_value."""
        rows = [
            {
                "measure_id": "IMM_3",
                "measure_name": "Healthcare workers given influenza vaccination",
                "score": "78",
                "footnote": "",
                "start_date": "10/01/2024",
                "end_date": "03/31/2025",
            },
        ]
        config = HOSPITAL_NATIONAL_CONFIGS["timely_effective_national"]
        result = normalize_hospital_national_benchmarks(rows, config, "2025-11")

        assert len(result) == 1
        assert result[0]["measure_id"] == "IMM_3"
        assert result[0]["geography_type"] == "national"
        assert result[0]["geography_code"] == "US"
        assert result[0]["avg_value"] == Decimal("78")
        assert result[0]["source"] == "Timely_and_Effective_Care-National"
        assert result[0]["source_vintage"] == "2025-11"
        assert result[0]["period_label"]  # Non-empty period label derived from dates

    def test_national_rate_field_parsed(self) -> None:
        """Complications national: National Rate field (different column name)."""
        rows = [
            {
                "measure_id": "COMP_HIP_KNEE",
                "measure_name": "Rate of complications for hip/knee",
                "national_rate": "3.6",
                "number_of_hospitals_worse": "12",
                "footnote": "",
                "start_date": "04/01/2021",
                "end_date": "03/31/2024",
            },
        ]
        config = HOSPITAL_NATIONAL_CONFIGS["complications_deaths_national"]
        result = normalize_hospital_national_benchmarks(rows, config, "2025-11")

        assert len(result) == 1
        assert result[0]["measure_id"] == "COMP_HIP_KNEE"
        assert result[0]["avg_value"] == Decimal("3.6")

    def test_unparseable_score_skipped(self) -> None:
        """'Not Applicable' scores are skipped."""
        rows = [
            {
                "measure_id": "EDAC_30_AMI",
                "national_rate": "Not Applicable",
                "start_date": "07/01/2023",
                "end_date": "06/30/2024",
            },
        ]
        config = HOSPITAL_NATIONAL_CONFIGS["readmissions_national"]
        result = normalize_hospital_national_benchmarks(rows, config, "2025-11")
        assert len(result) == 0

    def test_empty_measure_id_skipped(self) -> None:
        """Rows without a measure ID are skipped."""
        rows = [{"measure_id": "", "score": "50", "start_date": "01/01/2024", "end_date": "12/31/2024"}]
        config = HOSPITAL_NATIONAL_CONFIGS["timely_effective_national"]
        result = normalize_hospital_national_benchmarks(rows, config, "2025-11")
        assert len(result) == 0

    def test_multiple_measures(self) -> None:
        """Multiple rows produce multiple benchmark rows."""
        rows = [
            {"measure_id": "OP_10", "score": "5.9", "start_date": "07/01/2023", "end_date": "06/30/2024"},
            {"measure_id": "OP_13", "score": "1.6", "start_date": "07/01/2023", "end_date": "06/30/2024"},
        ]
        config = HOSPITAL_NATIONAL_CONFIGS["imaging_national"]
        result = normalize_hospital_national_benchmarks(rows, config, "2025-11")
        assert len(result) == 2
        ids = {r["measure_id"] for r in result}
        assert ids == {"OP_10", "OP_13"}


class TestHospitalStateBenchmarks:
    """Hospital -State.csv normalization."""

    def test_state_benchmark_parsed(self) -> None:
        """T&E state: state code extracted, score parsed."""
        rows = [
            {
                "state": "TX",
                "measure_id": "IMM_3",
                "measure_name": "test",
                "score": "74",
                "footnote": "",
                "start_date": "10/01/2024",
                "end_date": "03/31/2025",
            },
        ]
        config = HOSPITAL_STATE_CONFIGS["timely_effective_state"]
        result = normalize_hospital_state_benchmarks(rows, config, "2025-11")

        assert len(result) == 1
        assert result[0]["geography_type"] == "state"
        assert result[0]["geography_code"] == "TX"
        assert result[0]["avg_value"] == Decimal("74")

    def test_state_code_uppercased(self) -> None:
        """State codes are uppercased."""
        rows = [
            {"state": "ca", "measure_id": "OP_10", "score": "5.0",
             "start_date": "01/01/2024", "end_date": "12/31/2024"},
        ]
        config = HOSPITAL_STATE_CONFIGS["imaging_state"]
        result = normalize_hospital_state_benchmarks(rows, config, "2025-11")
        assert result[0]["geography_code"] == "CA"

    def test_missing_state_skipped(self) -> None:
        """Rows without a state are skipped."""
        rows = [
            {"state": "", "measure_id": "OP_10", "score": "5.0",
             "start_date": "01/01/2024", "end_date": "12/31/2024"},
        ]
        config = HOSPITAL_STATE_CONFIGS["imaging_state"]
        result = normalize_hospital_state_benchmarks(rows, config, "2025-11")
        assert len(result) == 0


class TestHGLMStateExclusion:
    """DEC-036: HGLM measures must NOT have state benchmark configs."""

    def test_complications_state_not_in_configs(self) -> None:
        """Complications-State has no score column — no config exists."""
        assert "complications_deaths_state" not in HOSPITAL_STATE_CONFIGS

    def test_readmissions_state_not_in_configs(self) -> None:
        """Readmissions-State has no score column — no config exists."""
        assert "readmissions_state" not in HOSPITAL_STATE_CONFIGS


class TestNHStateUSAverages:
    """NH_StateUSAverages wide-to-long normalization."""

    def test_nation_row(self) -> None:
        """NATION row produces geography_type='national', geography_code='US'."""
        rows = [
            {
                "state_or_nation": "NATION",
                "percentage_of_long_stay_residents_with_a_catheter_inserted_and_left_in_their_bladder": "1.699311",
                "processing_date": "2023-01-01",
            },
        ]
        result = normalize_nh_state_us_averages(rows, "2023-01")
        catheter = [r for r in result if r["measure_id"] == "404"]
        assert len(catheter) == 1
        assert catheter[0]["geography_type"] == "national"
        assert catheter[0]["geography_code"] == "US"
        assert catheter[0]["avg_value"] == Decimal("1.699311")

    def test_state_row(self) -> None:
        """State row produces geography_type='state' with state abbreviation."""
        rows = [
            {
                "state_or_nation": "TX",
                "percentage_of_long_stay_residents_who_lose_too_much_weight": "5.5",
                "processing_date": "2023-01-01",
            },
        ]
        result = normalize_nh_state_us_averages(rows, "2023-01")
        weight = [r for r in result if r["measure_id"] == "402"]
        assert len(weight) == 1
        assert weight[0]["geography_type"] == "state"
        assert weight[0]["geography_code"] == "TX"

    def test_unmapped_columns_ignored(self) -> None:
        """Columns not in NH_STATE_AVG_COLUMN_MAP are ignored."""
        rows = [
            {
                "state_or_nation": "NATION",
                "average_number_of_residents_per_day": "78.6",
                "number_of_fines": "2.2",
                "processing_date": "2023-01-01",
            },
        ]
        result = normalize_nh_state_us_averages(rows, "2023-01")
        # These columns are not quality measures, so not mapped.
        assert len(result) == 0

    def test_multiple_geographies_multiple_measures(self) -> None:
        """Multiple geographies × multiple measures = cross product."""
        rows = [
            {
                "state_or_nation": "NATION",
                "percentage_of_long_stay_residents_with_a_catheter_inserted_and_left_in_their_bladder": "1.7",
                "percentage_of_long_stay_residents_who_lose_too_much_weight": "6.2",
                "processing_date": "2023-01-01",
            },
            {
                "state_or_nation": "CA",
                "percentage_of_long_stay_residents_with_a_catheter_inserted_and_left_in_their_bladder": "1.4",
                "percentage_of_long_stay_residents_who_lose_too_much_weight": "5.8",
                "processing_date": "2023-01-01",
            },
        ]
        result = normalize_nh_state_us_averages(rows, "2023-01")
        assert len(result) == 4  # 2 geos × 2 measures


class TestSNFQRPNationalBenchmarks:
    """SNF QRP National Data normalization."""

    def test_nation_row_parsed(self) -> None:
        """NATION CCN rows produce national benchmarks."""
        rows = [
            {
                "cms_certification_number_(ccn)": "NATION",
                "measure_code": "S_001_03_NATL_RATE",
                "score": "98.8",
                "footnote": "",
                "start_date": "04/01/2021",
                "end_date": "03/31/2022",
            },
        ]
        result = normalize_snf_qrp_national_benchmarks(rows, "2023-01")
        assert len(result) == 1
        assert result[0]["measure_id"] == "S_001_03_NATL_RATE"
        assert result[0]["geography_type"] == "national"
        assert result[0]["avg_value"] == Decimal("98.8")
        assert result[0]["source"] == "SNF_QRP_National"

    def test_non_nation_rows_skipped(self) -> None:
        """Provider-level rows (non-NATION CCN) are skipped."""
        rows = [
            {
                "cms_certification_number_(ccn)": "015001",
                "measure_code": "S_001_03_NATL_RATE",
                "score": "99.0",
                "start_date": "04/01/2021",
                "end_date": "03/31/2022",
            },
        ]
        result = normalize_snf_qrp_national_benchmarks(rows, "2023-01")
        assert len(result) == 0

    def test_unparseable_score_skipped(self) -> None:
        """Non-numeric scores are skipped."""
        rows = [
            {
                "cms_certification_number_(ccn)": "NATION",
                "measure_code": "S_006_01",
                "score": "N/A",
                "start_date": "04/01/2021",
                "end_date": "03/31/2022",
            },
        ]
        result = normalize_snf_qrp_national_benchmarks(rows, "2023-01")
        assert len(result) == 0
