"""Add cms_measure_definition to measures, ci_source / prior_source to provider_measure_values.

Revision ID: 005
Revises: 004
Create Date: 2026-05-05

DEC-037: cms_measure_definition stores verbatim CMS text from official data dictionaries
and measure specifications. This is the legally authoritative description that
establishes the republication chain. Must not be paraphrased.

DEC-029: ci_source and prior_source on provider_measure_values disclose how each
interval was produced — "cms_published" or "calculated", and the prior source for
calculated intervals ("state average", "national average", "minimally informative").
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "measures",
        sa.Column("cms_measure_definition", sa.Text(), nullable=True),
    )
    op.add_column(
        "provider_measure_values",
        sa.Column("ci_source", sa.String(), nullable=True),
    )
    op.add_column(
        "provider_measure_values",
        sa.Column("prior_source", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("provider_measure_values", "prior_source")
    op.drop_column("provider_measure_values", "ci_source")
    op.drop_column("measures", "cms_measure_definition")
