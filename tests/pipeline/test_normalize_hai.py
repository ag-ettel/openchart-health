"""Tests for pipeline.normalize.hai — Healthcare-Associated Infections."""

from __future__ import annotations

from decimal import Decimal

import pytest

from pipeline.normalize.hai import DATASET_ID, normalize_dataset, _normalize_measure_id


# =========================================================================
# Measure ID parsing
# =========================================================================


class TestNormalizeMeasureId:
    """HAI measure IDs changed format between 2019 and 2021."""

    def test_current_sir(self) -> None:
        assert _normalize_measure_id("HAI_1_SIR") == ("HAI_1", "SIR")

    def test_current_cilower(self) -> None:
        assert _normalize_measure_id("HAI_1_CILOWER") == ("HAI_1", "CILOWER")

    def test_current_dopc(self) -> None:
        assert _normalize_measure_id("HAI_3_DOPC") == ("HAI_3", "DOPC")

    def test_2019_sir(self) -> None:
        assert _normalize_measure_id("HAI-1-SIR") == ("HAI_1", "SIR")

    def test_2019_ci_lower(self) -> None:
        assert _normalize_measure_id("HAI-1-CI-LOWER") == ("HAI_1", "CILOWER")

    def test_2019_ci_upper(self) -> None:
        assert _normalize_measure_id("HAI-2-CI-UPPER") == ("HAI_2", "CIUPPER")

    def test_2019_dopc_days(self) -> None:
        assert _normalize_measure_id("HAI-1-DOPC-DAYS") == ("HAI_1", "DOPC")

    def test_2019_numerator(self) -> None:
        assert _normalize_measure_id("HAI-5-NUMERATOR") == ("HAI_5", "NUMERATOR")

    def test_all_six_types(self) -> None:
        for n in range(1, 7):
            base, suffix = _normalize_measure_id(f"HAI_{n}_SIR")
            assert base == f"HAI_{n}"
            assert suffix == "SIR"


# =========================================================================
# Dataset normalization
# =========================================================================


def _make_hai_group(
    provider: str = "010001",
    hai_num: int = 1,
    sir: str = "1.364",
    ci_lower: str = "0.665",
    ci_upper: str = "2.504",
    dopc: str = "8275",
    eligcases: str = "6.597",
    numerator: str = "9.000",
    ctn: str = "No Different than National Benchmark",
    footnote: str = "",
    start: str = "04/01/2024",
    end: str = "03/31/2025",
) -> list[dict[str, str]]:
    """Build the 6 sub-measure rows for one HAI type."""
    base_fields = {
        "facility_id": provider,
        "compared_to_national": ctn,
        "start_date": start,
        "end_date": end,
    }
    rows = []
    for suffix, score, fn in [
        ("SIR", sir, footnote),
        ("CILOWER", ci_lower, ""),
        ("CIUPPER", ci_upper, ""),
        ("DOPC", dopc, ""),
        ("ELIGCASES", eligcases, ""),
        ("NUMERATOR", numerator, ""),
    ]:
        row = {
            **base_fields,
            "measure_id": f"HAI_{hai_num}_{suffix}",
            "measure_name": f"HAI {hai_num} {suffix}",
            "score": score,
            "footnote": fn,
        }
        rows.append(row)
    return rows


class TestNormalizeDataset:

    def test_normal_group(self) -> None:
        rows = _make_hai_group()
        results = normalize_dataset(rows)
        assert len(results) == 1
        r = results[0]
        assert r["measure_id"] == "HAI_1_SIR"
        assert r["numeric_value"] == Decimal("1.364")
        assert r["confidence_interval_lower"] == Decimal("0.665")
        assert r["confidence_interval_upper"] == Decimal("2.504")
        assert r["observed_value"] == Decimal("9.000")
        assert r["expected_value"] == Decimal("6.597")
        assert r["sample_size"] == 8275
        assert r["compared_to_national"] == "NO_DIFFERENT"
        assert r["source_dataset_id"] == DATASET_ID

    def test_suppressed_group(self) -> None:
        rows = _make_hai_group(
            sir="Not Available",
            ci_lower="Not Available",
            ci_upper="Not Available",
            ctn="Not Available",
            footnote="13",
        )
        results = normalize_dataset(rows)
        assert len(results) == 1
        r = results[0]
        assert r["suppressed"] is True
        assert r["numeric_value"] is None
        assert r["confidence_interval_lower"] is None

    def test_zero_infections_ci_lower_na(self) -> None:
        """N/A on CILOWER = zero infections, CI lower undefined. Not suppression."""
        rows = _make_hai_group(
            sir="0",
            ci_lower="N/A",
            ci_upper="1.234",
            numerator="0",
            footnote="8",
        )
        results = normalize_dataset(rows)
        assert len(results) == 1
        r = results[0]
        assert r["suppressed"] is False
        assert r["numeric_value"] == Decimal("0")
        assert r["confidence_interval_lower"] is None  # Undefined, not suppressed
        assert r["confidence_interval_upper"] == Decimal("1.234")
        assert r["observed_value"] == Decimal("0")

    def test_not_reported(self) -> None:
        rows = _make_hai_group(
            sir="Not Available",
            ci_lower="Not Available",
            ci_upper="Not Available",
            footnote="5",
        )
        results = normalize_dataset(rows)
        r = results[0]
        assert r["not_reported"] is True
        assert r["suppressed"] is False

    def test_multiple_hai_types(self) -> None:
        rows = _make_hai_group(hai_num=1) + _make_hai_group(hai_num=2, sir="0.5")
        results = normalize_dataset(rows)
        assert len(results) == 2
        ids = {r["measure_id"] for r in results}
        assert ids == {"HAI_1_SIR", "HAI_2_SIR"}

    def test_2019_era_measure_ids(self) -> None:
        """2019 uses hyphens: HAI-1-SIR, HAI-1-CI-LOWER, etc."""
        rows = [
            {"facility_id": "010001", "measure_id": "HAI-1-SIR", "score": "1.5",
             "compared_to_national": "No Different than National Benchmark",
             "footnote": "", "start_date": "04/01/2017", "end_date": "03/31/2018"},
            {"facility_id": "010001", "measure_id": "HAI-1-CI-LOWER", "score": "0.5",
             "compared_to_national": "No Different than National Benchmark",
             "footnote": "", "start_date": "04/01/2017", "end_date": "03/31/2018"},
            {"facility_id": "010001", "measure_id": "HAI-1-CI-UPPER", "score": "3.0",
             "compared_to_national": "No Different than National Benchmark",
             "footnote": "", "start_date": "04/01/2017", "end_date": "03/31/2018"},
            {"facility_id": "010001", "measure_id": "HAI-1-DOPC-DAYS", "score": "5000",
             "compared_to_national": "No Different than National Benchmark",
             "footnote": "", "start_date": "04/01/2017", "end_date": "03/31/2018"},
            {"facility_id": "010001", "measure_id": "HAI-1-ELIGCASES", "score": "4.0",
             "compared_to_national": "No Different than National Benchmark",
             "footnote": "", "start_date": "04/01/2017", "end_date": "03/31/2018"},
            {"facility_id": "010001", "measure_id": "HAI-1-NUMERATOR", "score": "6",
             "compared_to_national": "No Different than National Benchmark",
             "footnote": "", "start_date": "04/01/2017", "end_date": "03/31/2018"},
        ]
        results = normalize_dataset(rows)
        assert len(results) == 1
        r = results[0]
        assert r["measure_id"] == "HAI_1_SIR"
        assert r["numeric_value"] == Decimal("1.5")
        assert r["confidence_interval_lower"] == Decimal("0.5")
        assert r["sample_size"] == 5000

    def test_empty_input(self) -> None:
        assert normalize_dataset([]) == []

    def test_missing_sir_row_skipped(self) -> None:
        """If SIR sub-measure is missing, the group produces no output."""
        rows = [
            {"facility_id": "010001", "measure_id": "HAI_1_CILOWER", "score": "0.5",
             "compared_to_national": "", "footnote": "",
             "start_date": "04/01/2024", "end_date": "03/31/2025"},
        ]
        results = normalize_dataset(rows)
        assert len(results) == 0

    def test_compared_to_national_benchmark_phrasing(self) -> None:
        rows = _make_hai_group(ctn="Worse than the National Benchmark")
        results = normalize_dataset(rows)
        assert results[0]["compared_to_national"] == "WORSE"

    def test_better_benchmark(self) -> None:
        rows = _make_hai_group(ctn="Better than the National Benchmark")
        results = normalize_dataset(rows)
        assert results[0]["compared_to_national"] == "BETTER"

    def test_provider_id_zero_padded(self) -> None:
        rows = _make_hai_group(provider="1001")
        results = normalize_dataset(rows)
        assert results[0]["provider_id"] == "001001"


class TestFootnotes2019Format:
    """2019 footnotes include full text: '13 - Results cannot be calculated...'"""

    def test_full_text_footnote(self) -> None:
        rows = _make_hai_group(
            sir="Not Available",
            footnote="13 - Results cannot be calculated for this reporting period.",
        )
        results = normalize_dataset(rows)
        r = results[0]
        assert r["suppressed"] is True
        assert 13 in r["footnote_codes"]

    def test_compound_full_text_footnote(self) -> None:
        rows = _make_hai_group(
            sir="Not Available",
            footnote="12 - This measure does not apply to this hospital for this reporting period., 3 - Results are based on a shorter time period than required.",
        )
        results = normalize_dataset(rows)
        r = results[0]
        assert 12 in r["footnote_codes"]
        assert 3 in r["footnote_codes"]
