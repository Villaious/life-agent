"""create session checkpoints table

Revision ID: 20260608_0002
Revises: 20260608_0001
Create Date: 2026-06-08
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260608_0002"
down_revision = "20260608_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "session_checkpoints",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("session_id", sa.String(length=128), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "session_id", name="uq_session_checkpoint"),
    )
    op.create_index("ix_session_checkpoints_user_id", "session_checkpoints", ["user_id"])
    op.create_index("ix_session_checkpoints_session_id", "session_checkpoints", ["session_id"])


def downgrade() -> None:
    op.drop_table("session_checkpoints")
