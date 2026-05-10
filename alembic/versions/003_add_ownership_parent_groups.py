"""Add ownership_parent_groups and ownership_entity_group_map tables.

Revision ID: 003
Revises: 002
Create Date: 2026-03-24

Supports semi-automated entity resolution for nursing home ownership data.
Maps ~12,000 distinct CMS entity names to ~500 parent corporate groups.
Schema per docs/ownership_entity_resolution.md.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers
revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ownership_parent_groups",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("parent_group_id", sa.String(), nullable=False, unique=True,
                  comment="URL-safe slug, e.g. 'genesis_healthcare'"),
        sa.Column("parent_group_name", sa.String(), nullable=False,
                  comment="Display name, e.g. 'Genesis Healthcare'"),
        sa.Column("entity_type", sa.String(), nullable=True,
                  comment="CMS-derived: e.g. 'chain_operator', 'nonprofit_system', 'management_company'"),
        sa.Column("ownership_structure_type", sa.String(), nullable=True,
                  comment="Structural classification: e.g. 'family_investment_layered', 'nonprofit_operator'"),
        sa.Column("structural_tags", sa.ARRAY(sa.String()), nullable=True,
                  comment="Individual structural signals: FAMILY_CONTROLLED, INVESTMENT_FUND_PRESENCE, etc."),
        sa.Column("notes", sa.Text(), nullable=True,
                  comment="Human reviewer notes"),
        sa.Column("review_status", sa.String(), nullable=False, server_default="auto_matched",
                  comment="auto_matched, human_verified, or disputed"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "ownership_entity_group_map",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("entity_name", sa.String(), nullable=False,
                  comment="Exact match to provider_ownership.owner_name"),
        sa.Column("parent_group_id", sa.String(),
                  sa.ForeignKey("ownership_parent_groups.parent_group_id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("match_method", sa.String(), nullable=False,
                  comment="exact, fuzzy, facility_overlap, chain_crossref, manual"),
        sa.Column("match_confidence", sa.Numeric(3, 2), nullable=False,
                  comment="0.00-1.00"),
        sa.Column("reviewed_by", sa.String(), nullable=True,
                  comment="Human reviewer identifier"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # Upsert key: one entity name per parent group
    op.create_unique_constraint(
        "uq_oegm_entity_name",
        "ownership_entity_group_map",
        ["entity_name"],
    )

    # Indexes
    op.create_index("ix_oegm_parent_group_id", "ownership_entity_group_map", ["parent_group_id"])
    op.create_index("ix_oegm_entity_name", "ownership_entity_group_map", ["entity_name"])


def downgrade() -> None:
    op.drop_index("ix_oegm_entity_name", table_name="ownership_entity_group_map")
    op.drop_index("ix_oegm_parent_group_id", table_name="ownership_entity_group_map")
    op.drop_constraint("uq_oegm_entity_name", "ownership_entity_group_map", type_="unique")
    op.drop_table("ownership_entity_group_map")
    op.drop_table("ownership_parent_groups")
