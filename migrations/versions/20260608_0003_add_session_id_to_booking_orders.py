"""add session id to booking orders

Revision ID: 20260608_0003
Revises: 20260608_0002
Create Date: 2026-06-08
"""

from alembic import op
import sqlalchemy as sa

revision = "20260608_0003"
down_revision = "20260608_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("booking_orders", sa.Column("session_id", sa.String(length=128), nullable=True))
    op.create_index("ix_booking_orders_session_id", "booking_orders", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_booking_orders_session_id", table_name="booking_orders")
    op.drop_column("booking_orders", "session_id")
