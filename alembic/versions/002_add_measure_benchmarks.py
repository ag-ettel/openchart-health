"""Add measure_benchmarks table for national and state averages.

Revision ID: 002
Revises: 001
Create Date: 2026-03-22

Stores per-measure, per-period national and state average values sourced from
CMS companion CSV files (-National.csv, -State.csv). Used by:
- Export layer: populates national_avg / state_avg in JSON export
- Transform layer: Bayesian credible interval prior selection (DEC-029, DEC-036)

Schema per database-schema.md § measure_benchmarks Table.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "measure_benchmarks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("measure_id", sa.String(), sa.ForeignKey("measures.measure_id"), nullable=False),
        sa.Column("geography_type", sa.String(), nullable=False, comment="'national' or 'state'"),
        sa.Column("geography_code", sa.String(), nullable=False, comment="'US' for national, state abbreviation for state"),
        sa.Column("period_label", sa.String(), nullable=False),
        sa.Column("avg_value", sa.Numeric(12, 4), nullable=False),
        sa.Column("sample_size", sa.Integer(), nullable=True, comment="Number of providers contributing"),
        sa.Column("source", sa.String(), nullable=False, comment="CMS filename pattern"),
        sa.Column("source_vintage", sa.String(), nullable=True, comment="Archive vintage label"),
        sa.Column("pipeline_run_id", UUID(as_uuid=True), sa.ForeignKey("pipeline_runs.run_id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # Upsert key
    op.create_unique_constraint(
        "uq_measure_benchmarks_upsert",
        "measure_benchmarks",
        ["measure_id", "geography_type", "geography_code", "period_label"],
    )

    # Indexes per schema spec
    op.create_index("ix_measure_benchmarks_measure_id", "measure_benchmarks", ["measure_id"])
    op.create_index("ix_measure_benchmarks_geography", "measure_benchmarks", ["geography_type", "geography_code"])


def downgrade() -> None:
    op.drop_index("ix_measure_benchmarks_geography", table_name="measure_benchmarks")
    op.drop_index("ix_measure_benchmarks_measure_id", table_name="measure_benchmarks")
    op.drop_constraint("uq_measure_benchmarks_upsert", "measure_benchmarks", type_="unique")
    op.drop_table("measure_benchmarks")
