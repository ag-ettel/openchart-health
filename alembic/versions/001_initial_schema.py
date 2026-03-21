"""Initial schema — all tables, enums, and indexes for hospital and nursing home data.

Revision ID: 001
Revises: None
Create Date: 2026-03-19

Covers:
- PostgreSQL enum types (internal classifications only; CMS-originated strings use varchar per DEC-013/014)
- pipeline_runs (audit trail)
- providers (hospital + nursing home metadata, staffing context, inspection scoring)
- measures (MEASURE_REGISTRY mirror)
- provider_measure_values (all quality measures for all provider types)
- provider_payment_adjustments (HRRP, HACRP, VBP, SNF VBP — includes VBP domain scores per DEC-011)
- provider_inspection_events (nursing home deficiency citations)
- provider_ownership (nursing home entity-level ownership)
- provider_penalties (nursing home individual penalty records per DEC-025)

Schema decisions incorporated:
- DEC-013/014: hospital_type, hospital_ownership, provider_subtype, NH ownership_type stored as varchar
- DEC-016: observed_value, expected_value columns for claims quality measures
- DEC-022 (AMB-3): compared_to_national as varchar
- DEC-023 (AMB-4): count_suppressed bool for HRRP privacy-level count suppression
- DEC-024 (AMB-5): score_text varchar for EDV categorical scores
- DEC-025: provider_penalties table
- DEC-011: VBP domain score columns on provider_payment_adjustments
- DEC-010: provider_summaries table removed (deterministic templates, not stored)
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY, ENUM

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------------------------
# Enum definitions
#
# Only internal classifications are PostgreSQL enums. CMS-originated strings
# (hospital_type, hospital_ownership, ownership_type, provider_subtype,
# suppression_reason, compared_to_national) use varchar with application-layer
# validation per DEC-013/014.
# ---------------------------------------------------------------------------

PROVIDER_TYPE_VALUES = ("HOSPITAL", "NURSING_HOME", "HOME_HEALTH", "HOSPICE")

MEASURE_GROUP_VALUES = (
    # Hospital (9)
    "MORTALITY",
    "SAFETY",
    "COMPLICATIONS",
    "INFECTIONS",
    "READMISSIONS",
    "TIMELY_EFFECTIVE_CARE",
    "PATIENT_EXPERIENCE",
    "IMAGING_EFFICIENCY",
    "SPENDING",
    # Nursing home (8)
    "NH_QUALITY_LONG_STAY",
    "NH_QUALITY_SHORT_STAY",
    "NH_QUALITY_CLAIMS",
    "NH_STAFFING",
    "NH_STAR_RATING",
    "NH_INSPECTION",
    "NH_PENALTIES",
    "NH_SNF_QRP",
)

MEASURE_DIRECTION_VALUES = ("LOWER_IS_BETTER", "HIGHER_IS_BETTER")

RELIABILITY_FLAG_VALUES = ("RELIABLE", "LIMITED_SAMPLE", "NOT_REPORTED", "SUPPRESSED")

SES_SENSITIVITY_VALUES = ("HIGH", "MODERATE", "LOW", "UNKNOWN")

PAYMENT_PROGRAM_VALUES = ("HRRP", "HACRP", "VBP", "SNF_VBP")

# survey_type and not_reported_reason are VARCHAR, not PostgreSQL enums.
#
# survey_type: CMS Inspection Dates API uses compound strings like "Fire Safety
# Standard", "Health Standard", "Health Complaint", "Infection Control" — not our
# internal enum values. Same DEC-013/014 principle applies.
#
# not_reported_reason: Values are derived from CMS footnote codes and vary by dataset.
# Partially speculative (NOT_SUBMITTED, NOT_PARTICIPATING lack direct CMS data
# traceability). Using varchar with application-layer validation avoids pipeline
# failures when encountering undocumented CMS states.


def _create_enums() -> None:
    """Create all PostgreSQL enum types."""
    for name, values in [
        ("provider_type", PROVIDER_TYPE_VALUES),
        ("measure_group", MEASURE_GROUP_VALUES),
        ("measure_direction", MEASURE_DIRECTION_VALUES),
        ("reliability_flag", RELIABILITY_FLAG_VALUES),
        ("ses_sensitivity", SES_SENSITIVITY_VALUES),
        ("payment_program", PAYMENT_PROGRAM_VALUES),
    ]:
        op.execute(
            f"DO $$ BEGIN CREATE TYPE {name} AS ENUM ({', '.join(repr(v) for v in values)}); EXCEPTION WHEN duplicate_object THEN NULL; END $$"
        )


def _drop_enums() -> None:
    """Drop all PostgreSQL enum types in reverse order."""
    for name in [
        "payment_program",
        "ses_sensitivity",
        "reliability_flag",
        "measure_direction",
        "measure_group",
        "provider_type",
    ]:
        op.execute(f"DROP TYPE IF EXISTS {name}")


def upgrade() -> None:
    _create_enums()

    # ------------------------------------------------------------------
    # pipeline_runs — audit trail for every pipeline execution
    # ------------------------------------------------------------------
    op.create_table(
        "pipeline_runs",
        sa.Column("run_id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("datasets_fetched", JSONB, nullable=True),
        sa.Column("rows_upserted", sa.Integer, nullable=True),
        sa.Column("rows_failed", sa.Integer, nullable=True),
        sa.Column("anomalies", JSONB, nullable=True),
        sa.Column("api_version", sa.String, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # ------------------------------------------------------------------
    # providers — one row per provider (hospital or nursing home)
    # ------------------------------------------------------------------
    op.create_table(
        "providers",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("provider_id", sa.String(6), nullable=False, unique=True, comment="CCN, 6-char zero-padded"),
        sa.Column("provider_type", ENUM("HOSPITAL", "NURSING_HOME", "HOME_HEALTH", "HOSPICE", name="provider_type", create_type=False), nullable=False),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("address", JSONB, nullable=True, comment="keys: street, city, state, zip"),
        sa.Column("city", sa.String, nullable=True),
        sa.Column("state", sa.String(2), nullable=True),
        sa.Column("zip", sa.String(10), nullable=True),
        sa.Column("phone", sa.String, nullable=True),
        # provider_subtype: varchar per DEC-013/014, not enum
        sa.Column("provider_subtype", sa.String, nullable=True, comment="hospital_type or NH provider_type — varchar per DEC-013/014"),
        sa.Column("ownership_type", sa.String, nullable=True, comment="Normalized CMS ownership category"),
        sa.Column("ownership_type_raw", sa.String, nullable=True, comment="Raw CMS ownership string"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("first_seen_pipeline_run_id", UUID, sa.ForeignKey("pipeline_runs.run_id"), nullable=True),
        sa.Column("last_updated_pipeline_run_id", UUID, sa.ForeignKey("pipeline_runs.run_id"), nullable=True),

        # --- Hospital context fields confirmed from xubh-q36u ---
        sa.Column("is_critical_access", sa.Boolean, nullable=True),
        sa.Column("is_emergency_services", sa.Boolean, nullable=True),

        # --- Hospital context fields from xubh-q36u ---
        sa.Column("birthing_friendly_designation", sa.Boolean, nullable=True, comment="DEC-007"),
        sa.Column("hospital_overall_rating", sa.SmallInteger, nullable=True, comment="1-5 integer from xubh-q36u"),
        sa.Column("hospital_overall_rating_footnote", sa.String(8), nullable=True),

        # --- Hospital star rating group fields (DEC-009) ---
        sa.Column("count_of_facility_mort_measures", sa.SmallInteger, nullable=True),
        sa.Column("count_of_facility_readm_measures", sa.SmallInteger, nullable=True),
        sa.Column("count_of_facility_safety_measures", sa.SmallInteger, nullable=True),
        sa.Column("count_of_facility_pt_exp_measures", sa.SmallInteger, nullable=True),
        sa.Column("count_of_facility_te_measures", sa.SmallInteger, nullable=True),
        sa.Column("mort_group_footnote", sa.String(8), nullable=True),
        sa.Column("readm_group_footnote", sa.String(8), nullable=True),
        sa.Column("safety_group_footnote", sa.String(8), nullable=True),
        sa.Column("pt_exp_group_footnote", sa.String(8), nullable=True),
        sa.Column("te_group_footnote", sa.String(8), nullable=True),

        # --- Nursing home metadata from Provider Information (4pq5-n9py) ---
        sa.Column("certified_beds", sa.Integer, nullable=True, comment="NH only: number_of_certified_beds"),
        sa.Column("average_daily_census", sa.Numeric(8, 2), nullable=True, comment="NH only"),
        sa.Column("resident_capacity", sa.Integer, nullable=True, comment="NH only"),
        sa.Column("is_continuing_care_retirement_community", sa.Boolean, nullable=True, comment="NH only"),
        sa.Column("is_special_focus_facility", sa.Boolean, nullable=True, comment="NH only: active SFF"),
        sa.Column("is_special_focus_facility_candidate", sa.Boolean, nullable=True, comment="NH only"),
        sa.Column("is_hospital_based", sa.Boolean, nullable=True, comment="NH only"),
        sa.Column("is_abuse_icon", sa.Boolean, nullable=True, comment="NH only: surface prominently"),
        sa.Column("is_urban", sa.Boolean, nullable=True, comment="NH only: from Provider Info urban field"),
        sa.Column("chain_name", sa.String, nullable=True, comment="NH only"),
        sa.Column("chain_id", sa.String, nullable=True, comment="NH only"),
        sa.Column("ownership_changed_recently", sa.Boolean, nullable=True, comment="NH: changed in last 12 months"),
        sa.Column("inspection_overdue", sa.Boolean, nullable=True, comment="NH: most recent health inspection >2yr ago"),
        sa.Column("resident_family_council", sa.String, nullable=True, comment="NH: Resident/Family/Both/None"),
        sa.Column("sprinkler_status", sa.String, nullable=True, comment="NH: Yes/Partial/No/Data Not Available"),
        sa.Column("processing_date", sa.Date, nullable=True, comment="CMS processing date for latest data"),
        sa.Column("latitude", sa.Numeric(10, 7), nullable=True),
        sa.Column("longitude", sa.Numeric(10, 7), nullable=True),

        # --- NH staffing context fields (DEC-018: context-only, not MEASURE_REGISTRY) ---
        sa.Column("reported_lpn_hprd", sa.Numeric(8, 4), nullable=True, comment="NH: LPN hours per resident day"),
        sa.Column("reported_licensed_hprd", sa.Numeric(8, 4), nullable=True, comment="NH: RN+LPN combined"),
        sa.Column("weekend_rn_hprd", sa.Numeric(8, 4), nullable=True, comment="NH: weekend RN hours"),
        sa.Column("pt_hprd", sa.Numeric(8, 4), nullable=True, comment="NH: physical therapist hours"),
        sa.Column("nursing_casemix_index", sa.Numeric(8, 4), nullable=True, comment="NH: PDPM case-mix index"),
        sa.Column("nursing_casemix_index_ratio", sa.Numeric(8, 4), nullable=True, comment="NH: case-mix ratio"),
        sa.Column("casemix_aide_hprd", sa.Numeric(8, 4), nullable=True, comment="NH: case-mix adjusted"),
        sa.Column("casemix_lpn_hprd", sa.Numeric(8, 4), nullable=True, comment="NH: case-mix adjusted"),
        sa.Column("casemix_rn_hprd", sa.Numeric(8, 4), nullable=True, comment="NH: case-mix adjusted"),
        sa.Column("casemix_licensed_hprd", sa.Numeric(8, 4), nullable=True, comment="NH: case-mix adjusted"),
        sa.Column("casemix_total_hprd", sa.Numeric(8, 4), nullable=True, comment="NH: case-mix adjusted"),
        sa.Column("adjusted_aide_hprd", sa.Numeric(8, 4), nullable=True, comment="NH: adjusted staffing"),
        sa.Column("adjusted_lpn_hprd", sa.Numeric(8, 4), nullable=True, comment="NH: adjusted staffing"),
        sa.Column("adjusted_rn_hprd", sa.Numeric(8, 4), nullable=True, comment="NH: adjusted staffing"),
        sa.Column("adjusted_licensed_hprd", sa.Numeric(8, 4), nullable=True, comment="NH: adjusted staffing"),
        sa.Column("adjusted_total_hprd", sa.Numeric(8, 4), nullable=True, comment="NH: adjusted staffing"),

        # --- NH inspection scoring context from Provider Information ---
        sa.Column("cycle_1_survey_date", sa.Date, nullable=True, comment="NH: most recent standard survey"),
        sa.Column("cycle_1_total_health_deficiencies", sa.Integer, nullable=True),
        sa.Column("cycle_1_standard_health_deficiencies", sa.Integer, nullable=True),
        sa.Column("cycle_1_complaint_health_deficiencies", sa.Integer, nullable=True),
        sa.Column("cycle_1_health_deficiency_score", sa.Numeric(8, 3), nullable=True),
        sa.Column("cycle_1_health_revisits", sa.Integer, nullable=True),
        sa.Column("cycle_1_health_revisit_score", sa.Numeric(8, 3), nullable=True),
        sa.Column("cycle_1_total_health_score", sa.Numeric(8, 3), nullable=True),
        sa.Column("cycle_2_survey_date", sa.Date, nullable=True),
        sa.Column("cycle_23_total_health_deficiencies", sa.Integer, nullable=True),
        sa.Column("cycle_23_standard_health_deficiencies", sa.Integer, nullable=True),
        sa.Column("cycle_23_complaint_health_deficiencies", sa.Integer, nullable=True),
        sa.Column("cycle_23_health_deficiency_score", sa.Numeric(8, 3), nullable=True),
        sa.Column("cycle_23_health_revisits", sa.Integer, nullable=True),
        sa.Column("cycle_23_health_revisit_score", sa.Numeric(8, 3), nullable=True),
        sa.Column("cycle_23_total_health_score", sa.Numeric(8, 3), nullable=True),
        sa.Column("total_weighted_health_survey_score", sa.Numeric(8, 3), nullable=True),
        sa.Column("infection_control_citations", sa.Integer, nullable=True, comment="NH: from Provider Info"),

        # --- NH chain average ratings (context for chain comparison) ---
        sa.Column("chain_average_overall_rating", sa.Numeric(3, 1), nullable=True),
        sa.Column("chain_average_health_inspection_rating", sa.Numeric(3, 1), nullable=True),
        sa.Column("chain_average_staffing_rating", sa.Numeric(3, 1), nullable=True),
        sa.Column("chain_average_qm_rating", sa.Numeric(3, 1), nullable=True),

        # --- NH penalty summary from Provider Information ---
        sa.Column("number_of_fines", sa.Integer, nullable=True, comment="NH: from Provider Info"),
        sa.Column("total_amount_of_fines_dollars", sa.Numeric(12, 2), nullable=True, comment="NH"),
        sa.Column("number_of_payment_denials", sa.Integer, nullable=True, comment="NH"),
        sa.Column("total_number_of_penalties", sa.Integer, nullable=True, comment="NH"),

        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # providers indexes
    op.create_index("ix_providers_city", "providers", ["city"])
    op.create_index("ix_providers_state", "providers", ["state"])
    op.create_index("ix_providers_provider_type", "providers", ["provider_type"])
    op.create_index("ix_providers_provider_subtype", "providers", ["provider_subtype"])

    # ------------------------------------------------------------------
    # measures — reference table mirroring MEASURE_REGISTRY
    # ------------------------------------------------------------------
    op.create_table(
        "measures",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("measure_id", sa.String, nullable=False, unique=True),
        sa.Column("measure_name", sa.String, nullable=False),
        sa.Column("measure_plain_language", sa.Text, nullable=True),
        sa.Column("measure_group", ENUM(*MEASURE_GROUP_VALUES, name="measure_group", create_type=False), nullable=False),
        sa.Column("direction", ENUM(*MEASURE_DIRECTION_VALUES, name="measure_direction", create_type=False), nullable=True,
                  comment="NULL for measures with no meaningful quality direction (EDV, HCAHPS middlebox)"),
        sa.Column("unit", sa.String, nullable=True),
        sa.Column("tail_risk_flag", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("ses_sensitivity", ENUM(*SES_SENSITIVITY_VALUES, name="ses_sensitivity", create_type=False), nullable=False),
        sa.Column("direction_source", sa.String, nullable=True,
                  comment="DEC-011: CMS_API, CMS_DATA_DICTIONARY, CMS_MEASURE_SPEC, or CMS_MEASURE_DEFINITION"),
        sa.Column("risk_adjustment_model", sa.String, nullable=True,
                  comment="DEC-021: HGLM, SIR, PATIENT_MIX_ADJUSTMENT, NONE, OTHER"),
        sa.Column("cms_ci_published", sa.Boolean, nullable=True,
                  comment="DEC-021: whether CMS publishes CI bounds"),
        sa.Column("numerator_denominator_published", sa.Boolean, nullable=True,
                  comment="DEC-021: whether raw counts are available"),
        sa.Column("dataset_id", sa.String, nullable=True,
                  comment="CMS Socrata dataset ID for provenance"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # ------------------------------------------------------------------
    # provider_measure_values — all measure data for all provider types
    # ------------------------------------------------------------------
    op.create_table(
        "provider_measure_values",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("provider_id", sa.String(6), nullable=False),
        sa.Column("provider_type", ENUM(*PROVIDER_TYPE_VALUES, name="provider_type", create_type=False), nullable=False),
        sa.Column("source_dataset_id", sa.String, nullable=False, comment="CMS dataset identifier from config.py"),
        sa.Column("measure_id", sa.String, nullable=False),

        # Stratification
        sa.Column("stratification", sa.String, nullable=False, server_default=sa.text("''"),
                  comment="Empty string for non-stratified; never NULL"),

        # Values
        sa.Column("raw_value", sa.String, nullable=True, comment="Exactly as received from CMS API (Rule 7)"),
        sa.Column("numeric_value", sa.Numeric(12, 4), nullable=True, comment="NULL if suppressed, not_reported, or categorical"),
        sa.Column("score_text", sa.String, nullable=True, comment="DEC-024 (AMB-5): categorical score for EDV etc."),
        sa.Column("confidence_interval_lower", sa.Numeric(12, 4), nullable=True,
                  comment="CMS-published or Bayesian credible interval (DEC-008)"),
        sa.Column("confidence_interval_upper", sa.Numeric(12, 4), nullable=True,
                  comment="CMS-published or Bayesian credible interval (DEC-008)"),
        sa.Column("observed_value", sa.Numeric(12, 4), nullable=True,
                  comment="DEC-016: NH claims O/E observed score"),
        sa.Column("expected_value", sa.Numeric(12, 4), nullable=True,
                  comment="DEC-016: NH claims O/E expected score"),
        sa.Column("compared_to_national", sa.String, nullable=True,
                  comment="DEC-022 (AMB-3): canonical values BETTER/NO_DIFFERENT/WORSE/TOO_FEW_CASES/NOT_AVAILABLE"),

        # Suppression and reporting status
        sa.Column("suppressed", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("suppression_reason", sa.String, nullable=True, comment="VARCHAR — CMS reasons vary by dataset"),
        sa.Column("not_reported", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("not_reported_reason", sa.String, nullable=True,
                  comment="VARCHAR — derived from CMS footnote codes, varies by dataset"),
        sa.Column("count_suppressed", sa.Boolean, nullable=False, server_default=sa.text("false"),
                  comment="DEC-023 (AMB-4): count fields suppressed but primary value populated"),

        # Footnotes
        sa.Column("footnote_codes", ARRAY(sa.Integer), nullable=True),
        sa.Column("footnote_text", ARRAY(sa.Text), nullable=True),

        # Reporting period
        sa.Column("period_start", sa.Date, nullable=True),
        sa.Column("period_end", sa.Date, nullable=True),
        sa.Column("period_label", sa.String, nullable=False),

        # Sample size and denominators
        sa.Column("sample_size", sa.Integer, nullable=True),
        sa.Column("denominator", sa.Integer, nullable=True),

        # Reliability
        sa.Column("reliability_flag",
                  ENUM(*RELIABILITY_FLAG_VALUES, name="reliability_flag", create_type=False),
                  nullable=True),

        # Benchmarks
        sa.Column("national_avg", sa.Numeric(12, 4), nullable=True),
        sa.Column("national_avg_period", sa.String, nullable=True),
        sa.Column("state_avg", sa.Numeric(12, 4), nullable=True),
        sa.Column("state_avg_period", sa.String, nullable=True),

        # Audit
        sa.Column("pipeline_run_id", UUID, sa.ForeignKey("pipeline_runs.run_id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # Upsert key: (provider_id, measure_id, period_label, stratification)
    op.create_unique_constraint(
        "uq_pmv_upsert_key",
        "provider_measure_values",
        ["provider_id", "measure_id", "period_label", "stratification"],
    )

    # FK to providers (on CCN, not UUID)
    op.create_foreign_key(
        "fk_pmv_provider_id",
        "provider_measure_values", "providers",
        ["provider_id"], ["provider_id"],
    )

    # FK to measures (on measure_id string)
    op.create_foreign_key(
        "fk_pmv_measure_id",
        "provider_measure_values", "measures",
        ["measure_id"], ["measure_id"],
    )

    # Performance indexes
    op.create_index("ix_pmv_provider_id", "provider_measure_values", ["provider_id"])
    op.create_index("ix_pmv_measure_id", "provider_measure_values", ["measure_id"])
    op.create_index("ix_pmv_provider_type", "provider_measure_values", ["provider_type"])
    op.create_index("ix_pmv_suppressed", "provider_measure_values", ["suppressed"],
                    postgresql_where=sa.text("suppressed = true"))

    # ------------------------------------------------------------------
    # provider_payment_adjustments
    # ------------------------------------------------------------------
    op.create_table(
        "provider_payment_adjustments",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("provider_id", sa.String(6), nullable=False),
        sa.Column("program", ENUM(*PAYMENT_PROGRAM_VALUES, name="payment_program", create_type=False), nullable=False),
        sa.Column("program_year", sa.Integer, nullable=False, comment="Federal fiscal year"),
        sa.Column("penalty_flag", sa.Boolean, nullable=True),
        sa.Column("payment_adjustment_pct", sa.Numeric(8, 4), nullable=True, comment="Negative = penalty, positive = bonus"),
        sa.Column("total_score", sa.Numeric(8, 4), nullable=True),
        sa.Column("score_percentile", sa.Numeric(6, 2), nullable=True),
        sa.Column("source_dataset_id", sa.String, nullable=False),

        # --- VBP domain scores (DEC-011) ---
        sa.Column("total_performance_score", sa.Numeric(8, 4), nullable=True),
        sa.Column("unweighted_normalized_clinical_outcomes_domain_score", sa.Numeric(8, 4), nullable=True),
        sa.Column("unweighted_efficiency_and_cost_reduction_domain_score", sa.Numeric(8, 4), nullable=True,
                  comment="DEC-011: dropped _normalized_ to stay under 63 chars"),
        sa.Column("unweighted_normalized_safety_domain_score", sa.Numeric(8, 4), nullable=True),
        sa.Column("unweighted_person_and_community_engagement_domain_score", sa.Numeric(8, 4), nullable=True),
        sa.Column("weighted_normalized_clinical_outcomes_domain_score", sa.Numeric(8, 4), nullable=True),
        sa.Column("weighted_efficiency_and_cost_reduction_domain_score", sa.Numeric(8, 4), nullable=True),
        sa.Column("weighted_safety_domain_score", sa.Numeric(8, 4), nullable=True),
        sa.Column("weighted_person_and_community_engagement_domain_score", sa.Numeric(8, 4), nullable=True),

        # --- HACRP fields ---
        sa.Column("total_hac_score", sa.Numeric(8, 4), nullable=True, comment="HACRP aggregate score"),
        sa.Column("payment_reduction", sa.Boolean, nullable=True, comment="HACRP payment reduction flag"),

        # --- SNF VBP fields ---
        sa.Column("baseline_rate", sa.Numeric(8, 4), nullable=True, comment="SNF VBP baseline period rate"),
        sa.Column("performance_rate", sa.Numeric(8, 4), nullable=True, comment="SNF VBP performance period rate"),
        sa.Column("achievement_score", sa.Numeric(8, 4), nullable=True),
        sa.Column("improvement_score", sa.Numeric(8, 4), nullable=True),
        sa.Column("measure_score", sa.Numeric(8, 4), nullable=True),
        sa.Column("incentive_payment_multiplier", sa.Numeric(8, 6), nullable=True, comment="SNF VBP payment multiplier"),

        sa.Column("pipeline_run_id", UUID, sa.ForeignKey("pipeline_runs.run_id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # Upsert key: (provider_id, program, program_year)
    op.create_unique_constraint(
        "uq_ppa_upsert_key",
        "provider_payment_adjustments",
        ["provider_id", "program", "program_year"],
    )

    op.create_foreign_key(
        "fk_ppa_provider_id",
        "provider_payment_adjustments", "providers",
        ["provider_id"], ["provider_id"],
    )

    op.create_index("ix_ppa_provider_id", "provider_payment_adjustments", ["provider_id"])
    op.create_index("ix_ppa_program", "provider_payment_adjustments", ["program"])

    # ------------------------------------------------------------------
    # provider_inspection_events — NH deficiency citations
    # ------------------------------------------------------------------
    op.create_table(
        "provider_inspection_events",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("provider_id", sa.String(6), nullable=False),
        sa.Column("provider_type", ENUM(*PROVIDER_TYPE_VALUES, name="provider_type", create_type=False), nullable=False),
        sa.Column("event_id", sa.String, nullable=False, comment="CMS survey event identifier"),
        sa.Column("survey_date", sa.Date, nullable=False),
        sa.Column("survey_type", sa.String, nullable=True,
                  comment="CMS strings: Fire Safety Standard, Health Standard, Health Complaint, Infection Control — varchar per DEC-013/014"),
        sa.Column("deficiency_tag", sa.String, nullable=False, comment="F-tag/K-tag e.g. F0690"),
        sa.Column("deficiency_description", sa.Text, nullable=True, comment="Denormalized from CMS tag reference"),
        sa.Column("deficiency_category", sa.String, nullable=True, comment="CMS deficiency category name"),
        sa.Column("scope_severity_code", sa.String(1), nullable=True, comment="A through L"),
        sa.Column("is_immediate_jeopardy", sa.Boolean, nullable=False, server_default=sa.text("false"),
                  comment="True when scope_severity_code in {J,K,L}"),
        sa.Column("is_complaint_deficiency", sa.Boolean, nullable=False, server_default=sa.text("false"),
                  comment="True when from complaint investigation"),
        sa.Column("correction_date", sa.Date, nullable=True),
        sa.Column("inspection_cycle", sa.SmallInteger, nullable=True, comment="1=most recent, 2, 3"),

        # Citation lifecycle tracking (DEC-028)
        sa.Column("originally_published_scope_severity", sa.String(1), nullable=True,
                  comment="DEC-028: scope/severity from first CMS snapshot; never updated after insert"),
        sa.Column("is_contested", sa.Boolean, nullable=False, server_default=sa.text("false"),
                  comment="DEC-028: true when scope_severity_code changed from a prior snapshot"),
        sa.Column("scope_severity_history", JSONB, nullable=True,
                  comment="DEC-028: [{code, vintage, idr}] array tracking all observed states"),
        sa.Column("originally_published_vintage", sa.String, nullable=True,
                  comment="DEC-028: CMS release date when citation first appeared (e.g. 2024-01)"),
        sa.Column("last_seen_vintage", sa.String, nullable=True,
                  comment="DEC-028: most recent CMS release containing this citation"),

        sa.Column("raw_row", JSONB, nullable=True, comment="Complete raw CMS API row per Rule 7"),
        sa.Column("source_dataset_id", sa.String, nullable=False),
        sa.Column("pipeline_run_id", UUID, sa.ForeignKey("pipeline_runs.run_id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # Upsert key: (provider_id, event_id, deficiency_tag)
    op.create_unique_constraint(
        "uq_pie_upsert_key",
        "provider_inspection_events",
        ["provider_id", "event_id", "deficiency_tag"],
    )

    op.create_foreign_key(
        "fk_pie_provider_id",
        "provider_inspection_events", "providers",
        ["provider_id"], ["provider_id"],
    )

    op.create_index("ix_pie_provider_id", "provider_inspection_events", ["provider_id"])
    op.create_index("ix_pie_survey_date", "provider_inspection_events", ["survey_date"])
    op.create_index("ix_pie_scope_severity", "provider_inspection_events", ["scope_severity_code"])
    op.create_index("ix_pie_immediate_jeopardy", "provider_inspection_events", ["is_immediate_jeopardy"],
                    postgresql_where=sa.text("is_immediate_jeopardy = true"))
    op.create_index("ix_pie_contested", "provider_inspection_events", ["is_contested"],
                    postgresql_where=sa.text("is_contested = true"))

    # ------------------------------------------------------------------
    # provider_ownership — NH entity-level ownership records
    # ------------------------------------------------------------------
    op.create_table(
        "provider_ownership",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("provider_id", sa.String(6), nullable=False),
        sa.Column("provider_type", ENUM(*PROVIDER_TYPE_VALUES, name="provider_type", create_type=False), nullable=False),
        sa.Column("owner_name", sa.String, nullable=False),
        sa.Column("owner_type", sa.String, nullable=False, comment="Individual or Organization"),
        sa.Column("role", sa.String, nullable=False, comment="11 confirmed role values from CMS"),
        sa.Column("ownership_percentage", sa.Integer, nullable=True),
        sa.Column("ownership_percentage_raw", sa.String, nullable=False, comment="Rule 7: exactly as received"),
        sa.Column("ownership_percentage_not_provided", sa.Boolean, nullable=False, server_default=sa.text("false"),
                  comment="True when raw = NO PERCENTAGE PROVIDED; distinct from NOT APPLICABLE"),
        sa.Column("association_date", sa.Date, nullable=True),
        sa.Column("association_date_raw", sa.String, nullable=False, comment="Rule 7: exactly as received"),
        sa.Column("source_dataset_id", sa.String, nullable=False),
        sa.Column("pipeline_run_id", UUID, sa.ForeignKey("pipeline_runs.run_id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # Upsert key: (provider_id, owner_name, role)
    op.create_unique_constraint(
        "uq_po_upsert_key",
        "provider_ownership",
        ["provider_id", "owner_name", "role"],
    )

    op.create_foreign_key(
        "fk_po_provider_id",
        "provider_ownership", "providers",
        ["provider_id"], ["provider_id"],
    )

    op.create_index("ix_po_provider_id", "provider_ownership", ["provider_id"])
    op.create_index("ix_po_owner_name_type", "provider_ownership", ["owner_name", "owner_type"])

    # ------------------------------------------------------------------
    # provider_penalties — NH individual penalty records (DEC-025)
    # ------------------------------------------------------------------
    op.create_table(
        "provider_penalties",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("provider_id", sa.String(6), nullable=False),
        sa.Column("provider_type", ENUM(*PROVIDER_TYPE_VALUES, name="provider_type", create_type=False), nullable=False),
        sa.Column("penalty_date", sa.Date, nullable=False),
        sa.Column("penalty_type", sa.String, nullable=False, comment="Fine or Payment Denial"),
        sa.Column("fine_amount", sa.Numeric(12, 2), nullable=True, comment="Populated when penalty_type=Fine"),
        sa.Column("payment_denial_start_date", sa.Date, nullable=True),
        sa.Column("payment_denial_length_days", sa.Integer, nullable=True),

        # Penalty lifecycle tracking (DEC-028 pattern)
        sa.Column("originally_published_fine_amount", sa.Numeric(12, 2), nullable=True,
                  comment="Fine amount from first CMS snapshot; never updated after insert"),
        sa.Column("originally_published_vintage", sa.String, nullable=True,
                  comment="CMS release date when penalty first appeared"),
        sa.Column("last_seen_vintage", sa.String, nullable=True,
                  comment="Most recent CMS release containing this penalty"),

        sa.Column("raw_row", JSONB, nullable=True, comment="Complete raw CMS API row per Rule 7"),
        sa.Column("source_dataset_id", sa.String, nullable=False),
        sa.Column("pipeline_run_id", UUID, sa.ForeignKey("pipeline_runs.run_id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # Upsert key: (provider_id, penalty_date, penalty_type)
    op.create_unique_constraint(
        "uq_pp_upsert_key",
        "provider_penalties",
        ["provider_id", "penalty_date", "penalty_type"],
    )

    op.create_foreign_key(
        "fk_pp_provider_id",
        "provider_penalties", "providers",
        ["provider_id"], ["provider_id"],
    )

    op.create_index("ix_pp_provider_id", "provider_penalties", ["provider_id"])
    op.create_index("ix_pp_penalty_date", "provider_penalties", ["penalty_date"])


def downgrade() -> None:
    op.drop_table("provider_penalties")
    op.drop_table("provider_ownership")
    op.drop_table("provider_inspection_events")
    op.drop_table("provider_payment_adjustments")
    op.drop_table("provider_measure_values")
    op.drop_table("measures")
    op.drop_table("providers")
    op.drop_table("pipeline_runs")
    _drop_enums()
