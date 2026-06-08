"""create booking task, order and audit tables

Revision ID: 20260608_0001
Revises:
Create Date: 2026-06-08
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260608_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "booking_tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_id", sa.String(length=64), nullable=True),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("session_id", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("current_step", sa.String(length=128), nullable=True),
        sa.Column("request_payload", postgresql.JSONB(), nullable=False),
        sa.Column("intent", postgresql.JSONB(), nullable=True),
        sa.Column("missing_fields", postgresql.JSONB(), nullable=False),
        sa.Column("response_payload", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_booking_tasks_task_id", "booking_tasks", ["task_id"])
    op.create_index("ix_booking_tasks_user_id", "booking_tasks", ["user_id"])
    op.create_index("ix_booking_tasks_session_id", "booking_tasks", ["session_id"])
    op.create_index("ix_booking_tasks_status", "booking_tasks", ["status"])

    op.create_table(
        "booking_orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("provider_id", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("price", postgresql.JSONB(), nullable=True),
        sa.Column("slot", postgresql.JSONB(), nullable=True),
        sa.Column("provider", postgresql.JSONB(), nullable=True),
        sa.Column("inventory_lock", postgresql.JSONB(), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_booking_orders_task_id", "booking_orders", ["task_id"])
    op.create_index("ix_booking_orders_user_id", "booking_orders", ["user_id"])
    op.create_index("ix_booking_orders_provider_id", "booking_orders", ["provider_id"])
    op.create_index("ix_booking_orders_status", "booking_orders", ["status"])

    op.create_table(
        "tool_audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_id", sa.String(length=64), nullable=True),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("step", sa.String(length=128), nullable=True),
        sa.Column("tool", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("permissions", postgresql.JSONB(), nullable=False),
        sa.Column("privacy_scopes", postgresql.JSONB(), nullable=False),
        sa.Column("request_payload", postgresql.JSONB(), nullable=True),
        sa.Column("response_payload", postgresql.JSONB(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_tool_audit_logs_task_id", "tool_audit_logs", ["task_id"])
    op.create_index("ix_tool_audit_logs_user_id", "tool_audit_logs", ["user_id"])
    op.create_index("ix_tool_audit_logs_step", "tool_audit_logs", ["step"])
    op.create_index("ix_tool_audit_logs_tool", "tool_audit_logs", ["tool"])
    op.create_index("ix_tool_audit_logs_status", "tool_audit_logs", ["status"])


def downgrade() -> None:
    op.drop_table("tool_audit_logs")
    op.drop_table("booking_orders")
    op.drop_table("booking_tasks")
