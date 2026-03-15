"""Initial schema."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260315_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    run_status = sa.Enum("PENDING", "RUNNING", "FAILED", "COMPLETED", name="runstatus")
    finding_category = sa.Enum("data", "ui", "navigation", "system", name="findingcategory")
    finding_severity = sa.Enum("info", "warning", "error", "critical", name="findingseverity")

    op.create_table(
        "dashboard_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("dashboard_name", sa.String(length=255), nullable=False),
        sa.Column("dashboard_url", sa.Text(), nullable=False),
        sa.Column("platform", sa.String(length=64), nullable=False),
        sa.Column("status", run_status, nullable=False),
        sa.Column("prompt", sa.Text(), nullable=True),
        sa.Column("rules_path", sa.Text(), nullable=False),
        sa.Column("dashboard_config_path", sa.Text(), nullable=True),
        sa.Column("report_dir", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("navigation_tree", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_dashboard_runs_status", "dashboard_runs", ["status"])

    op.create_table(
        "navigation_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("dashboard_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("navigation_events.id", ondelete="CASCADE"), nullable=True),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("depth", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("chart_type", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("page_title", sa.String(length=255), nullable=True),
        sa.Column("target_url", sa.Text(), nullable=True),
        sa.Column("state_hash", sa.String(length=64), nullable=True),
        sa.Column("screenshot_path", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_navigation_events_run_id", "navigation_events", ["run_id"])

    op.create_table(
        "validation_findings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("dashboard_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("navigation_events.id", ondelete="SET NULL"), nullable=True),
        sa.Column("category", finding_category, nullable=False),
        sa.Column("severity", finding_severity, nullable=False),
        sa.Column("code", sa.String(length=128), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("expected", sa.Text(), nullable=True),
        sa.Column("actual", sa.Text(), nullable=True),
        sa.Column("path", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_validation_findings_run_id", "validation_findings", ["run_id"])

    op.create_table(
        "execution_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("dashboard_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("level", sa.String(length=32), nullable=False),
        sa.Column("event", sa.String(length=128), nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_execution_logs_run_id", "execution_logs", ["run_id"])

    op.create_table(
        "artifacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("dashboard_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("navigation_events.id", ondelete="SET NULL"), nullable=True),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_artifacts_run_id", "artifacts", ["run_id"])


def downgrade() -> None:
    op.drop_index("ix_artifacts_run_id", table_name="artifacts")
    op.drop_table("artifacts")
    op.drop_index("ix_execution_logs_run_id", table_name="execution_logs")
    op.drop_table("execution_logs")
    op.drop_index("ix_validation_findings_run_id", table_name="validation_findings")
    op.drop_table("validation_findings")
    op.drop_index("ix_navigation_events_run_id", table_name="navigation_events")
    op.drop_table("navigation_events")
    op.drop_index("ix_dashboard_runs_status", table_name="dashboard_runs")
    op.drop_table("dashboard_runs")

    bind = op.get_bind()
    sa.Enum(name="findingseverity").drop(bind, checkfirst=True)
    sa.Enum(name="findingcategory").drop(bind, checkfirst=True)
    sa.Enum(name="runstatus").drop(bind, checkfirst=True)
