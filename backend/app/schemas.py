from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import AccountStatus, BotTier, DevicePlatform, LicenseStatus, Role


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)


class CustomerPublic(ORMModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    phone: str | None
    role: Role
    is_active: bool
    created_at: datetime


class BrokerPublic(ORMModel):
    id: uuid.UUID
    slug: str
    display_name: str
    is_active: bool


class TradingAccountPublic(ORMModel):
    id: uuid.UUID
    broker_login: str
    server_name: str | None
    currency: str
    equity_usd: Decimal
    bot_tier: BotTier
    route_reason: str
    status: AccountStatus
    last_synced_at: datetime | None


class LicensePublic(ORMModel):
    id: uuid.UUID
    trading_account_id: uuid.UUID
    product: BotTier
    status: LicenseStatus
    starts_at: datetime | None
    expires_at: datetime | None


class TradingAccountCreate(BaseModel):
    broker_id: uuid.UUID
    broker_login: str = Field(min_length=1, max_length=120)
    server_name: str | None = Field(default=None, max_length=160)


class EquitySyncRequest(BaseModel):
    equity_usd: Decimal = Field(ge=Decimal("0"))
    account_status: AccountStatus = AccountStatus.ACTIVE


class EquityDecisionPublic(BaseModel):
    eligible: bool
    tier: BotTier
    equity_usd: Decimal
    reason: str


class DeviceRegisterRequest(BaseModel):
    platform: DevicePlatform
    device_id: str = Field(min_length=4, max_length=255)
    push_token: str | None = Field(default=None, max_length=4096)
    app_version: str | None = Field(default=None, max_length=40)


class DevicePublic(ORMModel):
    id: uuid.UUID
    platform: DevicePlatform
    device_id: str
    app_version: str | None
    is_active: bool
    last_seen_at: datetime


class MobileBootstrapResponse(BaseModel):
    customer: CustomerPublic
    accounts: list[TradingAccountPublic]
    licenses: list[LicensePublic]
    feature_flags: dict[str, bool]


class AdminDashboardResponse(BaseModel):
    customers: int
    active_accounts: int
    active_licenses: int
    registered_devices: int
    queued_notifications: int
