"""Disclosure completeness tests.

Validates that the correct legal disclosures fire for given measure data,
per the disclosure checklist in legal-compliance.md:

| Disclosure          | Trigger                                           |
|---------------------|---------------------------------------------------|
| 3a Site-wide        | Every page                                        |
| 3b Data attribution | Every measure group                               |
| 3c SES disclosure   | Any measure with ses_sensitivity HIGH or MODERATE  |
| 3d Multiple comp.   | Full measure profile displayed                    |
| 3e Small sample     | sample_size < SMALL_SAMPLE_THRESHOLD              |
| 3f Population ctx   | Compare page with divergent populations            |
| 3g Ownership-quality| Ownership + quality in same view                  |
| 3h CI methodology   | Calculated (non-CMS) intervals displayed           |

These tests are logic tests — they verify the disclosure determination
functions, not rendered HTML. The frontend components that render these
disclosures must call the same logic.

Antifragile design: the disclosure rules are encoded as pure functions
that take measure data and return booleans. Adding a new disclosure is
one function + one test class.
"""

from decimal import Decimal
from typing import Any

import pytest

# ─── Disclosure thresholds (must match pipeline/config.py and
#     frontend/lib/constants.ts) ────────────────────────────────────────

SMALL_SAMPLE_THRESHOLD = 30  # provisional; sync with config.py
POPULATION_COMPARABILITY_THRESHOLD_PCT = 10  # sync with config.py


# ─── Disclosure determination functions ────────────────────────────────
# These encode the rules from legal-compliance.md. When pipeline/render/
# or frontend components are built, they must call these functions (or
# equivalent logic). Until then, the functions live here as the canonical
# implementation of the disclosure rules.

def requires_ses_disclosure(measures: list[dict[str, Any]]) -> bool:
    """Return True if any measure has ses_sensitivity HIGH or MODERATE.

    Per legal-compliance.md: SES disclosure appears once per measure group
    when any measure in the group has HIGH or MODERATE sensitivity.
    """
    return any(
        m.get("ses_sensitivity") in ("HIGH", "MODERATE")
        for m in measures
    )


def requires_small_sample_caveat(measure: dict[str, Any]) -> bool:
    """Return True if the measure's sample size is below threshold.

    Per legal-compliance.md: small sample caveat appears adjacent to any
    measure where sample_size < SMALL_SAMPLE_THRESHOLD. Also fires when
    sample_size is None (unknown denominator is not reassuring).
    """
    sample_size = measure.get("sample_size")
    if sample_size is None:
        return True
    return sample_size < SMALL_SAMPLE_THRESHOLD


def requires_multiple_comparison_disclosure(measure_count: int) -> bool:
    """Return True when a full measure profile is displayed.

    Per legal-compliance.md: appears once per page when many measures are
    shown together. A profile page always shows many measures.
    """
    return measure_count > 1


def requires_ci_methodology_note(measure: dict[str, Any]) -> bool:
    """Return True when a calculated (non-CMS) interval is displayed.

    Per legal-compliance.md: CI methodology note appears when intervals
    are calculated by us rather than published by CMS.
    """
    has_ci = (
        measure.get("confidence_interval_lower") is not None
        and measure.get("confidence_interval_upper") is not None
    )
    if not has_ci:
        return False
    # If CMS published the interval, no methodology note needed
    # (we're just republishing). The ci_source field distinguishes.
    return measure.get("ci_source") != "cms_published"


def requires_population_comparability_warning(
    provider_a: dict[str, Any],
    provider_b: dict[str, Any],
) -> bool:
    """Return True when comparing providers with divergent populations.

    Per legal-compliance.md: fires when dual_eligible_proportion differs
    by more than POPULATION_COMPARABILITY_THRESHOLD_PCT, OR when either
    value is null (unknown = cannot confirm comparability).
    """
    dep_a = provider_a.get("dual_eligible_proportion")
    dep_b = provider_b.get("dual_eligible_proportion")

    # If either is null, we can't confirm comparability
    if dep_a is None or dep_b is None:
        return True

    return abs(dep_a - dep_b) > POPULATION_COMPARABILITY_THRESHOLD_PCT


def requires_ownership_quality_disclaimer(
    has_ownership_data: bool,
    has_quality_data: bool,
) -> bool:
    """Return True when ownership and quality data appear in the same view.

    Per legal-compliance.md: fires whenever both are visible, regardless
    of what the data shows.
    """
    return has_ownership_data and has_quality_data


def requires_data_attribution(measures: list[dict[str, Any]]) -> bool:
    """Return True when any measures are displayed (always True).

    Per legal-compliance.md: data attribution appears per measure group
    whenever measures are displayed. This function exists for completeness
    and to make the rule testable.
    """
    return len(measures) > 0


# ─── Tests ─────────────────────────────────────────────────────────────

class TestSESDisclosure:
    """3c: SES disclosure fires for HIGH or MODERATE ses_sensitivity."""

    def test_high_sensitivity_triggers(self) -> None:
        measures = [
            {"measure_id": "MORT_30_AMI", "ses_sensitivity": "HIGH"},
        ]
        assert requires_ses_disclosure(measures)

    def test_moderate_sensitivity_triggers(self) -> None:
        measures = [
            {"measure_id": "H_COMP_1_A_P", "ses_sensitivity": "MODERATE"},
        ]
        assert requires_ses_disclosure(measures)

    def test_low_sensitivity_does_not_trigger(self) -> None:
        measures = [
            {"measure_id": "HAI_1_SIR", "ses_sensitivity": "LOW"},
            {"measure_id": "HAI_2_SIR", "ses_sensitivity": "LOW"},
        ]
        assert not requires_ses_disclosure(measures)

    def test_unknown_sensitivity_does_not_trigger(self) -> None:
        measures = [
            {"measure_id": "NEW_MEASURE", "ses_sensitivity": "UNKNOWN"},
        ]
        assert not requires_ses_disclosure(measures)

    def test_mixed_group_triggers_on_any_high(self) -> None:
        """If even one measure in the group is HIGH, disclosure fires."""
        measures = [
            {"measure_id": "HAI_1_SIR", "ses_sensitivity": "LOW"},
            {"measure_id": "READM_30_AMI", "ses_sensitivity": "HIGH"},
            {"measure_id": "HAI_2_SIR", "ses_sensitivity": "LOW"},
        ]
        assert requires_ses_disclosure(measures)

    def test_empty_measures_does_not_trigger(self) -> None:
        assert not requires_ses_disclosure([])


class TestSmallSampleCaveat:
    """3e: Small sample caveat fires below threshold or when null."""

    def test_below_threshold_triggers(self) -> None:
        assert requires_small_sample_caveat({"sample_size": 15})

    def test_at_threshold_does_not_trigger(self) -> None:
        assert not requires_small_sample_caveat({"sample_size": 30})

    def test_above_threshold_does_not_trigger(self) -> None:
        assert not requires_small_sample_caveat({"sample_size": 500})

    def test_null_sample_size_triggers(self) -> None:
        """Unknown denominator is not reassuring — caveat fires."""
        assert requires_small_sample_caveat({"sample_size": None})

    def test_missing_sample_size_triggers(self) -> None:
        """Field absent entirely — same as null."""
        assert requires_small_sample_caveat({})

    def test_boundary_one_below(self) -> None:
        assert requires_small_sample_caveat({"sample_size": 29})

    def test_zero_triggers(self) -> None:
        assert requires_small_sample_caveat({"sample_size": 0})


class TestMultipleComparisonDisclosure:
    """3d: Multiple comparison disclosure fires on full profile pages."""

    def test_single_measure_does_not_trigger(self) -> None:
        assert not requires_multiple_comparison_disclosure(1)

    def test_multiple_measures_triggers(self) -> None:
        assert requires_multiple_comparison_disclosure(5)

    def test_zero_measures_does_not_trigger(self) -> None:
        assert not requires_multiple_comparison_disclosure(0)


class TestCIMethodologyNote:
    """3h: CI methodology note fires for calculated (non-CMS) intervals."""

    def test_calculated_interval_triggers(self) -> None:
        measure = {
            "confidence_interval_lower": 10.1,
            "confidence_interval_upper": 16.8,
            "ci_source": "calculated",
        }
        assert requires_ci_methodology_note(measure)

    def test_cms_published_does_not_trigger(self) -> None:
        measure = {
            "confidence_interval_lower": 10.1,
            "confidence_interval_upper": 16.8,
            "ci_source": "cms_published",
        }
        assert not requires_ci_methodology_note(measure)

    def test_no_interval_does_not_trigger(self) -> None:
        measure = {
            "confidence_interval_lower": None,
            "confidence_interval_upper": None,
            "ci_source": "calculated",
        }
        assert not requires_ci_methodology_note(measure)

    def test_partial_interval_does_not_trigger(self) -> None:
        """Only lower bound — not a complete interval."""
        measure = {
            "confidence_interval_lower": 10.1,
            "confidence_interval_upper": None,
            "ci_source": "calculated",
        }
        assert not requires_ci_methodology_note(measure)


class TestPopulationComparabilityWarning:
    """3f: Population context warning on compare page."""

    def test_large_difference_triggers(self) -> None:
        a = {"dual_eligible_proportion": Decimal("35.0")}
        b = {"dual_eligible_proportion": Decimal("8.0")}
        assert requires_population_comparability_warning(a, b)

    def test_small_difference_does_not_trigger(self) -> None:
        a = {"dual_eligible_proportion": Decimal("20.0")}
        b = {"dual_eligible_proportion": Decimal("18.0")}
        assert not requires_population_comparability_warning(a, b)

    def test_null_a_triggers(self) -> None:
        """Unknown population = cannot confirm comparability."""
        a = {"dual_eligible_proportion": None}
        b = {"dual_eligible_proportion": Decimal("15.0")}
        assert requires_population_comparability_warning(a, b)

    def test_null_b_triggers(self) -> None:
        a = {"dual_eligible_proportion": Decimal("15.0")}
        b = {"dual_eligible_proportion": None}
        assert requires_population_comparability_warning(a, b)

    def test_both_null_triggers(self) -> None:
        a = {"dual_eligible_proportion": None}
        b = {"dual_eligible_proportion": None}
        assert requires_population_comparability_warning(a, b)

    def test_exactly_at_threshold_does_not_trigger(self) -> None:
        """At exactly 10pp difference, does not trigger (> not >=)."""
        a = {"dual_eligible_proportion": Decimal("20.0")}
        b = {"dual_eligible_proportion": Decimal("10.0")}
        assert not requires_population_comparability_warning(a, b)

    def test_just_over_threshold_triggers(self) -> None:
        a = {"dual_eligible_proportion": Decimal("20.1")}
        b = {"dual_eligible_proportion": Decimal("10.0")}
        assert requires_population_comparability_warning(a, b)


class TestOwnershipQualityDisclaimer:
    """3g: Ownership-quality disclaimer fires when both visible."""

    def test_both_present_triggers(self) -> None:
        assert requires_ownership_quality_disclaimer(True, True)

    def test_ownership_only_does_not_trigger(self) -> None:
        assert not requires_ownership_quality_disclaimer(True, False)

    def test_quality_only_does_not_trigger(self) -> None:
        assert not requires_ownership_quality_disclaimer(False, True)

    def test_neither_present_does_not_trigger(self) -> None:
        assert not requires_ownership_quality_disclaimer(False, False)


class TestDataAttribution:
    """3b: Data attribution fires whenever measures are displayed."""

    def test_measures_present_triggers(self) -> None:
        assert requires_data_attribution([{"measure_id": "X"}])

    def test_empty_does_not_trigger(self) -> None:
        assert not requires_data_attribution([])


class TestDisclosureChecklist:
    """Integration: given a full provider profile, verify all applicable
    disclosures are identified.

    This simulates what the frontend profile page must do: given a provider's
    data, determine which disclosures are required.
    """

    def _build_sample_hospital(self) -> dict[str, Any]:
        """A hospital with a mix of disclosure-triggering conditions."""
        return {
            "provider_id": "010001",
            "provider_type": "HOSPITAL",
            "measures": [
                {
                    "measure_id": "MORT_30_AMI",
                    "ses_sensitivity": "HIGH",
                    "sample_size": 25,
                    "confidence_interval_lower": 10.1,
                    "confidence_interval_upper": 16.8,
                    "ci_source": "cms_published",
                },
                {
                    "measure_id": "HAI_1_SIR",
                    "ses_sensitivity": "LOW",
                    "sample_size": 150,
                    "confidence_interval_lower": 0.8,
                    "confidence_interval_upper": 1.4,
                    "ci_source": "cms_published",
                },
                {
                    "measure_id": "OP_18a",
                    "ses_sensitivity": "LOW",
                    "sample_size": 200,
                    "confidence_interval_lower": 180,
                    "confidence_interval_upper": 220,
                    "ci_source": "calculated",
                },
            ],
            "hospital_context": {
                "dual_eligible_proportion": None,
            },
        }

    def test_full_profile_disclosures(self) -> None:
        """A hospital profile page must trigger: 3b, 3c, 3d, 3e, 3h."""
        hospital = self._build_sample_hospital()
        measures = hospital["measures"]

        # 3b: Data attribution (always when measures present)
        assert requires_data_attribution(measures)

        # 3c: SES disclosure (MORT_30_AMI is HIGH)
        assert requires_ses_disclosure(measures)

        # 3d: Multiple comparison (3 measures shown)
        assert requires_multiple_comparison_disclosure(len(measures))

        # 3e: Small sample caveat (MORT_30_AMI has sample_size=25)
        small_sample_measures = [
            m for m in measures if requires_small_sample_caveat(m)
        ]
        assert len(small_sample_measures) == 1
        assert small_sample_measures[0]["measure_id"] == "MORT_30_AMI"

        # 3h: CI methodology note (OP_18a is calculated)
        ci_note_measures = [
            m for m in measures if requires_ci_methodology_note(m)
        ]
        assert len(ci_note_measures) == 1
        assert ci_note_measures[0]["measure_id"] == "OP_18a"

    def test_compare_page_disclosures(self) -> None:
        """Compare page with null dual_eligible must trigger 3f."""
        hospital_a = self._build_sample_hospital()
        hospital_b = {
            "hospital_context": {"dual_eligible_proportion": Decimal("12.0")},
        }

        # 3f: Population comparability (hospital_a has null dep)
        assert requires_population_comparability_warning(
            hospital_a["hospital_context"],
            hospital_b["hospital_context"],
        )

    def test_all_low_ses_no_ses_disclosure(self) -> None:
        """A profile with only LOW ses_sensitivity should not trigger 3c."""
        measures = [
            {"measure_id": "HAI_1_SIR", "ses_sensitivity": "LOW"},
            {"measure_id": "HAI_2_SIR", "ses_sensitivity": "LOW"},
        ]
        assert not requires_ses_disclosure(measures)
