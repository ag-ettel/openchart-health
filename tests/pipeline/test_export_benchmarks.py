"""Tests for benchmark resolution and overlap_flag computation in build_json.

Covers:
  - _resolve_benchmark: exact match (with and without index)
  - _resolve_benchmark: fallback to most recent period when exact miss
  - _resolve_benchmark: index path matches linear path
  - _resolve_benchmark: returns (None, None) when no benchmark exists
  - _build_benchmark_index: groups by (measure_id, geo_type, geo_code)
  - _build_benchmark_index: sorts periods descending so [0] is most recent
  - _compute_overlap_flag: True when CI contains national_avg
  - _compute_overlap_flag: False when national_avg outside CI
  - _compute_overlap_flag: None on any null input

These are pure functions — no DB required.
"""

from decimal import Decimal

from pipeline.export.build_json import (
    _build_benchmark_index,
    _compute_overlap_flag,
    _resolve_benchmark,
)


class TestResolveBenchmark:
    """Benchmark lookup with same-measure period fallback."""

    def test_exact_period_match(self) -> None:
        lookup = {
            ("MORT_30_AMI", "national", "US", "2024-07-01 to 2025-06-30"): {
                "avg_value": Decimal("12.5"),
                "period_label": "2024-07-01 to 2025-06-30",
            },
        }
        avg, period = _resolve_benchmark(
            lookup, "MORT_30_AMI", "national", "US",
            "2024-07-01 to 2025-06-30",
        )
        assert avg == Decimal("12.5")
        assert period == "2024-07-01 to 2025-06-30"

    def test_period_miss_falls_back_to_most_recent(self) -> None:
        """When the exact period misses, returns the most recent benchmark."""
        lookup = {
            ("MORT_30_AMI", "national", "US", "2022-07-01 to 2023-06-30"): {
                "avg_value": Decimal("13.0"),
                "period_label": "2022-07-01 to 2023-06-30",
            },
            ("MORT_30_AMI", "national", "US", "2024-07-01 to 2025-06-30"): {
                "avg_value": Decimal("12.5"),
                "period_label": "2024-07-01 to 2025-06-30",
            },
        }
        avg, period = _resolve_benchmark(
            lookup, "MORT_30_AMI", "national", "US",
            "different-period-not-in-lookup",
        )
        # Picks the most recent (2024-07-01 to 2025-06-30 sorts after 2022-...)
        assert avg == Decimal("12.5")
        assert period == "2024-07-01 to 2025-06-30"

    def test_no_benchmark_returns_nulls(self) -> None:
        avg, period = _resolve_benchmark({}, "MORT_30_AMI", "national", "US", "anything")
        assert avg is None
        assert period is None

    def test_state_lookup_isolated_from_national(self) -> None:
        """Resolving 'state' must not return a 'national' benchmark by accident."""
        lookup = {
            ("HAI_1_SIR", "national", "US", "2025-Q4"): {
                "avg_value": Decimal("0.85"),
                "period_label": "2025-Q4",
            },
        }
        avg, period = _resolve_benchmark(lookup, "HAI_1_SIR", "state", "TX", "2025-Q4")
        assert avg is None
        assert period is None

    def test_different_measure_isolated(self) -> None:
        lookup = {
            ("OP-8", "national", "US", "2025-Q4"): {
                "avg_value": Decimal("70.0"),
                "period_label": "2025-Q4",
            },
        }
        avg, period = _resolve_benchmark(
            lookup, "OP-10", "national", "US", "2025-Q4",
        )
        assert avg is None
        assert period is None


class TestComputeOverlapFlag:
    """overlap_flag = True when CI contains national_avg."""

    def test_ci_contains_national_avg(self) -> None:
        # ci_lower=10, ci_upper=14, national_avg=12 → True
        assert _compute_overlap_flag(Decimal("10"), Decimal("14"), Decimal("12")) is True

    def test_national_avg_at_lower_bound(self) -> None:
        # Inclusive on the lower bound
        assert _compute_overlap_flag(Decimal("10"), Decimal("14"), Decimal("10")) is True

    def test_national_avg_at_upper_bound(self) -> None:
        assert _compute_overlap_flag(Decimal("10"), Decimal("14"), Decimal("14")) is True

    def test_national_avg_below_ci(self) -> None:
        assert _compute_overlap_flag(Decimal("10"), Decimal("14"), Decimal("9.9")) is False

    def test_national_avg_above_ci(self) -> None:
        assert _compute_overlap_flag(Decimal("10"), Decimal("14"), Decimal("14.1")) is False

    def test_null_ci_lower_returns_none(self) -> None:
        assert _compute_overlap_flag(None, Decimal("14"), Decimal("12")) is None

    def test_null_ci_upper_returns_none(self) -> None:
        assert _compute_overlap_flag(Decimal("10"), None, Decimal("12")) is None

    def test_null_national_avg_returns_none(self) -> None:
        assert _compute_overlap_flag(Decimal("10"), Decimal("14"), None) is None

    def test_accepts_string_inputs(self) -> None:
        # The export reads from JSON-decoded values which may be float/str
        assert _compute_overlap_flag("10.0", "14.0", "12.5") is True


class TestBuildBenchmarkIndex:
    """Index-based benchmark lookup for fast period fallback."""

    def test_groups_by_measure_geo(self) -> None:
        lookup = {
            ("MORT_30_AMI", "national", "US", "P1"): {"avg_value": Decimal("12.0"), "period_label": "P1"},
            ("MORT_30_AMI", "national", "US", "P2"): {"avg_value": Decimal("12.5"), "period_label": "P2"},
            ("MORT_30_AMI", "state", "TX", "P1"): {"avg_value": Decimal("11.0"), "period_label": "P1"},
            ("HAI_1_SIR", "national", "US", "P1"): {"avg_value": Decimal("0.85"), "period_label": "P1"},
        }
        index = _build_benchmark_index(lookup)
        assert ("MORT_30_AMI", "national", "US") in index
        assert ("MORT_30_AMI", "state", "TX") in index
        assert ("HAI_1_SIR", "national", "US") in index
        # MORT national has 2 periods; state has 1
        assert len(index[("MORT_30_AMI", "national", "US")]) == 2
        assert len(index[("MORT_30_AMI", "state", "TX")]) == 1

    def test_periods_sorted_most_recent_first(self) -> None:
        """[0] must be the most recent period after indexing."""
        lookup = {
            ("M", "national", "US", "2020-01"): {"avg_value": Decimal("1.0"), "period_label": "2020-01"},
            ("M", "national", "US", "2024-01"): {"avg_value": Decimal("2.0"), "period_label": "2024-01"},
            ("M", "national", "US", "2022-01"): {"avg_value": Decimal("3.0"), "period_label": "2022-01"},
        }
        index = _build_benchmark_index(lookup)
        periods = index[("M", "national", "US")]
        assert periods[0][0] == "2024-01"  # most recent first
        assert periods[-1][0] == "2020-01"

    def test_index_path_matches_linear_path(self) -> None:
        """_resolve_benchmark with index produces same result as without."""
        lookup = {
            ("M", "national", "US", "2024-01"): {"avg_value": Decimal("2.0"), "period_label": "2024-01"},
            ("M", "national", "US", "2022-01"): {"avg_value": Decimal("3.0"), "period_label": "2022-01"},
        }
        index = _build_benchmark_index(lookup)

        # Both should resolve to same fallback result on a missing period
        avg_lin, period_lin = _resolve_benchmark(lookup, "M", "national", "US", "missing")
        avg_idx, period_idx = _resolve_benchmark(lookup, "M", "national", "US", "missing", index=index)
        assert avg_lin == avg_idx == Decimal("2.0")
        assert period_lin == period_idx == "2024-01"

        # Both should resolve to same exact match
        avg_lin, period_lin = _resolve_benchmark(lookup, "M", "national", "US", "2022-01")
        avg_idx, period_idx = _resolve_benchmark(lookup, "M", "national", "US", "2022-01", index=index)
        assert avg_lin == avg_idx == Decimal("3.0")

    def test_empty_lookup_yields_empty_index(self) -> None:
        assert _build_benchmark_index({}) == {}
