"""Начальная схема: crm (данные) и hub (лента событий и биения фоновых задач).

Revision ID: 0001_init
Revises:
Create Date: 2026-10-27
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None

TS = sa.DateTime(timezone=True)
NOW = sa.text("now()")


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS crm")
    op.execute("CREATE SCHEMA IF NOT EXISTS hub")

    op.create_table(
        "id_counters",
        sa.Column("key", sa.Text, primary_key=True),
        sa.Column("nomer", sa.BigInteger, nullable=False),
        schema="crm")

    op.create_table(
        "users",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("email", sa.String, nullable=False, unique=True),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("password_hash", sa.String, nullable=False),
        sa.Column("role", sa.String, nullable=False, server_default="owner"),
        sa.Column("created_at", TS, nullable=False, server_default=NOW),
        schema="crm")

    op.create_table(
        "api_keys",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("key_hash", sa.String, nullable=False, unique=True),
        sa.Column("prefix", sa.String, nullable=False),
        sa.Column("role", sa.String, nullable=False, server_default="agent"),
        sa.Column("revoked", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_at", TS, nullable=False, server_default=NOW),
        sa.Column("last_used_at", TS),
        schema="crm")

    op.create_table(
        "projects",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("folder", sa.String),
        sa.Column("status", sa.String, nullable=False, server_default="active"),
        sa.Column("roadmap_text", sa.Text, nullable=False, server_default=""),
        sa.Column("progress", sa.Integer, nullable=False, server_default="0"),
        sa.Column("updated_at", TS, nullable=False, server_default=NOW),
        schema="crm")

    op.create_table(
        "stages",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("project_id", sa.String, sa.ForeignKey("crm.projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("n", sa.Integer, nullable=False),
        sa.Column("title", sa.String, nullable=False),
        sa.Column("marker", sa.String),
        sa.Column("status", sa.String, nullable=False, server_default="todo"),
        sa.Column("frozen", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("closed_at", TS),
        schema="crm")
    op.create_index("ix_stages_project", "stages", ["project_id"], schema="crm")

    op.create_table(
        "journal",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("project_id", sa.String, sa.ForeignKey("crm.projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String, nullable=False, server_default="note"),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("files", JSONB, nullable=False, server_default="[]"),
        sa.Column("author", sa.String),
        sa.Column("created_at", TS, nullable=False, server_default=NOW),
        schema="crm")
    op.create_index("ix_journal_project", "journal", ["project_id", "created_at"], schema="crm")

    op.create_table(
        "tasks",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("title", sa.String, nullable=False),
        sa.Column("notes", sa.Text, nullable=False, server_default=""),
        sa.Column("project_id", sa.String, sa.ForeignKey("crm.projects.id", ondelete="SET NULL")),
        sa.Column("plan_date", sa.Date),
        sa.Column("due", sa.Date),
        sa.Column("priority", sa.Integer, nullable=False, server_default="0"),
        sa.Column("status", sa.String, nullable=False, server_default="open"),
        sa.Column("created_at", TS, nullable=False, server_default=NOW),
        sa.Column("done_at", TS),
        schema="crm")
    op.create_index("ix_tasks_open", "tasks", ["status", "plan_date"], schema="crm")
    op.create_index("ix_tasks_project", "tasks", ["project_id"], schema="crm")
    op.execute("CREATE INDEX ix_tasks_fts ON crm.tasks USING gin "
               "(to_tsvector('russian', title || ' ' || coalesce(notes, '')))")

    op.create_table(
        "notes",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("title", sa.String, nullable=False),
        sa.Column("body", sa.Text, nullable=False, server_default=""),
        sa.Column("tags", JSONB, nullable=False, server_default="[]"),
        sa.Column("pinned", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("updated_at", TS, nullable=False, server_default=NOW),
        schema="crm")
    op.execute("CREATE INDEX ix_notes_fts ON crm.notes USING gin (to_tsvector('russian', title || ' ' || body))")

    op.create_table(
        "events",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("title", sa.String, nullable=False),
        sa.Column("starts_at", TS, nullable=False),
        sa.Column("ends_at", TS),
        sa.Column("location", sa.String),
        sa.Column("kind", sa.String, nullable=False, server_default="event"),
        schema="crm")
    op.create_index("ix_events_starts", "events", ["starts_at"], schema="crm")

    op.create_table(
        "feed",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("source", sa.String, nullable=False),
        sa.Column("kind", sa.String, nullable=False, server_default="info"),
        sa.Column("level", sa.String, nullable=False, server_default="info"),
        sa.Column("title", sa.String, nullable=False),
        sa.Column("detail", sa.Text),
        sa.Column("external_id", sa.String),
        sa.Column("payload", JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", TS, nullable=False, server_default=NOW),
        schema="hub")
    op.create_index("ix_feed_created", "feed", ["created_at"], schema="hub")
    op.create_index("ux_feed_external", "feed", ["source", "external_id"], unique=True, schema="hub",
                    postgresql_where=sa.text("external_id IS NOT NULL"))

    op.create_table(
        "beats",
        sa.Column("source", sa.String, primary_key=True),
        sa.Column("title", sa.String, nullable=False),
        sa.Column("machine", sa.String, nullable=False, server_default="server"),
        sa.Column("expect_every", sa.Integer, nullable=False, server_default="3600"),
        sa.Column("status", sa.String, nullable=False, server_default="ok"),
        sa.Column("note", sa.String),
        sa.Column("fails", sa.Integer, nullable=False, server_default="0"),
        sa.Column("muted_until", TS),
        sa.Column("last_at", TS, nullable=False, server_default=NOW),
        schema="hub")


def downgrade() -> None:
    op.execute("DROP SCHEMA hub CASCADE")
    for t in ("events", "notes", "tasks", "journal", "stages", "projects", "api_keys", "users", "id_counters"):
        op.drop_table(t, schema="crm")
