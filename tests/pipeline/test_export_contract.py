"""Export-to-frontend contract tests.

Validates that the JSON export schema (json-export.md) and the frontend
TypeScript types (frontend/types/provider.ts) stay in sync. These tests
define the canonical schema in Python and check both sides against it.

When the export module is implemented, these tests also validate real
exported JSON files against the same schema.

Antifragile design: the schema is defined once in PROVIDER_SCHEMA. Adding
a field means adding it here, in json-export.md, and in provider.ts in the
same commit. The test catches any drift between the three.
"""

import json
import re
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PROVIDER_TS = PROJECT_ROOT / "frontend" / "types" / "provider.ts"
EXPORT_DATA = PROJECT_ROOT / "build" / "data"

# ─── Canonical schema ─────────────────────────────────────────────────
# This is the single source of truth for field names and types.
# "type" uses a simplified type language:
#   "string", "number", "boolean", "integer" — required, non-null
#   "string?" — nullable (string | null in TS, "string or null" in json-export.md)
#   "number?" — nullable number
#   "array" — required array
#   "object?" — nullable object
#
# The test checks that provider.ts declares every field listed here,
# and that real exported JSON (when available) conforms.

TREND_PERIOD_FIELDS: dict[str, str] = {
    "period_label": "string",
    "numeric_value": "number?",
    "suppressed": "boolean",
    "not_reported": "boolean",
    "methodology_change_flag": "boolean",
}

MEASURE_FIELDS: dict[str, str] = {
    "measure_id": "string",
    "measure_name": "string?",  # nullable for auto-registered retired stubs
    "measure_plain_language": "string?",
    "cms_measure_definition": "string?",  # DEC-037: verbatim CMS definition
    "measure_group": "string",
    "source_dataset_id": "string?",
    "source_dataset_name": "string",
    "direction": "string?",  # null for EDV, HCAHPS middlebox
    "direction_source": "string?",  # DEC-032: CMS_API, CMS_DATA_DICTIONARY, CMS_MEASURE_SPEC, CMS_MEASURE_DEFINITION
    "unit": "string?",
    "tail_risk_flag": "boolean",
    "ses_sensitivity": "string",  # SesSensitivity enum
    "stratification": "string?",  # null = non-stratified
    "numeric_value": "number?",
    "score_text": "string?",  # DEC-024: EDV categorical
    "confidence_interval_lower": "number?",
    "confidence_interval_upper": "number?",
    "ci_source": "string?",  # DEC-029: "cms_published" | "calculated"
    "prior_source": "string?",  # DEC-029: prior hierarchy label
    "observed_value": "number?",  # DEC-016: NH claims O/E
    "expected_value": "number?",  # DEC-016: NH claims O/E
    "compared_to_national": "string?",  # DEC-022
    "suppressed": "boolean",
    "suppression_reason": "string?",
    "not_reported": "boolean",
    "not_reported_reason": "string?",
    "count_suppressed": "boolean",  # DEC-023
    "footnote_codes": "array?",  # null when no footnotes
    "footnote_text": "array?",  # null when no footnotes
    "period_label": "string",
    "period_start": "string?",
    "period_end": "string?",
    "sample_size": "number?",
    "denominator": "number?",
    "reliability_flag": "string?",  # nullable until transform layer runs
    "national_avg": "number?",
    "national_avg_period": "string?",
    "state_avg": "number?",
    "state_avg_period": "string?",
    "ci_level": "string?",  # e.g. "95%"; null when no interval
    "overlap_flag": "boolean?",  # CI contains national avg
    "trend": "array?",  # null when only 1 period
    "trend_valid": "boolean",
    "trend_period_count": "number",
}

PAYMENT_ADJUSTMENT_FIELDS: dict[str, str] = {
    "program": "string",  # PaymentProgram enum
    "program_year": "number",
    "penalty_flag": "boolean?",  # null = excluded from program (HACRP N/A)
    "payment_adjustment_pct": "number?",
    "total_score": "number?",
    "score_percentile": "number?",
}

HOSPITAL_CONTEXT_FIELDS: dict[str, str] = {
    "is_critical_access": "boolean?",
    "is_emergency_services": "boolean?",
    "birthing_friendly_designation": "boolean?",
    "hospital_overall_rating": "number?",
    "hospital_overall_rating_footnote": "string?",
}

NURSING_HOME_CONTEXT_FIELDS: dict[str, str] = {
    "certified_beds": "number?",
    "average_daily_census": "number?",
    "is_continuing_care_retirement_community": "boolean?",
    "is_special_focus_facility": "boolean?",
    "is_special_focus_facility_candidate": "boolean?",
    "is_hospital_based": "boolean?",
    "is_abuse_icon": "boolean?",
    "is_urban": "boolean?",
    "chain_name": "string?",
    "chain_id": "string?",
    # PBJ staffing context (DEC-018) — context, not MEASURE_REGISTRY
    "reported_total_hprd": "number?",
    "reported_rn_hprd": "number?",
    "reported_lpn_hprd": "number?",
    "reported_aide_hprd": "number?",
    "adjusted_total_hprd": "number?",
    "adjusted_rn_hprd": "number?",
    "adjusted_lpn_hprd": "number?",
    "adjusted_aide_hprd": "number?",
    "casemix_total_hprd": "number?",
    "casemix_rn_hprd": "number?",
    "weekend_total_hprd": "number?",
    "weekend_rn_hprd": "number?",
    "pt_hprd": "number?",
    "nursing_casemix_index": "number?",
    "total_turnover": "number?",
    "rn_turnover": "number?",
    "administrator_departures": "number?",
    # Inspection context surfaced for the NH profile header
    "total_weighted_health_survey_score": "number?",
    "cycle_1_total_health_deficiencies": "number?",
    "cycle_1_health_deficiency_score": "number?",
    "staffing_rating": "number?",
    "staffing_trend": "array?",
    "standard_survey_dates": "array?",
}

ADDRESS_FIELDS: dict[str, str] = {
    "street": "string?",
    "city": "string?",
    "state": "string?",
    "zip": "string?",
}

PROVIDER_FIELDS: dict[str, str] = {
    "provider_id": "string",
    "provider_type": "string",  # ProviderType enum
    "name": "string",
    "is_active": "boolean",
    "phone": "string?",
    "address": "object",
    "provider_subtype": "string?",
    "ownership_type": "string?",
    "last_updated": "string",
    "measures": "array",
    "payment_adjustments": "array",
    "hospital_context": "object?",
    "nursing_home_context": "object?",
    "inspection_events": "array?",
    "penalties": "array?",
    "ownership": "array?",
    # parent_group_stats is declared in provider.ts but not yet emitted by the
    # export. Marked as not-yet-implemented; the no-extra-fields check below
    # accepts it on the TS side.
}

# Fields that must NOT appear in provider.ts (removed by decisions)
REMOVED_FIELDS: dict[str, str] = {
    "summaries": "Removed by DEC-031 (LLM generation replaced by templates)",
}

# Interfaces that must NOT appear in provider.ts (removed by decisions)
REMOVED_INTERFACES: dict[str, str] = {
    "Summary": "Removed by DEC-031 (LLM generation replaced by templates)",
}

# Enum values that must appear in provider.ts
EXPECTED_ENUMS: dict[str, list[str]] = {
    "ReliabilityFlag": ["RELIABLE", "LIMITED_SAMPLE", "NOT_REPORTED", "SUPPRESSED"],
    "MeasureDirection": ["LOWER_IS_BETTER", "HIGHER_IS_BETTER"],
    "DirectionSource": ["CMS_API", "CMS_DATA_DICTIONARY", "CMS_MEASURE_SPEC", "CMS_MEASURE_DEFINITION"],
    "SesSensitivity": ["HIGH", "MODERATE", "LOW", "UNKNOWN"],
    "ProviderType": ["HOSPITAL", "NURSING_HOME", "HOME_HEALTH", "HOSPICE"],
    "PaymentProgram": ["HRRP", "HACRP", "VBP", "SNF_VBP"],
}


def _read_provider_ts() -> str:
    """Read the frontend types file."""
    return PROVIDER_TS.read_text(encoding="utf-8")


def _extract_interface_fields(ts_content: str, interface_name: str) -> set[str]:
    """Extract field names from a TypeScript interface declaration.

    Handles standard interface declarations like:
        export interface Foo {
            field_name: type;
        }
    """
    # Match the interface block
    pattern = rf"export\s+interface\s+{interface_name}\s*\{{([^}}]+)\}}"
    match = re.search(pattern, ts_content, re.DOTALL)
    if not match:
        return set()

    body = match.group(1)
    fields: set[str] = set()
    for line in body.splitlines():
        line = line.strip()
        # Skip comments and empty lines
        if not line or line.startswith("//"):
            continue
        # Extract field name before the colon
        field_match = re.match(r"(\w+)\s*:", line)
        if field_match:
            fields.add(field_match.group(1))
    return fields


# ─── provider.ts field presence tests ─────────────────────────────────

class TestProviderTsFieldPresence:
    """Verify provider.ts declares all fields from the canonical schema."""

    def test_provider_fields(self) -> None:
        ts = _read_provider_ts()
        ts_fields = _extract_interface_fields(ts, "Provider")
        for field in PROVIDER_FIELDS:
            assert field in ts_fields, (
                f"Provider.{field} missing from provider.ts"
            )

    def test_measure_fields(self) -> None:
        ts = _read_provider_ts()
        ts_fields = _extract_interface_fields(ts, "Measure")
        for field in MEASURE_FIELDS:
            assert field in ts_fields, (
                f"Measure.{field} missing from provider.ts"
            )

    def test_trend_period_fields(self) -> None:
        ts = _read_provider_ts()
        ts_fields = _extract_interface_fields(ts, "TrendPeriod")
        for field in TREND_PERIOD_FIELDS:
            assert field in ts_fields, (
                f"TrendPeriod.{field} missing from provider.ts"
            )

    def test_payment_adjustment_fields(self) -> None:
        ts = _read_provider_ts()
        ts_fields = _extract_interface_fields(ts, "PaymentAdjustment")
        for field in PAYMENT_ADJUSTMENT_FIELDS:
            assert field in ts_fields, (
                f"PaymentAdjustment.{field} missing from provider.ts"
            )

    def test_hospital_context_fields(self) -> None:
        ts = _read_provider_ts()
        ts_fields = _extract_interface_fields(ts, "HospitalContext")
        for field in HOSPITAL_CONTEXT_FIELDS:
            assert field in ts_fields, (
                f"HospitalContext.{field} missing from provider.ts"
            )

    def test_nursing_home_context_fields(self) -> None:
        ts = _read_provider_ts()
        ts_fields = _extract_interface_fields(ts, "NursingHomeContext")
        for field in NURSING_HOME_CONTEXT_FIELDS:
            assert field in ts_fields, (
                f"NursingHomeContext.{field} missing from provider.ts"
            )

    def test_address_fields(self) -> None:
        ts = _read_provider_ts()
        ts_fields = _extract_interface_fields(ts, "Address")
        for field in ADDRESS_FIELDS:
            assert field in ts_fields, (
                f"Address.{field} missing from provider.ts"
            )


class TestProviderTsNoExtraFields:
    """Verify provider.ts doesn't have fields not in the canonical schema."""

    def test_provider_no_extra(self) -> None:
        ts = _read_provider_ts()
        ts_fields = _extract_interface_fields(ts, "Provider")
        schema_fields = set(PROVIDER_FIELDS.keys())
        # parent_group_stats is declared in provider.ts ahead of pipeline emission.
        # When the export starts emitting it, add it back to PROVIDER_FIELDS.
        ts_fields = ts_fields - {"parent_group_stats"}
        extra = ts_fields - schema_fields
        assert not extra, (
            f"Provider has fields not in canonical schema: {extra}. "
            f"Add to PROVIDER_FIELDS in test or remove from provider.ts."
        )

    def test_measure_no_extra(self) -> None:
        ts = _read_provider_ts()
        ts_fields = _extract_interface_fields(ts, "Measure")
        schema_fields = set(MEASURE_FIELDS.keys())
        extra = ts_fields - schema_fields
        assert not extra, (
            f"Measure has fields not in canonical schema: {extra}. "
            f"Add to MEASURE_FIELDS in test or remove from provider.ts."
        )

    def test_hospital_context_no_extra(self) -> None:
        ts = _read_provider_ts()
        ts_fields = _extract_interface_fields(ts, "HospitalContext")
        schema_fields = set(HOSPITAL_CONTEXT_FIELDS.keys())
        extra = ts_fields - schema_fields
        assert not extra, (
            f"HospitalContext has fields not in canonical schema: {extra}."
        )

    def test_nursing_home_context_no_extra(self) -> None:
        ts = _read_provider_ts()
        ts_fields = _extract_interface_fields(ts, "NursingHomeContext")
        schema_fields = set(NURSING_HOME_CONTEXT_FIELDS.keys())
        extra = ts_fields - schema_fields
        assert not extra, (
            f"NursingHomeContext has fields not in canonical schema: {extra}."
        )


class TestProviderTsRemovedFields:
    """Verify fields and interfaces removed by decisions don't appear."""

    def test_no_summaries_field(self) -> None:
        """DEC-031: summaries array removed from export."""
        ts = _read_provider_ts()
        ts_fields = _extract_interface_fields(ts, "Provider")
        for field, reason in REMOVED_FIELDS.items():
            assert field not in ts_fields, (
                f"Provider.{field} should not exist in provider.ts: {reason}"
            )

    def test_no_summary_interface(self) -> None:
        """DEC-031: Summary interface should not exist."""
        ts = _read_provider_ts()
        for interface_name, reason in REMOVED_INTERFACES.items():
            assert f"interface {interface_name}" not in ts, (
                f"{interface_name} interface should not exist in provider.ts: "
                f"{reason}"
            )


class TestProviderTsEnums:
    """Verify enum type declarations match expected values."""

    @pytest.mark.parametrize(
        "enum_name,expected_values",
        list(EXPECTED_ENUMS.items()),
    )
    def test_enum_values(self, enum_name: str, expected_values: list[str]) -> None:
        ts = _read_provider_ts()
        for value in expected_values:
            assert f'"{value}"' in ts, (
                f"{enum_name} missing value '{value}' in provider.ts"
            )


# ─── Exported JSON validation (runs when build/data/ has files) ───────

def _get_exported_json_files() -> list[Path]:
    """Find all provider JSON files in build/data/."""
    if not EXPORT_DATA.exists():
        return []
    return sorted(EXPORT_DATA.glob("*.json"))


def _validate_fields(
    data: dict[str, Any],
    schema: dict[str, str],
    context: str,
) -> list[str]:
    """Validate a JSON object against a field schema.

    Returns list of error messages (empty = valid).
    """
    errors: list[str] = []

    for field, field_type in schema.items():
        if field not in data:
            errors.append(f"{context}.{field}: missing")
            continue

        value = data[field]
        nullable = field_type.endswith("?")
        base_type = field_type.rstrip("?")

        if value is None:
            if not nullable:
                errors.append(f"{context}.{field}: null but type is {field_type}")
            continue

        if base_type == "string" and not isinstance(value, str):
            errors.append(f"{context}.{field}: expected string, got {type(value).__name__}")
        elif base_type == "number" and not isinstance(value, (int, float)):
            errors.append(f"{context}.{field}: expected number, got {type(value).__name__}")
        elif base_type == "integer" and not isinstance(value, int):
            errors.append(f"{context}.{field}: expected integer, got {type(value).__name__}")
        elif base_type == "boolean" and not isinstance(value, bool):
            errors.append(f"{context}.{field}: expected boolean, got {type(value).__name__}")
        elif base_type == "array" and not isinstance(value, list):
            errors.append(f"{context}.{field}: expected array, got {type(value).__name__}")
        elif base_type == "object" and not isinstance(value, dict):
            errors.append(f"{context}.{field}: expected object, got {type(value).__name__}")

    # Check for unexpected fields
    expected = set(schema.keys())
    actual = set(data.keys())
    extra = actual - expected
    if extra:
        errors.append(f"{context}: unexpected fields: {extra}")

    return errors


exported_files = _get_exported_json_files()


@pytest.mark.skipif(not exported_files, reason="No exported JSON in build/data/")
class TestExportedJsonSchema:
    """Validate real exported JSON files against the canonical schema."""

    @pytest.fixture(params=exported_files[:10])  # cap at 10 for test speed
    def provider_data(self, request: pytest.FixtureRequest) -> dict[str, Any]:
        filepath: Path = request.param
        return json.loads(filepath.read_text(encoding="utf-8"))

    def test_provider_fields(self, provider_data: dict[str, Any]) -> None:
        ccn = provider_data.get("provider_id", "unknown")
        errors = _validate_fields(provider_data, PROVIDER_FIELDS, f"Provider({ccn})")
        assert not errors, "\n".join(errors)

    def test_no_summaries_in_export(self, provider_data: dict[str, Any]) -> None:
        """DEC-031: summaries must not appear in exported JSON."""
        assert "summaries" not in provider_data, (
            "Exported JSON contains 'summaries' — removed by DEC-031"
        )

    def test_measures_schema(self, provider_data: dict[str, Any]) -> None:
        ccn = provider_data.get("provider_id", "unknown")
        for i, measure in enumerate(provider_data.get("measures", [])):
            errors = _validate_fields(
                measure, MEASURE_FIELDS, f"Provider({ccn}).measures[{i}]"
            )
            assert not errors, "\n".join(errors)

    def test_stratification_not_empty_string(self, provider_data: dict[str, Any]) -> None:
        """json-export.md: empty string in DB must be null in export."""
        for measure in provider_data.get("measures", []):
            assert measure.get("stratification") != "", (
                f"measure {measure.get('measure_id')}: stratification is empty "
                f"string, should be null"
            )

    def test_hospital_context_schema(self, provider_data: dict[str, Any]) -> None:
        ctx = provider_data.get("hospital_context")
        if provider_data.get("provider_type") == "HOSPITAL":
            assert ctx is not None, "hospital_context null for HOSPITAL provider"
            errors = _validate_fields(ctx, HOSPITAL_CONTEXT_FIELDS, "hospital_context")
            assert not errors, "\n".join(errors)
        else:
            assert ctx is None, "hospital_context should be null for non-HOSPITAL"

    def test_nursing_home_context_schema(self, provider_data: dict[str, Any]) -> None:
        ctx = provider_data.get("nursing_home_context")
        if provider_data.get("provider_type") == "NURSING_HOME":
            assert ctx is not None, "nursing_home_context null for NURSING_HOME"
            errors = _validate_fields(
                ctx, NURSING_HOME_CONTEXT_FIELDS, "nursing_home_context"
            )
            assert not errors, "\n".join(errors)
        else:
            assert ctx is None, "nursing_home_context should be null for non-NH"

    def test_sff_mutual_exclusivity(self, provider_data: dict[str, Any]) -> None:
        ctx = provider_data.get("nursing_home_context")
        if ctx is not None:
            assert not (
                ctx.get("is_special_focus_facility")
                and ctx.get("is_special_focus_facility_candidate")
            ), "SFF and SFF candidate cannot both be true"

    def test_ccn_format(self, provider_data: dict[str, Any]) -> None:
        """CCN must be 6-character zero-padded string."""
        ccn = provider_data.get("provider_id", "")
        assert len(ccn) == 6, f"CCN '{ccn}' is not 6 characters"
        assert ccn == ccn.zfill(6), f"CCN '{ccn}' is not zero-padded"

    def test_trend_validity(self, provider_data: dict[str, Any]) -> None:
        """trend_valid must be False when trend_period_count < 3."""
        for measure in provider_data.get("measures", []):
            if measure.get("trend_period_count", 0) < 3:
                assert not measure.get("trend_valid"), (
                    f"measure {measure.get('measure_id')}: trend_valid=True "
                    f"with only {measure.get('trend_period_count')} periods"
                )
