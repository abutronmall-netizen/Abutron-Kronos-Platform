from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class MT5SessionStatus(str, enum.Enum):
    DISCONNECTED = "disconnected"
    VERIFYING = "verifying"
    PROVISIONING = "provisioning"
    RUNNING = "running"
    DEGRADED = "degraded"
    ERROR = "error"


class MT5Credential(Base):
    __tablename__ = "mt5_credentials"
    __table_args__ = (Index("ix_mt5_credentials_account", "trading_account_id", unique=True),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trading_account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("trading_accounts.id", ondelete="CASCADE"), nullable=False)
    encrypted_password: Mapped[str] = mapped_column(Text, nullable=False)
    key_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class MT5Session(Base):
    __tablename__ = "mt5_sessions"
    __table_args__ = (
        Index("ix_mt5_sessions_account", "trading_account_id", unique=True),
        Index("ix_mt5_sessions_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trading_account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("trading_accounts.id", ondelete="CASCADE"), nullable=False)
    agent_session_id: Mapped[str | None] = mapped_column(String(120), unique=True, nullable=True)
    status: Mapped[MT5SessionStatus] = mapped_column(Enum(MT5SessionStatus, native_enum=False), default=MT5SessionStatus.DISCONNECTED)
    broker_login: Mapped[str] = mapped_column(String(120), nullable=False)
    server_name: Mapped[str] = mapped_column(String(160), nullable=False)
    agent_url: Mapped[str] = mapped_column(String(500), nullable=False)
    gateway_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    gateway_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    terminal_instance: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_health_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
