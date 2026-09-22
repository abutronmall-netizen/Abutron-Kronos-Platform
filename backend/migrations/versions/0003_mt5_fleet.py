"""Add encrypted MT5 credential vault and session registry.

Revision ID: 0003_mt5_fleet
Revises: 0002_notification_read_state
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003_mt5_fleet"
down_revision = "0002_notification_read_state"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mt5_credentials",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trading_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("encrypted_password", sa.Text(), nullable=False),
        sa.Column("key_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["trading_account_id"], ["trading_accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_mt5_credentials_account", "mt5_credentials", ["trading_account_id"], unique=True)
    op.create_table(
        "mt5_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trading_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_session_id", sa.String(length=120), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("broker_login", sa.String(length=120), nullable=False),
        sa.Column("server_name", sa.String(length=160), nullable=False),
        sa.Column("agent_url", sa.String(length=500), nullable=False),
        sa.Column("gateway_url", sa.String(length=500), nullable=True),
        sa.Column("gateway_port", sa.Integer(), nullable=True),
        sa.Column("terminal_instance", sa.String(length=255), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("last_health_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["trading_account_id"], ["trading_accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("agent_session_id"),
    )
    op.create_index("ix_mt5_sessions_account", "mt5_sessions", ["trading_account_id"], unique=True)
    op.create_index("ix_mt5_sessions_status", "mt5_sessions", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_mt5_sessions_status", table_name="mt5_sessions")
    op.drop_index("ix_mt5_sessions_account", table_name="mt5_sessions")
    op.drop_table("mt5_sessions")
    op.drop_index("ix_mt5_credentials_account", table_name="mt5_credentials")
    op.drop_table("mt5_credentials")
