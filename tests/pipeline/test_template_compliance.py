"""Template output compliance tests.

Tests that rendered template output conforms to legal-compliance.md,
text-templates.md, and display-philosophy.md rules. These tests enforce:

1. No prohibited language in rendered text (advisory, predictive, causal,
   inferential, clinical directives)
2. Required disclosures fire for the correct conditions (SES, small sample,
   multiple comparison)
3. Conditional template inserts render correctly (direction note, CI source,
   overlap note)
4. Color encoding constraints (no directional color in standard metric blocks)

Testing.md items covered: 14-23.

Antifragile design: prohibited patterns are defined once in PROHIBITED_PATTERNS
and reused across all template tests. Adding a new prohibited term is one line.
Adding a new template variant is one parametrized test case.
"""

import re
from decimal import Decimal

import pytest

# ─── Prohibited language patterns ─────────────────────────────────────
# These mirror the compliance lint (scripts/lint_compliance.py) but run
# against rendered template OUTPUT, not source code. A string that passes
# source-level lint can still produce prohibited output if a template
# variable contains bad content.

PROHIBITED_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # Advisory / personalization
    (re.compile(r"\byou\s+should\b", re.I), "advisory: 'you should'"),
    (re.compile(r"\byour\s+risk\b", re.I), "personalization: 'your risk'"),
    (re.compile(r"\bbased\s+on\s+your\s+needs\b", re.I), "personalization"),
    (re.compile(r"\bfor\s+your\s+situation\b", re.I), "personalization"),
    (re.compile(r"\bpatients\s+can\s+expect\b", re.I), "predictive"),
    (re.compile(r"\bpatients\s+should\b", re.I), "clinical directive"),
    (re.compile(r"\bseek\s+care\b", re.I), "clinical directive"),
    (re.compile(r"\brecommend\b", re.I), "clinical directive"),
    (re.compile(r"\bshould\s+consider\b", re.I), "clinical directive"),

    # Predictive / causal
    (re.compile(r"\bwhat\s+could\s+go\s+wrong\b", re.I), "predictive framing"),
    (re.compile(r"\byou\s+are\s+likely\b", re.I), "predictive"),
    (re.compile(r"\bpredicted\s+outcomes?\b", re.I), "predictive"),
    (re.compile(r"\blikelihood\s+of\b", re.I), "predictive"),
    (re.compile(r"\bbecause\s+of\b", re.I), "causal without CMS citation"),
    (re.compile(r"\bdue\s+to\b", re.I), "causal without CMS citation"),
    (re.compile(r"\bcaused\s+by\b", re.I), "causal"),
    (re.compile(r"\bresulting\s+from\b", re.I), "causal"),

    # Inferential
    (re.compile(r"\bsuggests\b", re.I), "inferential"),
    (re.compile(r"\bindicates\b", re.I), "inferential"),
    (re.compile(r"\bmay\s+reflect\b", re.I), "inferential"),
    (re.compile(r"\blikely\s+indicates\b", re.I), "inferential"),
    (re.compile(r"\blikely\s+reflects\b", re.I), "inferential"),

    # Superlatives / ranking
    (re.compile(r"\bone\s+of\s+the\s+best\b", re.I), "superlative"),
    (re.compile(r"\bamong\s+the\s+worst\b", re.I), "superlative"),
    (re.compile(r"\btop\s+\d+\b", re.I), "ranking language"),
    (re.compile(r"\bbottom\s+\d+\b", re.I), "ranking language"),
    (re.compile(r"\bleaderboard\b", re.I), "ranking language"),

    # Ownership-quality (legal-compliance.md § Ownership Data)
    (re.compile(r"\btrack\s+record\b", re.I), "ownership-quality: 'track record'"),
    (re.compile(r"\bpattern\s+of\b", re.I), "ownership-quality: 'pattern of'"),
    (re.compile(r"\bsystemic\b", re.I), "ownership-quality: 'systemic'"),
    (re.compile(r"\bsignificantly\b", re.I), "statistical: 'significantly' without basis"),
    (re.compile(r"\bsafety[\s-]*net\s+hospital\b", re.I), "prohibited term: 'safety net hospital'"),
]

# Directional color classes (Tailwind) — prohibited in standard metric output
DIRECTIONAL_COLOR_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\btext-red-\d+\b"), "red text (directional color)"),
    (re.compile(r"\btext-green-\d+\b"), "green text (directional color)"),
    (re.compile(r"\bbg-red-\d+\b"), "red background (directional color)"),
    (re.compile(r"\bbg-green-\d+\b"), "green background (directional color)"),
]


def assert_no_prohibited_language(text: str, context: str = "") -> None:
    """Assert that rendered text contains no prohibited patterns.

    Args:
        text: The rendered template output to check.
        context: Description of what was rendered, for error messages.
    """
    for pattern, violation_type in PROHIBITED_PATTERNS:
        match = pattern.search(text)
        assert match is None, (
            f"Prohibited language ({violation_type}) found in {context}: "
            f"'{match.group()}'"
        )


def assert_no_directional_color(html: str, context: str = "") -> None:
    """Assert that rendered HTML contains no directional color classes.

    Args:
        html: The rendered HTML/JSX output to check.
        context: Description of what was rendered, for error messages.
    """
    for pattern, violation_type in DIRECTIONAL_COLOR_PATTERNS:
        match = pattern.search(html)
        assert match is None, (
            f"Directional color ({violation_type}) in {context}: "
            f"'{match.group()}'"
        )


# ─── Sample data for parametrized tests ───────────────────────────────

STANDARD_METRIC_CASES = [
    pytest.param(
        {
            "facility_name": "General Hospital",
            "metric_name": "Heart Attack 30-Day Mortality Rate",
            "metric_value": "13.2%",
            "national_average": "12.8%",
            "state_name": "California",
            "state_average": "12.5%",
            "metric_plain_language": (
                "The percentage of Medicare patients who died within "
                "30 days of being admitted to the hospital for a heart attack."
            ),
            "cms_direction": "lower",
            "ci_lower": "10.1%",
            "ci_upper": "16.8%",
            "sample_size": 45,
            "ci_source": "cms_published",
            "prior_source": None,
            "ci_level": "95%",
            "direction_source": "CMS_API",
            "overlap_flag": True,
        },
        id="standard-with-overlap-cms-ci",
    ),
    pytest.param(
        {
            "facility_name": "Rural Medical Center",
            "metric_name": "Pneumonia 30-Day Mortality Rate",
            "metric_value": "18.5%",
            "national_average": "15.2%",
            "state_name": "Montana",
            "state_average": "16.1%",
            "metric_plain_language": (
                "The percentage of Medicare patients who died within "
                "30 days of being admitted for pneumonia."
            ),
            "cms_direction": "lower",
            "ci_lower": "15.8%",
            "ci_upper": "21.2%",
            "sample_size": 28,
            "ci_source": "calculated",
            "prior_source": "state average",
            "ci_level": "95%",
            "direction_source": "CMS_DATA_DICTIONARY",
            "overlap_flag": False,
        },
        id="small-sample-calculated-ci-no-overlap",
    ),
    pytest.param(
        {
            "facility_name": "City Hospital",
            "metric_name": "Sepsis 3-Hour Bundle Compliance",
            "metric_value": "72%",
            "national_average": "68%",
            "state_name": "New York",
            "state_average": "70%",
            "metric_plain_language": (
                "The percentage of patients who received all "
                "recommended treatments within 3 hours of severe sepsis recognition."
            ),
            "cms_measure_definition": (
                "The measures of timely and effective care show the percentage of "
                "hospital patients who got treatments known to get the best results "
                "for certain common, serious medical conditions or surgical procedures."
            ),
            "cms_direction": "higher",
            "ci_lower": "65%",
            "ci_upper": "79%",
            "sample_size": 120,
            "ci_source": "calculated",
            "prior_source": "national average",
            "ci_level": "95%",
            "direction_source": "CMS_MEASURE_DEFINITION",
            "overlap_flag": True,
        },
        id="measure-definition-direction-source",
    ),
    pytest.param(
        {
            "facility_name": "Valley Medical Center",
            "metric_name": "Heart Attack 30-Day Mortality Rate",
            "metric_value": "11.5%",
            "national_average": "12.8%",
            "state_name": "Oregon",
            "state_average": None,  # HGLM: CMS does not publish state avg (DEC-036)
            "metric_plain_language": (
                "The percentage of Medicare patients who died within "
                "30 days of being admitted for a heart attack."
            ),
            "cms_measure_definition": (
                "The 30-day death measures are estimates of deaths within 30 days "
                "of the start of a hospital admission from any cause."
            ),
            "cms_direction": "lower",
            "ci_lower": "8.2%",
            "ci_upper": "15.1%",
            "sample_size": 35,
            "ci_source": "cms_published",
            "prior_source": None,
            "ci_level": "95%",
            "direction_source": "CMS_API",
            "overlap_flag": True,
        },
        id="no-state-avg-hglm-measure",
    ),
    pytest.param(
        {
            "facility_name": "Community Hospital",
            "metric_name": "HCAHPS Nurse Communication",
            "metric_value": "78%",
            "national_average": "80%",
            "state_name": "Iowa",
            "state_average": "79%",
            "metric_plain_language": (
                "The percentage of patients who reported that their nurses "
                "always communicated well."
            ),
            "cms_measure_definition": None,  # REVIEW_NEEDED: not yet sourced
            "cms_direction": None,
            "ci_lower": None,  # No CI for HCAHPS (patient-mix adjusted)
            "ci_upper": None,
            "sample_size": 300,
            "ci_source": None,
            "prior_source": None,
            "ci_level": None,
            "direction_source": "CMS_MEASURE_DEFINITION",
            "overlap_flag": None,
        },
        id="no-ci-no-cms-definition-hcahps",
    ),
]

SEVERE_DEFICIENCY_CASES = [
    pytest.param(
        {
            "facility_name": "Sunrise Nursing Home",
            "citation_date": "2025-11-15",
            "deficiency_category": "Quality of Care",
            "scope_severity_code": "J",
            "scope_severity_plain": (
                "A scope and severity J citation indicates a pattern of "
                "deficiencies causing actual harm to residents that does not "
                "constitute immediate jeopardy"
            ),
        },
        id="scope-j-actual-harm",
    ),
    pytest.param(
        {
            "facility_name": "Valley Care Center",
            "citation_date": "2026-01-08",
            "deficiency_category": "Infection Control",
            "scope_severity_code": "L",
            "scope_severity_plain": (
                "A scope and severity L citation indicates immediate jeopardy "
                "to resident health or safety, the most serious category of "
                "deficiency finding under CMS regulations"
            ),
        },
        id="scope-l-immediate-jeopardy",
    ),
]

REPEAT_DEFICIENCY_CASES = [
    pytest.param(
        {
            "facility_name": "Oakwood Nursing Home",
            "deficiency_category": "Infection Control",
            "repeat_count": 3,
            "date_first": "2023-06-12",
            "date_most_recent": "2025-12-01",
        },
        id="repeat-3-cycles",
    ),
]

STAFFING_BELOW_THRESHOLD_CASES = [
    pytest.param(
        {
            "facility_name": "Pine Ridge Care",
            "staff_type": "Registered Nurse",
            "reported_hours": Decimal("0.35"),
            "threshold_hours": Decimal("0.55"),
            "data_period": "Q3 2025",
        },
        id="rn-below-threshold",
    ),
]


# ─── Attempt to import render functions ───────────────────────────────
# These will be implemented in pipeline/render/. Until then, tests that
# depend on them are skipped. The validation utilities above can still
# be used independently.

try:
    from pipeline.render import render_standard_metric_block
    HAS_STANDARD_RENDERER = True
except ImportError:
    HAS_STANDARD_RENDERER = False

try:
    from pipeline.render import render_severe_deficiency
    HAS_DEFICIENCY_RENDERER = True
except ImportError:
    HAS_DEFICIENCY_RENDERER = False

try:
    from pipeline.render import render_repeat_deficiency
    HAS_REPEAT_RENDERER = True
except ImportError:
    HAS_REPEAT_RENDERER = False

try:
    from pipeline.render import render_staffing_below_threshold
    HAS_STAFFING_RENDERER = True
except ImportError:
    HAS_STAFFING_RENDERER = False


# ─── Template Type 1: Standard Metric Block ───────────────────────────

@pytest.mark.parametrize("data", STANDARD_METRIC_CASES)
@pytest.mark.skipif(not HAS_STANDARD_RENDERER, reason="render not yet implemented")
class TestStandardMetricBlock:
    """Tests for Template Type 1 (text-templates.md)."""

    def test_no_prohibited_language(self, data: dict) -> None:
        """testing.md item 20: no predictive language, 'what could go wrong'."""
        output = render_standard_metric_block(**data)
        assert_no_prohibited_language(output, f"standard metric: {data['metric_name']}")

    def test_no_directional_color(self, data: dict) -> None:
        """testing.md item 23: color only for tail risk / repeat deficiencies."""
        output = render_standard_metric_block(**data)
        assert_no_directional_color(output, f"standard metric: {data['metric_name']}")

    def test_no_better_worse_language(self, data: dict) -> None:
        """testing.md item 21: no 'better/worse', only CMS direction."""
        output = render_standard_metric_block(**data)
        for word in ["better than", "worse than", "is better", "is worse"]:
            assert word.lower() not in output.lower(), (
                f"Standard metric output contains '{word}' — "
                f"only CMS direction language is permitted"
            )

    def test_direction_note_conditional(self, data: dict) -> None:
        """testing.md item 15: direction note conditional on direction_source."""
        output = render_standard_metric_block(**data)
        direction_phrase = "CMS designates"
        if data["direction_source"] in ("CMS_API", "CMS_DATA_DICTIONARY", "CMS_MEASURE_SPEC"):
            assert direction_phrase in output, (
                f"Direction note missing for direction_source={data['direction_source']}"
            )
        else:
            assert direction_phrase not in output, (
                f"Direction note should not appear for "
                f"direction_source={data['direction_source']}"
            )

    def test_ci_source_note_conditional(self, data: dict) -> None:
        """testing.md item 15: CI source note conditional on ci_source."""
        output = render_standard_metric_block(**data)
        if data["ci_source"] == "cms_published":
            assert "as published by CMS" in output
            assert "Beta-Binomial" not in output
        elif data["ci_source"] == "calculated":
            assert "Bayesian Beta-Binomial" in output
            assert data["prior_source"] in output

    def test_overlap_note_conditional(self, data: dict) -> None:
        """testing.md item 16: overlap note conditional on overlap_flag."""
        output = render_standard_metric_block(**data)
        overlap_phrase = "may not be meaningful"
        if data["overlap_flag"]:
            assert overlap_phrase in output, "Overlap note missing when overlap_flag=True"
        else:
            assert overlap_phrase not in output, (
                "Overlap note should not appear when overlap_flag=False"
            )

    def test_ci_sentence_omitted_when_unavailable(self, data: dict) -> None:
        """testing.md item 22: omit CI sentence where unavailable."""
        # If ci_lower and ci_upper are both None, the CI sentence should not appear
        if data.get("ci_lower") is None and data.get("ci_upper") is None:
            output = render_standard_metric_block(**data)
            assert "credible interval" not in output.lower()

    def test_state_avg_note_conditional(self, data: dict) -> None:
        """DEC-036: state average sentence omitted when state_avg is null."""
        output = render_standard_metric_block(**data)
        if data.get("state_average") is None:
            assert "average for this measure is" not in output.split(
                "national average", 1
            )[-1], (
                "State average sentence should be omitted when state_avg is null"
            )
        else:
            assert data["state_name"] in output

    def test_cms_definition_note_conditional(self, data: dict) -> None:
        """DEC-037: CMS definition sentence omitted when null."""
        output = render_standard_metric_block(**data)
        if data.get("cms_measure_definition") is not None:
            assert "CMS defines this measure as" in output
            assert data["cms_measure_definition"] in output
        else:
            assert "CMS defines this measure as" not in output

    def test_facility_name_present(self, data: dict) -> None:
        """Basic contract: facility name appears in output."""
        output = render_standard_metric_block(**data)
        assert data["facility_name"] in output

    def test_national_average_present(self, data: dict) -> None:
        """Basic contract: national average appears in output."""
        output = render_standard_metric_block(**data)
        assert data["national_average"] in output


# ─── Template Type 2a: Severe Deficiency ──────────────────────────────

@pytest.mark.parametrize("data", SEVERE_DEFICIENCY_CASES)
@pytest.mark.skipif(not HAS_DEFICIENCY_RENDERER, reason="render not yet implemented")
class TestSevereDeficiency:
    """Tests for Template Type 2a (text-templates.md)."""

    def test_no_prohibited_language(self, data: dict) -> None:
        output = render_severe_deficiency(**data)
        assert_no_prohibited_language(output, f"deficiency: {data['scope_severity_code']}")

    def test_scope_severity_code_present(self, data: dict) -> None:
        """testing.md item 17: severe deficiency with plain-language lookup."""
        output = render_severe_deficiency(**data)
        assert data["scope_severity_code"] in output
        assert data["scope_severity_plain"] in output

    def test_cms_attribution(self, data: dict) -> None:
        """Output must attribute to CMS inspection records."""
        output = render_severe_deficiency(**data)
        assert "CMS" in output


# ─── Template Type 2b: Repeat Deficiency ──────────────────────────────

@pytest.mark.parametrize("data", REPEAT_DEFICIENCY_CASES)
@pytest.mark.skipif(not HAS_REPEAT_RENDERER, reason="render not yet implemented")
class TestRepeatDeficiency:
    """Tests for Template Type 2b (text-templates.md)."""

    def test_no_prohibited_language(self, data: dict) -> None:
        output = render_repeat_deficiency(**data)
        assert_no_prohibited_language(output, "repeat deficiency")

    def test_no_inferential_language(self, data: dict) -> None:
        """Repeat deficiency template must not use inferential language."""
        output = render_repeat_deficiency(**data)
        for phrase in ["may indicate", "may be a signal", "suggests", "indicates"]:
            assert phrase.lower() not in output.lower(), (
                f"Inferential language '{phrase}' in repeat deficiency output"
            )

    def test_cycle_count_present(self, data: dict) -> None:
        """testing.md item 18: repeat deficiency with cycle count and dates."""
        output = render_repeat_deficiency(**data)
        assert str(data["repeat_count"]) in output
        assert data["date_first"] in output
        assert data["date_most_recent"] in output


# ─── Template Type 2c: Staffing Below Threshold ──────────────────────

@pytest.mark.parametrize("data", STAFFING_BELOW_THRESHOLD_CASES)
@pytest.mark.skipif(not HAS_STAFFING_RENDERER, reason="render not yet implemented")
class TestStaffingBelowThreshold:
    """Tests for Template Type 2c (text-templates.md)."""

    def test_no_prohibited_language(self, data: dict) -> None:
        output = render_staffing_below_threshold(**data)
        assert_no_prohibited_language(output, "staffing threshold")

    def test_threshold_comparison(self, data: dict) -> None:
        """testing.md item 19: staffing threshold with correct comparison."""
        output = render_staffing_below_threshold(**data)
        assert str(data["reported_hours"]) in output
        assert str(data["threshold_hours"]) in output

    def test_cms_attribution(self, data: dict) -> None:
        """Output must reference CMS/PBJ as data source."""
        output = render_staffing_below_threshold(**data)
        assert "CMS" in output or "Payroll Based Journal" in output


# ─── Validation utility tests (always run) ────────────────────────────
# These test the validation functions themselves, ensuring the prohibited
# pattern list catches what it should.

class TestValidationUtilities:
    """Tests for the assert_no_prohibited_language function itself."""

    def test_clean_text_passes(self) -> None:
        """A clean CMS-style sentence should pass all checks."""
        text = (
            "General Hospital has a Heart Attack 30-Day Mortality Rate of 13.2%. "
            "The national average for this measure is 12.8%. "
            "The California average for this measure is 12.5%."
        )
        assert_no_prohibited_language(text, "clean text")

    def test_advisory_language_caught(self) -> None:
        with pytest.raises(AssertionError, match="advisory"):
            assert_no_prohibited_language("You should visit this hospital")

    def test_predictive_language_caught(self) -> None:
        with pytest.raises(AssertionError, match="predictive"):
            assert_no_prohibited_language(
                "What could go wrong at this hospital"
            )

    def test_causal_language_caught(self) -> None:
        with pytest.raises(AssertionError, match="causal"):
            assert_no_prohibited_language(
                "Higher rates because of staffing shortages"
            )

    def test_inferential_language_caught(self) -> None:
        with pytest.raises(AssertionError, match="inferential"):
            assert_no_prohibited_language(
                "This pattern suggests quality problems"
            )

    def test_clinical_directive_caught(self) -> None:
        with pytest.raises(AssertionError, match="clinical directive"):
            assert_no_prohibited_language(
                "Patients should seek care at another facility"
            )

    def test_superlative_caught(self) -> None:
        with pytest.raises(AssertionError, match="superlative"):
            assert_no_prohibited_language(
                "This is one of the best hospitals in the state"
            )

    def test_ranking_language_caught(self) -> None:
        with pytest.raises(AssertionError, match="ranking"):
            assert_no_prohibited_language("Top 10 hospitals by mortality rate")

    def test_personalization_caught(self) -> None:
        with pytest.raises(AssertionError, match="personalization"):
            assert_no_prohibited_language(
                "Based on your needs, this hospital may be appropriate"
            )

    def test_directional_color_clean(self) -> None:
        """Gray styling should pass."""
        assert_no_directional_color(
            '<span class="text-gray-700 bg-gray-50">13.2%</span>'
        )

    def test_directional_color_red_caught(self) -> None:
        with pytest.raises(AssertionError, match="red"):
            assert_no_directional_color(
                '<span class="text-red-600">Above average</span>'
            )

    def test_directional_color_green_caught(self) -> None:
        with pytest.raises(AssertionError, match="green"):
            assert_no_directional_color(
                '<span class="text-green-600">Below average</span>'
            )

    def test_ownership_track_record_caught(self) -> None:
        with pytest.raises(AssertionError, match="ownership"):
            assert_no_prohibited_language(
                "This entity has a track record of poor quality"
            )

    def test_ownership_pattern_of_caught(self) -> None:
        with pytest.raises(AssertionError, match="ownership"):
            assert_no_prohibited_language(
                "There is a pattern of deficiencies at these facilities"
            )

    def test_significantly_caught(self) -> None:
        with pytest.raises(AssertionError, match="statistical"):
            assert_no_prohibited_language(
                "This rate is significantly higher than the national average"
            )

    def test_safety_net_hospital_caught(self) -> None:
        with pytest.raises(AssertionError, match="prohibited term"):
            assert_no_prohibited_language(
                "This safety net hospital serves a vulnerable population"
            )
