"""Tests for pipeline.normalize.common — shared normalizer infrastructure.

Coverage target: 100% (testing.md). These functions sit between raw CMS data and
the database. Every edge case caught here prevents a patient-facing data error.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from pipeline.normalize.common import (
    detect_suppression_state,
    derive_period_label,
    footnote_texts,
    is_count_suppressed,
    is_suppressed,
    normalize_compared_to_national,
    normalize_measure_row,
    parse_date,
    parse_decimal,
    parse_footnote_codes,
    parse_int,
)


# =========================================================================
# Suppression detection
# =========================================================================


class TestIsSuppressed:
    def test_not_available(self) -> None:
        assert is_suppressed("Not Available") is True

    def test_not_applicable(self) -> None:
        assert is_suppressed("Not Applicable") is True

    def test_na(self) -> None:
        assert is_suppressed("N/A") is True

    def test_case_insensitive(self) -> None:
        assert is_suppressed("not available") is True
        assert is_suppressed("NOT AVAILABLE") is True

    def test_whitespace(self) -> None:
        assert is_suppressed("  Not Available  ") is True

    def test_numeric_not_suppressed(self) -> None:
        assert is_suppressed("12.5") is False

    def test_empty_not_suppressed(self) -> None:
        assert is_suppressed("") is False

    def test_categorical_not_suppressed(self) -> None:
        assert is_suppressed("low") is False
        assert is_suppressed("very high") is False


class TestIsCountSuppressed:
    def test_too_few_to_report(self) -> None:
        assert is_count_suppressed("Too Few to Report") is True

    def test_na(self) -> None:
        assert is_count_suppressed("N/A") is True

    def test_case_insensitive(self) -> None:
        assert is_count_suppressed("too few to report") is True

    def test_numeric_not_suppressed(self) -> None:
        assert is_count_suppressed("234") is False


class TestDetectSuppressionState:
    def test_normal_value(self) -> None:
        suppressed, not_reported, reason = detect_suppression_state("12.5")
        assert suppressed is False
        assert not_reported is False
        assert reason is None

    def test_suppressed_not_available(self) -> None:
        suppressed, not_reported, reason = detect_suppression_state(
            "Not Available", "Number of Cases Too Small", "1"
        )
        assert suppressed is True
        assert not_reported is False
        assert reason == "Number of cases too small"

    def test_suppressed_from_footnote_13(self) -> None:
        suppressed, not_reported, reason = detect_suppression_state(
            "Not Available", "Not Available", "13"
        )
        assert suppressed is True
        assert reason == "Results cannot be calculated for this reporting period"

    def test_not_reported_footnote_5(self) -> None:
        suppressed, not_reported, reason = detect_suppression_state(
            "Not Available", "", "5"
        )
        assert suppressed is False
        assert not_reported is True
        assert "not available" in reason.lower()

    def test_empty_score_not_suppressed(self) -> None:
        # Empty string is not a suppression sentinel — it's missing data
        suppressed, not_reported, reason = detect_suppression_state("")
        assert suppressed is False
        assert not_reported is False


# =========================================================================
# Footnote parsing
# =========================================================================


class TestParseFootnoteCodes:
    def test_single_code(self) -> None:
        assert parse_footnote_codes("1") == [1]

    def test_multiple_codes(self) -> None:
        assert parse_footnote_codes("1, 28") == [1, 28]

    def test_triple_codes(self) -> None:
        assert parse_footnote_codes("3, 13, 29") == [3, 13, 29]

    def test_empty(self) -> None:
        assert parse_footnote_codes("") == []

    def test_whitespace(self) -> None:
        assert parse_footnote_codes("  ") == []

    def test_non_integer_skipped(self) -> None:
        # HACRP uses "a" and "*" as footnotes
        assert parse_footnote_codes("a") == []

    def test_mixed_integer_and_non(self) -> None:
        assert parse_footnote_codes("1, a, 28") == [1, 28]


class TestFootnoteTexts:
    def test_known_code(self) -> None:
        texts = footnote_texts([1])
        assert len(texts) == 1
        assert "too few" in texts[0].lower()

    def test_multiple_codes(self) -> None:
        texts = footnote_texts([1, 29])
        assert len(texts) == 2

    def test_unknown_code(self) -> None:
        texts = footnote_texts([999])
        assert len(texts) == 1
        assert "999" in texts[0]

    def test_empty(self) -> None:
        assert footnote_texts([]) == []


# =========================================================================
# compared_to_national mapping
# =========================================================================


class TestNormalizeComparedToNational:
    # Rate phrasing (CompDeaths)
    def test_better_rate(self) -> None:
        assert normalize_compared_to_national("Better Than the National Rate") == "BETTER"

    def test_worse_rate(self) -> None:
        assert normalize_compared_to_national("Worse Than the National Rate") == "WORSE"

    def test_no_different_rate(self) -> None:
        assert normalize_compared_to_national("No Different Than the National Rate") == "NO_DIFFERENT"

    # Value phrasing (PSI_90)
    def test_no_different_value(self) -> None:
        assert normalize_compared_to_national("No Different Than the National Value") == "NO_DIFFERENT"

    # Benchmark phrasing (HAI)
    def test_better_benchmark(self) -> None:
        assert normalize_compared_to_national("Better than the National Benchmark") == "BETTER"

    def test_no_different_benchmark(self) -> None:
        # Note: HAI uses "No Different than" (lowercase t) not "Than"
        assert normalize_compared_to_national("No Different than National Benchmark") == "NO_DIFFERENT"

    # Days phrasing (EDAC)
    def test_fewer_days(self) -> None:
        assert normalize_compared_to_national("Fewer Days Than Average per 100 Discharges") == "BETTER"

    def test_more_days(self) -> None:
        assert normalize_compared_to_national("More Days Than Average per 100 Discharges") == "WORSE"

    def test_average_days(self) -> None:
        assert normalize_compared_to_national("Average Days per 100 Discharges") == "NO_DIFFERENT"

    # Expected phrasing (OP_36)
    def test_better_expected(self) -> None:
        assert normalize_compared_to_national("Better than expected") == "BETTER"

    def test_worse_expected(self) -> None:
        assert normalize_compared_to_national("Worse than expected") == "WORSE"

    def test_no_different_expected(self) -> None:
        assert normalize_compared_to_national("No Different than expected") == "NO_DIFFERENT"

    # Suppression sentinels
    def test_too_few_cases(self) -> None:
        assert normalize_compared_to_national("Number of Cases Too Small") == "TOO_FEW_CASES"

    def test_too_few_cases_lowercase(self) -> None:
        # CMS inconsistent capitalization (confirmed in 632h-zaca)
        assert normalize_compared_to_national("Number of cases too small") == "TOO_FEW_CASES"

    def test_not_available(self) -> None:
        assert normalize_compared_to_national("Not Available") == "NOT_AVAILABLE"

    # Edge cases
    def test_none(self) -> None:
        assert normalize_compared_to_national(None) is None

    def test_empty(self) -> None:
        assert normalize_compared_to_national("") is None

    def test_whitespace(self) -> None:
        assert normalize_compared_to_national("  ") is None

    def test_unknown_stored_not_rejected(self) -> None:
        # Unknown values are logged and stored, not discarded
        result = normalize_compared_to_national("Some New CMS Phrasing")
        assert result is not None  # Not rejected
        assert isinstance(result, str)


# =========================================================================
# Date parsing
# =========================================================================


class TestParseDate:
    def test_mm_dd_yyyy(self) -> None:
        assert parse_date("07/01/2022") == date(2022, 7, 1)

    def test_yyyy_mm_dd(self) -> None:
        assert parse_date("2022-07-01") == date(2022, 7, 1)

    def test_none(self) -> None:
        assert parse_date(None) is None

    def test_empty(self) -> None:
        assert parse_date("") is None

    def test_whitespace(self) -> None:
        assert parse_date("  ") is None

    def test_invalid(self) -> None:
        assert parse_date("not-a-date") is None

    def test_leading_trailing_whitespace(self) -> None:
        assert parse_date(" 07/01/2022 ") == date(2022, 7, 1)


class TestDerivePeriodLabel:
    def test_from_dates(self) -> None:
        label = derive_period_label(date(2022, 7, 1), date(2024, 6, 30))
        assert label == "2022-07 to 2024-06"

    def test_raw_period_preferred(self) -> None:
        label = derive_period_label(date(2022, 7, 1), date(2024, 6, 30), "2024Q4-2025Q3")
        assert label == "2024Q4-2025Q3"

    def test_no_dates(self) -> None:
        assert derive_period_label(None, None) == "unknown"


# =========================================================================
# Value conversion
# =========================================================================


class TestParseDecimal:
    def test_integer(self) -> None:
        assert parse_decimal("12") == Decimal("12")

    def test_decimal(self) -> None:
        assert parse_decimal("12.5") == Decimal("12.5")

    def test_high_precision(self) -> None:
        assert parse_decimal("0.9875") == Decimal("0.9875")

    def test_not_available(self) -> None:
        assert parse_decimal("Not Available") is None

    def test_na(self) -> None:
        assert parse_decimal("N/A") is None

    def test_none(self) -> None:
        assert parse_decimal(None) is None

    def test_empty(self) -> None:
        assert parse_decimal("") is None

    def test_negative(self) -> None:
        assert parse_decimal("-0.5") == Decimal("-0.5")


class TestParseInt:
    def test_normal(self) -> None:
        assert parse_int("234") == 234

    def test_comma_formatted(self) -> None:
        assert parse_int("1,234") == 1234

    def test_not_available(self) -> None:
        assert parse_int("Not Available") is None

    def test_none(self) -> None:
        assert parse_int(None) is None

    def test_empty(self) -> None:
        assert parse_int("") is None


# =========================================================================
# normalize_measure_row (integration of all components)
# =========================================================================


class TestNormalizeMeasureRow:
    """Test the shared row-level normalization pass."""

    def _make_row(self, **overrides: str) -> dict[str, str]:
        """Build a minimal raw CMS row with defaults."""
        base = {
            "facility_id": "010001",
            "measure_id": "MORT_30_AMI",
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

    def test_normal_row(self) -> None:
        result = normalize_measure_row(self._make_row())
        assert result["provider_id"] == "010001"
        assert result["measure_id"] == "MORT_30_AMI"
        assert result["numeric_value"] == Decimal("12.5")
        assert result["confidence_interval_lower"] == Decimal("10.1")
        assert result["confidence_interval_upper"] == Decimal("15.3")
        assert result["compared_to_national"] == "NO_DIFFERENT"
        assert result["suppressed"] is False
        assert result["not_reported"] is False
        assert result["period_label"] == "2022-07 to 2024-06"
        assert result["denominator"] == 523

    def test_suppressed_row(self) -> None:
        result = normalize_measure_row(self._make_row(
            score="Not Available",
            denominator="Not Available",
            lower_estimate="Not Available",
            higher_estimate="Not Available",
            compared_to_national="Number of Cases Too Small",
            footnote="1",
        ))
        assert result["suppressed"] is True
        assert result["numeric_value"] is None
        assert result["confidence_interval_lower"] is None
        assert result["compared_to_national"] == "TOO_FEW_CASES"
        assert 1 in result["footnote_codes"]
        assert result["suppression_reason"] is not None

    def test_not_reported_row(self) -> None:
        result = normalize_measure_row(self._make_row(
            score="Not Available",
            footnote="5",
        ))
        assert result["not_reported"] is True
        assert result["suppressed"] is False

    def test_provider_id_zero_padded(self) -> None:
        result = normalize_measure_row(self._make_row(facility_id="1001"))
        assert result["provider_id"] == "001001"

    def test_empty_footnote(self) -> None:
        result = normalize_measure_row(self._make_row(footnote=""))
        assert result["footnote_codes"] is None
        assert result["footnote_text"] is None

    def test_multi_footnote(self) -> None:
        result = normalize_measure_row(self._make_row(footnote="1, 28"))
        assert result["footnote_codes"] == [1, 28]
        assert len(result["footnote_text"]) == 2

    def test_stratification_default(self) -> None:
        result = normalize_measure_row(self._make_row())
        assert result["stratification"] == ""

    def test_raw_value_preserved(self) -> None:
        """Rule 7: raw value exactly as received."""
        result = normalize_measure_row(self._make_row(score="12.5"))
        assert result["raw_value"] == "12.5"

    def test_raw_value_preserved_when_suppressed(self) -> None:
        result = normalize_measure_row(self._make_row(score="Not Available"))
        assert result["raw_value"] == "Not Available"
