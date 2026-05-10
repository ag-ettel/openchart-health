"""
Bayesian credible interval calculation for measures where CMS does not
publish interval bounds.

Applies to measures where:
  - risk_adjustment_model in ("NONE", "PATIENT_MIX_ADJUSTMENT")
  - numerator_denominator_published == True

Uses a Beta-Binomial conjugate model with a tiered informative prior:
  1. State average rate (preferred — most specific population context)
  2. National average rate (fallback — available for all measures)
  3. Uninformative Beta(1, 1) uniform prior (last resort)

See DEC-029 in docs/pipeline_decisions.md and docs/data_dictionary.md
§ Interval Estimation Methodology for full specification.

PATIENT_MIX_ADJUSTMENT measures (HCAHPS): CMS adjusts the published
percentages for patient mix but does not publish interval bounds. The
sampling uncertainty from finite survey counts is real and material. We
treat the adjusted top-box percentage as a binomial proportion with
n = completed surveys. The numerator is derived: round(percentage * n / 100).
See DEC-039 in docs/pipeline_decisions.md.

This module is called by the transform layer after normalization has
populated numeric_value, denominator, state_avg, and national_avg.
CMS-published intervals (HGLM, SIR, OTHER with cms_ci_published=True)
are never overwritten — this module only fills in intervals where
confidence_interval_lower/upper are currently null.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

from scipy.stats import beta as beta_dist

from pipeline.config import (
    CREDIBLE_INTERVAL_CONCENTRATION,
    CREDIBLE_INTERVAL_LEVEL,
)

logger = logging.getLogger(__name__)

# Prior source labels matching text-templates.md template variables.
PRIOR_STATE_AVG = "state average"
PRIOR_NATIONAL_AVG = "national average"
PRIOR_UNINFORMATIVE = "minimally informative"

# Quantile boundaries for the credible interval.
_LOWER_QUANTILE = (1 - CREDIBLE_INTERVAL_LEVEL) / 2  # 0.025
_UPPER_QUANTILE = 1 - _LOWER_QUANTILE                # 0.975

# Decimal precision for output (matches database decimal(12,4)).
_DECIMAL_PLACES = Decimal("0.0001")


@dataclass(frozen=True, slots=True)
class CredibleInterval:
    """Result of a Bayesian credible interval calculation."""

    lower: Decimal
    upper: Decimal
    prior_source: str  # "state average", "national average", or "minimally informative"
    ci_source: str = "calculated"  # Always "calculated" for this module


def _select_prior(
    kappa: int,
    state_avg: Optional[Decimal],
    national_avg: Optional[Decimal],
) -> tuple[float, float, str]:
    """Select Beta prior parameters using the tiered hierarchy.

    Returns (alpha_prior, beta_prior, prior_source_label).

    Prior hierarchy (DEC-029):
      1. State average → Beta(κ·p, κ·(1−p))
      2. National average → Beta(κ·p, κ·(1−p))
      3. Neither → Beta(1, 1) (uninformative uniform)

    Parameters
    ----------
    kappa : int
        Concentration parameter (pseudo-observations). Currently 10.
    state_avg : Decimal or None
        State average rate as a proportion (0-1 scale) or percentage
        (0-100 scale). None if unavailable.
    national_avg : Decimal or None
        National average rate, same scale considerations as state_avg.
    """
    for avg, label in [
        (state_avg, PRIOR_STATE_AVG),
        (national_avg, PRIOR_NATIONAL_AVG),
    ]:
        if avg is not None:
            p = float(avg)
            # CMS rates may be on 0-100 scale; convert to proportion.
            if p > 1.0:
                p = p / 100.0
            # Guard against degenerate priors (p=0 or p=1).
            p = max(1e-6, min(1.0 - 1e-6, p))
            alpha_prior = kappa * p
            beta_prior = kappa * (1.0 - p)
            return alpha_prior, beta_prior, label

    # Uninformative uniform prior.
    return 1.0, 1.0, PRIOR_UNINFORMATIVE


def calculate_credible_interval(
    numerator: int,
    denominator: int,
    state_avg: Optional[Decimal] = None,
    national_avg: Optional[Decimal] = None,
) -> Optional[CredibleInterval]:
    """Calculate a 95% Bayesian credible interval for a binomial rate measure.

    Parameters
    ----------
    numerator : int
        Observed count of events (x). Must be >= 0.
    denominator : int
        Total observations (n). Must be > 0.
    state_avg : Decimal or None
        State average rate for this measure. Preferred prior source.
        May be on 0-1 or 0-100 scale (auto-detected).
    national_avg : Decimal or None
        National average rate. Fallback prior source.
        May be on 0-1 or 0-100 scale (auto-detected).

    Returns
    -------
    CredibleInterval or None
        The interval bounds and prior metadata. None if inputs are invalid.

    Notes
    -----
    Model: Beta-Binomial conjugate.
      Prior: Beta(α₀, β₀) selected via _select_prior()
      Posterior: Beta(α₀ + x, β₀ + n − x)
      Interval: 2.5th and 97.5th percentiles of posterior

    The posterior mean (α₀ + x) / (α₀ + β₀ + n) is a weighted average
    of the prior mean and the observed rate, with the prior contributing
    κ pseudo-observations. For n >> κ, the posterior converges to the
    observed rate. For n << κ, the posterior is pulled toward the prior.
    """
    if denominator <= 0:
        logger.warning(
            "Cannot calculate credible interval: denominator=%d (must be > 0)",
            denominator,
        )
        return None

    if numerator < 0:
        logger.warning(
            "Cannot calculate credible interval: numerator=%d (must be >= 0)",
            numerator,
        )
        return None

    if numerator > denominator:
        logger.warning(
            "Numerator (%d) exceeds denominator (%d) — clamping to denominator",
            numerator,
            denominator,
        )
        numerator = denominator

    alpha_prior, beta_prior, prior_source = _select_prior(
        CREDIBLE_INTERVAL_CONCENTRATION, state_avg, national_avg,
    )

    # Posterior parameters.
    alpha_post = alpha_prior + numerator
    beta_post = beta_prior + (denominator - numerator)

    # Posterior quantiles.
    lower_raw = beta_dist.ppf(_LOWER_QUANTILE, alpha_post, beta_post)
    upper_raw = beta_dist.ppf(_UPPER_QUANTILE, alpha_post, beta_post)

    # Convert to Decimal with 4 decimal places (Rule 10: no float for rates).
    # Values are proportions on [0, 1]. The export layer scales to match
    # the measure's unit (e.g., multiply by 100 for percentage display).
    lower = Decimal(str(lower_raw)).quantize(_DECIMAL_PLACES, rounding=ROUND_HALF_UP)
    upper = Decimal(str(upper_raw)).quantize(_DECIMAL_PLACES, rounding=ROUND_HALF_UP)

    return CredibleInterval(
        lower=lower,
        upper=upper,
        prior_source=prior_source,
    )


_CI_ELIGIBLE_MODELS = {"NONE", "PATIENT_MIX_ADJUSTMENT"}


def is_ci_calculable(
    risk_adjustment_model: Optional[str],
    cms_ci_published: Optional[bool],
    numerator_denominator_published: Optional[bool],
) -> bool:
    """Determine if a Bayesian credible interval should be calculated.

    Returns True only when:
      - CMS does NOT already publish interval bounds
      - The measure uses a CI-eligible risk adjustment model
      - Numerator and denominator are available (or derivable) from CMS data

    Parameters
    ----------
    risk_adjustment_model : str or None
        From MEASURE_REGISTRY. Must be in _CI_ELIGIBLE_MODELS.
        "NONE" = unadjusted raw rate.
        "PATIENT_MIX_ADJUSTMENT" = HCAHPS patient-mix adjusted percentage
        (DEC-039: sampling uncertainty from finite surveys is real; numerator
        derived from adjusted percentage × survey count).
    cms_ci_published : bool or None
        True if CMS publishes interval bounds. None = REVIEW_NEEDED.
    numerator_denominator_published : bool or None
        True if raw counts are in the CMS download. None = REVIEW_NEEDED.
    """
    # Never overwrite CMS-published intervals.
    if cms_ci_published is True:
        return False

    # None (REVIEW_NEEDED) on any field prevents calculation.
    if cms_ci_published is None or numerator_denominator_published is None:
        return False

    return (
        risk_adjustment_model in _CI_ELIGIBLE_MODELS
        and numerator_denominator_published is True
    )


def determine_ci_source(
    cms_ci_published: Optional[bool],
) -> Optional[str]:
    """Determine the ci_source label for a measure value row.

    Returns
    -------
    str or None
        "cms_published" if CMS provides the interval.
        "calculated" if we compute it via Beta-Binomial.
        None if no interval is available.
    """
    if cms_ci_published is True:
        return "cms_published"
    # The caller determines whether calculation is applicable.
    # This function is called after is_ci_calculable() returns True.
    return "calculated"
