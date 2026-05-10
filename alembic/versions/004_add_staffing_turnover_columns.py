"""Add reported staffing, turnover, and missing inspection columns to providers.

Revision ID: 004
Revises: 003
Create Date: 2026-04-17

Columns that exist in CMS NH Provider Info but were missing from the schema:
- reported_rn_hprd, reported_total_hprd, reported_aide_hprd (raw PBJ hours)
- total_nursing_staff_turnover, rn_turnover, administrator_departures
- infection_control_citations
- adjusted_weekend_total_hprd, casemix_weekend_total_hprd
- weekend_total_hprd (reported)
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Reported staffing (raw PBJ, before case-mix adjustment)
    op.add_column("providers", sa.Column("reported_rn_hprd", sa.Numeric(8, 4), nullable=True))
    op.add_column("providers", sa.Column("reported_total_hprd", sa.Numeric(8, 4), nullable=True))
    op.add_column("providers", sa.Column("reported_aide_hprd", sa.Numeric(8, 4), nullable=True))

    # Weekend staffing
    op.add_column("providers", sa.Column("weekend_total_hprd", sa.Numeric(8, 4), nullable=True))
    op.add_column("providers", sa.Column("adjusted_weekend_total_hprd", sa.Numeric(8, 4), nullable=True))
    op.add_column("providers", sa.Column("casemix_weekend_total_hprd", sa.Numeric(8, 4), nullable=True))

    # Turnover
    op.add_column("providers", sa.Column("total_nursing_staff_turnover", sa.Numeric(6, 2), nullable=True))
    op.add_column("providers", sa.Column("rn_turnover", sa.Numeric(6, 2), nullable=True))
    op.add_column("providers", sa.Column("administrator_departures", sa.Integer(), nullable=True))

    # infection_control_citations already exists from migration 001


def downgrade() -> None:
    op.drop_column("providers", "administrator_departures")
    op.drop_column("providers", "rn_turnover")
    op.drop_column("providers", "total_nursing_staff_turnover")
    op.drop_column("providers", "casemix_weekend_total_hprd")
    op.drop_column("providers", "adjusted_weekend_total_hprd")
    op.drop_column("providers", "weekend_total_hprd")
    op.drop_column("providers", "reported_aide_hprd")
    op.drop_column("providers", "reported_total_hprd")
    op.drop_column("providers", "reported_rn_hprd")
