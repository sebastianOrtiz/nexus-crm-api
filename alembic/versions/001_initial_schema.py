"""Initial CRM schema

Revision ID: 001
Revises:
Create Date: 2026-03-24 00:00:00

Creates the ``crm`` schema and all tables for the NexusCRM application.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create the crm schema
    op.execute("CREATE SCHEMA IF NOT EXISTS crm")

    # organizations
    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("plan", sa.String(50), nullable=False, server_default="free"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
        schema="crm",
    )
    op.create_index("ix_crm_organizations_id", "organizations", ["id"], schema="crm")
    op.create_index("ix_crm_organizations_slug", "organizations", ["slug"], schema="crm")

    # users
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("role", sa.String(50), nullable=False, server_default="sales_rep"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["crm.organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        schema="crm",
    )
    op.create_index("ix_crm_users_id", "users", ["id"], schema="crm")
    op.create_index("ix_crm_users_email", "users", ["email"], schema="crm")
    op.create_index("ix_crm_users_organization_id", "users", ["organization_id"], schema="crm")

    # companies
    op.create_table(
        "companies",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("domain", sa.String(255), nullable=True),
        sa.Column("industry", sa.String(100), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["crm.organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema="crm",
    )
    op.create_index("ix_crm_companies_id", "companies", ["id"], schema="crm")
    op.create_index("ix_crm_companies_organization_id", "companies", ["organization_id"], schema="crm")

    # pipeline_stages
    op.create_table(
        "pipeline_stages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_won", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_lost", sa.Boolean(), nullable=False, server_default="false"),
        sa.ForeignKeyConstraint(["organization_id"], ["crm.organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema="crm",
    )
    op.create_index("ix_crm_pipeline_stages_id", "pipeline_stages", ["id"], schema="crm")
    op.create_index("ix_crm_pipeline_stages_organization_id", "pipeline_stages", ["organization_id"], schema="crm")

    # contacts
    op.create_table(
        "contacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("position", sa.String(150), nullable=True),
        sa.Column("source", sa.String(50), nullable=True, server_default="other"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("assigned_to_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["crm.organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["crm.companies.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["assigned_to_id"], ["crm.users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        schema="crm",
    )
    op.create_index("ix_crm_contacts_id", "contacts", ["id"], schema="crm")
    op.create_index("ix_crm_contacts_organization_id", "contacts", ["organization_id"], schema="crm")
    op.create_index("ix_crm_contacts_company_id", "contacts", ["company_id"], schema="crm")
    op.create_index("ix_crm_contacts_email", "contacts", ["email"], schema="crm")
    op.create_index("ix_crm_contacts_assigned_to_id", "contacts", ["assigned_to_id"], schema="crm")

    # deals
    op.create_table(
        "deals",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("value", sa.Numeric(14, 2), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("stage_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("contact_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("assigned_to_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("expected_close", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["crm.organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["stage_id"], ["crm.pipeline_stages.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["contact_id"], ["crm.contacts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["company_id"], ["crm.companies.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["assigned_to_id"], ["crm.users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        schema="crm",
    )
    op.create_index("ix_crm_deals_id", "deals", ["id"], schema="crm")
    op.create_index("ix_crm_deals_organization_id", "deals", ["organization_id"], schema="crm")
    op.create_index("ix_crm_deals_stage_id", "deals", ["stage_id"], schema="crm")
    op.create_index("ix_crm_deals_contact_id", "deals", ["contact_id"], schema="crm")
    op.create_index("ix_crm_deals_company_id", "deals", ["company_id"], schema="crm")
    op.create_index("ix_crm_deals_assigned_to_id", "deals", ["assigned_to_id"], schema="crm")

    # activities
    op.create_table(
        "activities",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", sa.String(50), nullable=False, server_default="note"),
        sa.Column("subject", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("contact_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("deal_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["crm.organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["contact_id"], ["crm.contacts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["deal_id"], ["crm.deals.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["crm.users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema="crm",
    )
    op.create_index("ix_crm_activities_id", "activities", ["id"], schema="crm")
    op.create_index("ix_crm_activities_organization_id", "activities", ["organization_id"], schema="crm")
    op.create_index("ix_crm_activities_contact_id", "activities", ["contact_id"], schema="crm")
    op.create_index("ix_crm_activities_deal_id", "activities", ["deal_id"], schema="crm")
    op.create_index("ix_crm_activities_user_id", "activities", ["user_id"], schema="crm")


def downgrade() -> None:
    op.drop_table("activities", schema="crm")
    op.drop_table("deals", schema="crm")
    op.drop_table("contacts", schema="crm")
    op.drop_table("pipeline_stages", schema="crm")
    op.drop_table("companies", schema="crm")
    op.drop_table("users", schema="crm")
    op.drop_table("organizations", schema="crm")
    op.execute("DROP SCHEMA IF EXISTS crm")
