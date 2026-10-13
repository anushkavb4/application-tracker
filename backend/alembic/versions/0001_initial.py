"""create initial persistence schema

Revision ID: 0001_initial
Revises:
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "raw_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("client_event_id", sa.String(128), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("page_title", sa.Text(), nullable=False),
        sa.Column("referrer", sa.Text()),
        sa.Column("trigger_type", sa.String(32), nullable=False),
        sa.Column("tab_id", sa.Integer()),
        sa.Column("nav_chain_id", postgresql.UUID(as_uuid=True)),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.UniqueConstraint("client_event_id", name="uq_raw_events_client_event_id"),
    )
    op.create_table(
        "companies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("normalized_key", sa.String(255), nullable=False),
        sa.Column("aliases", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.UniqueConstraint("normalized_key", name="uq_companies_normalized_key"),
    )
    op.create_table(
        "applications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("dedup_key", sa.String(512), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True)),
        sa.Column("company_name", sa.String(255)),
        sa.Column("role", sa.String(512)),
        sa.Column("ats", sa.String(128)),
        sa.Column("external_id", sa.String(255)),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="viewed"),
        sa.Column("status_source", sa.String(32), nullable=False, server_default="automatic"),
        sa.Column("confidence", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("applied_at", sa.DateTime(timezone=True)),
        sa.Column("notes", sa.Text()),
        sa.UniqueConstraint("dedup_key", name="uq_applications_dedup_key"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], name="fk_applications_company_id"),
    )
    op.create_table(
        "application_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("raw_event_id", postgresql.UUID(as_uuid=True)),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("confidence", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("source", sa.String(32), nullable=False, server_default="automatic"),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"], name="fk_application_events_application_id"),
        sa.ForeignKeyConstraint(["raw_event_id"], ["raw_events.id"], name="fk_application_events_raw_event_id"),
    )
    op.create_table(
        "url_patterns",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ats", sa.String(128), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False, server_default="job_posting"),
        sa.Column("url_regex", sa.Text(), nullable=False),
        sa.Column("title_regex", sa.Text()),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "manual_overrides",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("dedup_key", sa.String(512), nullable=False),
        sa.Column("status", sa.String(32)),
        sa.Column("company_name", sa.String(255)),
        sa.Column("role", sa.String(512)),
        sa.Column("notes", sa.Text()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("dedup_key", name="uq_manual_overrides_dedup_key"),
    )


def downgrade() -> None:
    op.drop_table("manual_overrides")
    op.drop_table("url_patterns")
    op.drop_table("application_events")
    op.drop_table("applications")
    op.drop_table("companies")
    op.drop_table("raw_events")
