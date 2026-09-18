"""Initial Abutron production platform schema.

Revision ID: 0001_platform
Revises:
Create Date: 2026-09-18
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0001_platform"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "customers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "role",
            sa.Enum("CUSTOMER", "SUPPORT", "ADMIN", name="role", native_enum=False),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("broker_referral_verified", sa.Boolean(), nullable=False),
        sa.Column("broker_referral_slug", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_customers_email", "customers", ["email"], unique=True)

    op.create_table(
        "brokers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("display_name", sa.String(length=160), nullable=False),
        sa.Column("adapter_key", sa.String(length=80), nullable=False),
        sa.Column("api_base_url", sa.String(length=500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_brokers_slug", "brokers", ["slug"], unique=True)

    op.create_table(
        "billing_plans",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("display_name", sa.String(length=160), nullable=False),
        sa.Column(
            "product",
            sa.Enum(
                "INELIGIBLE",
                "FLIPPER",
                "SCALPER",
                "MASTER",
                name="bottier",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("price_minor", sa.Integer(), nullable=False),
        sa.Column("broker_discount_percent", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_billing_plans_code", "billing_plans", ["code"], unique=True)
    op.create_index("ix_billing_plans_product", "billing_plans", ["product"], unique=False)

    op.create_table(
        "trading_accounts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("broker_id", sa.Uuid(), nullable=False),
        sa.Column("broker_login", sa.String(length=120), nullable=False),
        sa.Column("server_name", sa.String(length=160), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("equity_usd", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column(
            "bot_tier",
            sa.Enum(
                "INELIGIBLE",
                "FLIPPER",
                "SCALPER",
                "MASTER",
                name="bottier",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("route_reason", sa.String(length=255), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING",
                "ACTIVE",
                "PAUSED",
                "DISABLED",
                name="accountstatus",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["broker_id"], ["brokers.id"]),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_trading_accounts_broker_id", "trading_accounts", ["broker_id"])
    op.create_index("ix_trading_accounts_customer_id", "trading_accounts", ["customer_id"])
    op.create_index(
        "ix_trading_accounts_customer_status",
        "trading_accounts",
        ["customer_id", "status"],
    )
    op.create_index(
        "ix_trading_accounts_broker_login",
        "trading_accounts",
        ["broker_id", "broker_login"],
        unique=True,
    )

    op.create_table(
        "licenses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("trading_account_id", sa.Uuid(), nullable=False),
        sa.Column(
            "product",
            sa.Enum(
                "INELIGIBLE",
                "FLIPPER",
                "SCALPER",
                "MASTER",
                name="bottier",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING",
                "ACTIVE",
                "SUSPENDED",
                "EXPIRED",
                "REVOKED",
                name="licensestatus",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("source", sa.String(length=80), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["trading_account_id"],
            ["trading_accounts.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_licenses_customer_id", "licenses", ["customer_id"])
    op.create_index(
        "ix_licenses_trading_account_id",
        "licenses",
        ["trading_account_id"],
        unique=True,
    )

    op.create_table(
        "devices",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column(
            "platform",
            sa.Enum("ANDROID", "IOS", name="deviceplatform", native_enum=False),
            nullable=False,
        ),
        sa.Column("device_id", sa.String(length=255), nullable=False),
        sa.Column("push_token", sa.Text(), nullable=True),
        sa.Column("app_version", sa.String(length=40), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_devices_customer_id", "devices", ["customer_id"])
    op.create_index(
        "ix_devices_customer_platform",
        "devices",
        ["customer_id", "platform"],
    )
    op.create_index("ix_devices_device_id", "devices", ["device_id"], unique=True)

    op.create_table(
        "notifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "QUEUED",
                "SENT",
                "FAILED",
                name="notificationstatus",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("provider_message_id", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notifications_customer_id", "notifications", ["customer_id"])

    op.create_table(
        "audit_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("actor_customer_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("entity_id", sa.String(length=120), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["actor_customer_id"],
            ["customers.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_events_action", "audit_events", ["action"])
    op.create_index("ix_audit_events_entity_type", "audit_events", ["entity_type"])

    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("license_id", sa.Uuid(), nullable=False),
        sa.Column("plan_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING",
                "ACTIVE",
                "PAST_DUE",
                "CANCELLED",
                "EXPIRED",
                name="subscriptionstatus",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("provider_reference", sa.String(length=255), nullable=True),
        sa.Column("amount_minor", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("discount_percent", sa.Integer(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("renews_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["license_id"], ["licenses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plan_id"], ["billing_plans.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_subscriptions_customer_id", "subscriptions", ["customer_id"])
    op.create_index(
        "ix_subscriptions_customer_status",
        "subscriptions",
        ["customer_id", "status"],
    )
    op.create_index("ix_subscriptions_license_id", "subscriptions", ["license_id"])
    op.create_index(
        "ix_subscriptions_license_status",
        "subscriptions",
        ["license_id", "status"],
    )
    op.create_index("ix_subscriptions_plan_id", "subscriptions", ["plan_id"])

    op.create_table(
        "payments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("subscription_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("provider_event_id", sa.String(length=255), nullable=False),
        sa.Column("amount_minor", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING",
                "PAID",
                "FAILED",
                "REFUNDED",
                name="paymentstatus",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("raw_event", sa.JSON(), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["subscription_id"],
            ["subscriptions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_payments_provider_event_id",
        "payments",
        ["provider_event_id"],
        unique=True,
    )
    op.create_index("ix_payments_subscription_id", "payments", ["subscription_id"])

    op.create_table(
        "notification_attempts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("notification_id", sa.Uuid(), nullable=False),
        sa.Column("device_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING",
                "SENT",
                "FAILED",
                name="pushattemptstatus",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("provider_message_id", sa.String(length=255), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["notification_id"],
            ["notifications.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_notification_attempts_device_id",
        "notification_attempts",
        ["device_id"],
    )
    op.create_index(
        "ix_notification_attempts_notification_id",
        "notification_attempts",
        ["notification_id"],
    )

    op.create_table(
        "outbox_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=120), nullable=False),
        sa.Column("aggregate_type", sa.String(length=80), nullable=False),
        sa.Column("aggregate_id", sa.String(length=120), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING",
                "PROCESSING",
                "SENT",
                "FAILED",
                name="outboxstatus",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_outbox_events_event_type", "outbox_events", ["event_type"])
    op.create_index(
        "ix_outbox_events_idempotency_key",
        "outbox_events",
        ["idempotency_key"],
        unique=True,
    )
    op.create_index(
        "ix_outbox_status_created",
        "outbox_events",
        ["status", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_outbox_status_created", table_name="outbox_events")
    op.drop_index("ix_outbox_events_idempotency_key", table_name="outbox_events")
    op.drop_index("ix_outbox_events_event_type", table_name="outbox_events")
    op.drop_table("outbox_events")

    op.drop_index(
        "ix_notification_attempts_notification_id",
        table_name="notification_attempts",
    )
    op.drop_index(
        "ix_notification_attempts_device_id",
        table_name="notification_attempts",
    )
    op.drop_table("notification_attempts")

    op.drop_index("ix_payments_subscription_id", table_name="payments")
    op.drop_index("ix_payments_provider_event_id", table_name="payments")
    op.drop_table("payments")

    op.drop_index("ix_subscriptions_plan_id", table_name="subscriptions")
    op.drop_index("ix_subscriptions_license_status", table_name="subscriptions")
    op.drop_index("ix_subscriptions_license_id", table_name="subscriptions")
    op.drop_index("ix_subscriptions_customer_status", table_name="subscriptions")
    op.drop_index("ix_subscriptions_customer_id", table_name="subscriptions")
    op.drop_table("subscriptions")

    op.drop_index("ix_audit_events_entity_type", table_name="audit_events")
    op.drop_index("ix_audit_events_action", table_name="audit_events")
    op.drop_table("audit_events")

    op.drop_index("ix_notifications_customer_id", table_name="notifications")
    op.drop_table("notifications")

    op.drop_index("ix_devices_device_id", table_name="devices")
    op.drop_index("ix_devices_customer_platform", table_name="devices")
    op.drop_index("ix_devices_customer_id", table_name="devices")
    op.drop_table("devices")

    op.drop_index("ix_licenses_trading_account_id", table_name="licenses")
    op.drop_index("ix_licenses_customer_id", table_name="licenses")
    op.drop_table("licenses")

    op.drop_index("ix_trading_accounts_broker_login", table_name="trading_accounts")
    op.drop_index("ix_trading_accounts_customer_status", table_name="trading_accounts")
    op.drop_index("ix_trading_accounts_customer_id", table_name="trading_accounts")
    op.drop_index("ix_trading_accounts_broker_id", table_name="trading_accounts")
    op.drop_table("trading_accounts")

    op.drop_index("ix_billing_plans_product", table_name="billing_plans")
    op.drop_index("ix_billing_plans_code", table_name="billing_plans")
    op.drop_table("billing_plans")

    op.drop_index("ix_brokers_slug", table_name="brokers")
    op.drop_table("brokers")

    op.drop_index("ix_customers_email", table_name="customers")
    op.drop_table("customers")
