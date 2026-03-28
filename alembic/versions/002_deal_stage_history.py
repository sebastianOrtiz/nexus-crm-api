"""Add deal_stage_history table

Revision ID: 002
Revises: 001
Create Date: 2026-03-27 00:00:00

Adds ``crm.deal_stage_history`` to track every pipeline stage transition for
a deal — recording which stage was entered, who triggered the move, and the
entry/exit timestamps.  An open entry (``exited_at`` IS NULL) means the deal
is currently in that stage.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "deal_stage_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("deal_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("stage_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("moved_by_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("exited_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["deal_id"], ["crm.deals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["stage_id"], ["crm.pipeline_stages.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["moved_by_id"], ["crm.users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        schema="crm",
    )
    op.create_index("ix_crm_deal_stage_history_id", "deal_stage_history", ["id"], schema="crm")
    op.create_index(
        "ix_crm_deal_stage_history_deal_id_entered_at",
        "deal_stage_history",
        ["deal_id", "entered_at"],
        schema="crm",
    )
    op.create_index(
        "ix_crm_deal_stage_history_stage_id",
        "deal_stage_history",
        ["stage_id"],
        schema="crm",
    )
    op.create_index(
        "ix_crm_deal_stage_history_moved_by_id",
        "deal_stage_history",
        ["moved_by_id"],
        schema="crm",
    )


def downgrade() -> None:
    op.drop_index("ix_crm_deal_stage_history_moved_by_id", table_name="deal_stage_history", schema="crm")
    op.drop_index("ix_crm_deal_stage_history_stage_id", table_name="deal_stage_history", schema="crm")
    op.drop_index("ix_crm_deal_stage_history_deal_id_entered_at", table_name="deal_stage_history", schema="crm")
    op.drop_index("ix_crm_deal_stage_history_id", table_name="deal_stage_history", schema="crm")
    op.drop_table("deal_stage_history", schema="crm")
