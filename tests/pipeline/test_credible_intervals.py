"""
Tests for pipeline/transform/credible_intervals.py

Covers:
  - Prior selection hierarchy (state → national → uninformative)
  - Posterior calculation correctness against known Beta quantiles
  - Edge cases (zero numerator, full denominator, small samples)
  - Shrinkage behavior (small n pulled toward prior)
  - Guard rails (invalid inputs, numerator > denominator)
  - is_ci_calculable() eligibility logic
  - Scale auto-detection (0-1 vs 0-100)
"""

from decimal import Decimal

import pytest
from scipy.stats import beta as beta_dist

from pipeline.transform.credible_intervals import (
    PRIOR_NATIONAL_AVG,
    PRIOR_STATE_AVG,
    PRIOR_UNINFORMATIVE,
    CredibleInterval,
    calculate_credible_interval,
    determine_ci_source,
    is_ci_calculable,
)


class TestPriorSelectionHierarchy:
    """Prior selection: state avg > national avg > uninformative."""

    def test_state_avg_preferred_over_national(self) -> None:
        """When both state and national averages are available, use state."""
        result = calculate_credible_interval(
            numerator=50,
            denominator=200,
            state_avg=Decimal("0.30"),
            national_avg=Decimal("0.25"),
        )
        assert result is not None
        assert result.prior_source == PRIOR_STATE_AVG

    def test_national_avg_fallback_when_no_state(self) -> None:
        """When only national average is available, use it."""
        result = calculate_credible_interval(
            numerator=50,
            denominator=200,
            state_avg=None,
            national_avg=Decimal("0.25"),
        )
        assert result is not None
        assert result.prior_source == PRIOR_NATIONAL_AVG

    def test_uninformative_when_no_averages(self) -> None:
        """When neither average is available, use Beta(1,1)."""
        result = calculate_credible_interval(
            numerator=50,
            denominator=200,
            state_avg=None,
            national_avg=None,
        )
        assert result is not None
        assert result.prior_source == PRIOR_UNINFORMATIVE

    def test_state_none_national_none_explicit(self) -> None:
        """Explicit None for both averages produces uninformative prior."""
        result = calculate_credible_interval(
            numerator=10,
            denominator=100,
        )
        assert result is not None
        assert result.prior_source == PRIOR_UNINFORMATIVE


class TestPosteriorCorrectness:
    """Verify interval bounds match direct scipy Beta quantile computation."""

    def test_known_posterior_uninformative(self) -> None:
        """With Beta(1,1) prior, posterior is Beta(1+x, 1+n-x)."""
        x, n = 30, 100
        result = calculate_credible_interval(numerator=x, denominator=n)
        assert result is not None

        # Manual computation with uninformative prior.
        alpha_post = 1.0 + x
        beta_post = 1.0 + (n - x)
        expected_lower = beta_dist.ppf(0.025, alpha_post, beta_post)
        expected_upper = beta_dist.ppf(0.975, alpha_post, beta_post)

        assert abs(float(result.lower) - expected_lower) < 0.001
        assert abs(float(result.upper) - expected_upper) < 0.001

    def test_known_posterior_with_state_avg(self) -> None:
        """With state avg prior, posterior uses κ=10 informative prior."""
        x, n = 30, 100
        state_p = 0.25
        kappa = 10
        result = calculate_credible_interval(
            numerator=x,
            denominator=n,
            state_avg=Decimal(str(state_p)),
        )
        assert result is not None

        alpha_post = kappa * state_p + x
        beta_post = kappa * (1 - state_p) + (n - x)
        expected_lower = beta_dist.ppf(0.025, alpha_post, beta_post)
        expected_upper = beta_dist.ppf(0.975, alpha_post, beta_post)

        assert abs(float(result.lower) - expected_lower) < 0.001
        assert abs(float(result.upper) - expected_upper) < 0.001

    def test_interval_contains_observed_rate(self) -> None:
        """The 95% CI should contain the observed rate for moderate samples."""
        x, n = 50, 200
        observed_rate = x / n
        result = calculate_credible_interval(numerator=x, denominator=n)
        assert result is not None
        assert float(result.lower) <= observed_rate <= float(result.upper)

    def test_lower_less_than_upper(self) -> None:
        """Lower bound must always be less than upper bound."""
        for x, n in [(0, 10), (5, 10), (10, 10), (1, 1000), (999, 1000)]:
            result = calculate_credible_interval(numerator=x, denominator=n)
            assert result is not None
            assert result.lower < result.upper, f"Failed for x={x}, n={n}"


class TestShrinkageBehavior:
    """Small samples should be pulled toward the prior mean."""

    def test_small_sample_shrunk_toward_prior(self) -> None:
        """With n=3 and x=3 (100% observed), posterior mean < 1.0."""
        result = calculate_credible_interval(
            numerator=3,
            denominator=3,
            national_avg=Decimal("0.25"),
        )
        assert result is not None
        # The posterior mean should be pulled below 1.0 by the prior.
        posterior_mean = (10 * 0.25 + 3) / (10 + 3)
        assert posterior_mean < 1.0  # Sanity check on the math.
        # Upper bound of 95% CI should be < 1.0 for informative prior.
        assert float(result.upper) < 1.0

    def test_large_sample_dominates_prior(self) -> None:
        """With n=1000, the prior has negligible effect."""
        x, n = 300, 1000
        observed_rate = x / n

        result_with_prior = calculate_credible_interval(
            numerator=x,
            denominator=n,
            national_avg=Decimal("0.50"),  # Very different from observed 0.30
        )
        result_no_prior = calculate_credible_interval(
            numerator=x,
            denominator=n,
        )
        assert result_with_prior is not None
        assert result_no_prior is not None

        # Both intervals should be very close to each other.
        assert abs(float(result_with_prior.lower) - float(result_no_prior.lower)) < 0.005
        assert abs(float(result_with_prior.upper) - float(result_no_prior.upper)) < 0.005

        # Both should be centered near the observed rate.
        midpoint = (float(result_with_prior.lower) + float(result_with_prior.upper)) / 2
        assert abs(midpoint - observed_rate) < 0.02


class TestScaleAutoDetection:
    """Averages on 0-100 scale are auto-converted to proportions."""

    def test_percentage_scale_state_avg(self) -> None:
        """State avg of 25.0 (percentage) treated same as 0.25 (proportion)."""
        result_pct = calculate_credible_interval(
            numerator=50, denominator=200,
            state_avg=Decimal("25.0"),
        )
        result_prop = calculate_credible_interval(
            numerator=50, denominator=200,
            state_avg=Decimal("0.25"),
        )
        assert result_pct is not None
        assert result_prop is not None
        assert result_pct.lower == result_prop.lower
        assert result_pct.upper == result_prop.upper
        assert result_pct.prior_source == PRIOR_STATE_AVG

    def test_proportion_scale_not_double_converted(self) -> None:
        """State avg of 0.50 is NOT divided by 100."""
        result = calculate_credible_interval(
            numerator=50, denominator=100,
            state_avg=Decimal("0.50"),
        )
        assert result is not None
        # With prior at 0.50 and observed at 0.50, posterior should
        # be centered very close to 0.50.
        midpoint = (float(result.lower) + float(result.upper)) / 2
        assert abs(midpoint - 0.50) < 0.05


class TestEdgeCases:
    """Edge cases and guard rails."""

    def test_zero_numerator(self) -> None:
        """Zero events out of n observations."""
        result = calculate_credible_interval(numerator=0, denominator=50)
        assert result is not None
        assert result.lower >= Decimal("0")
        assert result.upper > Decimal("0")  # Prior pulls away from 0.

    def test_full_denominator(self) -> None:
        """All observations are events (x == n)."""
        result = calculate_credible_interval(numerator=50, denominator=50)
        assert result is not None
        assert result.upper <= Decimal("1")
        assert result.lower < Decimal("1")  # Prior pulls away from 1.

    def test_zero_denominator_returns_none(self) -> None:
        """Cannot calculate with zero denominator."""
        result = calculate_credible_interval(numerator=0, denominator=0)
        assert result is None

    def test_negative_denominator_returns_none(self) -> None:
        """Negative denominator is invalid."""
        result = calculate_credible_interval(numerator=0, denominator=-5)
        assert result is None

    def test_negative_numerator_returns_none(self) -> None:
        """Negative numerator is invalid."""
        result = calculate_credible_interval(numerator=-1, denominator=10)
        assert result is None

    def test_numerator_exceeds_denominator_clamped(self) -> None:
        """Numerator > denominator is clamped with warning."""
        result = calculate_credible_interval(numerator=15, denominator=10)
        assert result is not None
        # Clamped to x=10, n=10 — should produce valid interval.
        assert result.lower < result.upper

    def test_single_observation(self) -> None:
        """n=1 should still produce a valid interval."""
        result = calculate_credible_interval(numerator=1, denominator=1)
        assert result is not None
        assert Decimal("0") <= result.lower < result.upper <= Decimal("1")


class TestOutputFormat:
    """Output meets schema requirements."""

    def test_decimal_precision_four_places(self) -> None:
        """Output Decimals have exactly 4 decimal places."""
        result = calculate_credible_interval(numerator=50, denominator=200)
        assert result is not None
        # Check that the Decimal has at most 4 places after the point.
        assert abs(result.lower.as_tuple().exponent) == 4  # type: ignore[arg-type]
        assert abs(result.upper.as_tuple().exponent) == 4  # type: ignore[arg-type]

    def test_ci_source_always_calculated(self) -> None:
        """ci_source is always 'calculated' for this module."""
        result = calculate_credible_interval(numerator=50, denominator=200)
        assert result is not None
        assert result.ci_source == "calculated"

    def test_bounds_between_zero_and_one(self) -> None:
        """Proportions are on [0, 1] scale."""
        result = calculate_credible_interval(numerator=50, denominator=200)
        assert result is not None
        assert Decimal("0") <= result.lower
        assert result.upper <= Decimal("1")


class TestIsCiCalculable:
    """is_ci_calculable() eligibility logic."""

    def test_raw_rate_with_counts_is_calculable(self) -> None:
        assert is_ci_calculable("NONE", False, True) is True

    def test_cms_published_not_calculable(self) -> None:
        """Never overwrite CMS-published intervals."""
        assert is_ci_calculable("NONE", True, True) is False

    def test_hglm_not_calculable(self) -> None:
        assert is_ci_calculable("HGLM", False, False) is False

    def test_sir_with_published_ci_not_calculable(self) -> None:
        assert is_ci_calculable("SIR", True, True) is False

    def test_patient_mix_not_calculable(self) -> None:
        assert is_ci_calculable("PATIENT_MIX_ADJUSTMENT", False, False) is False

    def test_none_model_without_counts_not_calculable(self) -> None:
        assert is_ci_calculable("NONE", False, False) is False

    def test_review_needed_not_calculable(self) -> None:
        """None (REVIEW_NEEDED) fields prevent calculation."""
        assert is_ci_calculable(None, None, None) is False
        assert is_ci_calculable("NONE", None, True) is False
        assert is_ci_calculable("NONE", False, None) is False


class TestDetermineCiSource:
    """determine_ci_source() label assignment."""

    def test_cms_published(self) -> None:
        assert determine_ci_source(True) == "cms_published"

    def test_calculated(self) -> None:
        assert determine_ci_source(False) == "calculated"

    def test_none_review_needed(self) -> None:
        assert determine_ci_source(None) == "calculated"
