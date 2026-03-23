# HCAHPS Credible Interval Calculation

## Summary

Calculate approximate 95% Bayesian credible intervals for HCAHPS "Always" (or
primary positive response) percentages. CMS does not publish intervals for HCAHPS.

## Rationale

HCAHPS percentages currently display without interval estimates, making them appear
more precise than they are. A hospital with 60% "Always" from 50 surveys is much
less certain than 60% from 2,000 surveys. The credible interval makes this visible
on the histogram (blue shading) and in the stat block.

## Method

Treat the primary response as binary: "Always" vs not-"Always".

- Numerator: `numeric_value / 100 * sample_size` (approximate count of "Always")
- Denominator: `sample_size` (completed surveys)
- Model: Beta-Binomial with Beta(1,1) uninformative prior (same as DEC-029 Tier 3)
- Posterior: Beta(numerator + 1, denominator - numerator + 1)
- Interval: 2.5th and 97.5th percentiles of posterior

## Caveat

HCAHPS percentages are patient-mix adjusted by CMS. The adjusted percentage is not
a raw proportion — it has been shifted to account for patient demographics. The
credible interval calculated from the adjusted percentage and survey count will
slightly understate true uncertainty because it doesn't account for the adjustment
model's own uncertainty.

Label as: `ci_source: "calculated"`, `prior_source: "minimally informative"`.
Add a note in the methodology page: "HCAHPS interval estimates are approximate.
They reflect sampling uncertainty based on survey count but do not account for
additional uncertainty from CMS's patient-mix adjustment model."

## Pipeline Changes

1. In the transform or export layer, for measures where:
   - `measure_id` starts with `H_` and ends with `_A_P`, `_DY`, `_Y_P`, `_9_10`
   - `sample_size` is not null
   - `confidence_interval_lower` is null (CMS didn't publish one)
   Calculate and populate `confidence_interval_lower`, `confidence_interval_upper`,
   `ci_source = "calculated"`, `prior_source = "minimally informative"`.

2. Apply the same logic to trend periods once per-period CI is flowing.

## Small Sample Threshold for Surveys

Propose: 100 completed surveys (vs 30 for clinical measures). HCAHPS has higher
inherent variance than clinical rates, and CMS recommends minimum 300 surveys for
reliable estimates. A threshold of 100 triggers the amber warning while still being
below CMS's recommended minimum.

Add to `constants.ts`: `SMALL_SURVEY_THRESHOLD = 100`.

## Frontend (already partially wired)

Once CI values are populated:
- Histogram blue shading will render automatically (DistributionHistogram already
  accepts ciLower/ciUpper)
- Stat block will show "INTERVAL ESTIMATE" column automatically
- Small sample warning will trigger when survey count < threshold
