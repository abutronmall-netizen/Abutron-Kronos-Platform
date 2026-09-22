from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, SecretStr

from app.models import BotTier
from app.mt5_fleet.models import MT5SessionStatus


class MT5ConnectRequest(BaseModel):
    trading_account_id: uuid.UUID
    login: str = Field(min_length=1, max_length=120)
    server: str = Field(min_length=2, max_length=160)
    password: SecretStr
    start_session: bool = True


class MT5VerifyResult(BaseModel):
    verified: bool
    login: str
    server: str
    currency: str = "USD"
    equity: Decimal = Decimal("0.00")
    company: str = ""
    terminal: str = ""


class MT5SessionPublic(BaseModel):
    trading_account_id: uuid.UUID
    status: MT5SessionStatus
    login: str
    server: str
    last_error: str | None = None
    last_health_at: datetime | None = None


class MT5AdminSessionPublic(MT5SessionPublic):
    gateway_url: str | None = None
    gateway_port: int | None = None
    terminal_instance: str | None = None


class MT5ConnectResponse(BaseModel):
    connected: bool
    broker: str
    platform: str = "MetaTrader 5"
    login: str
    server: str
    currency: str
    equity: Decimal
    tier: BotTier
    route_reason: str
    session: MT5SessionPublic


class AgentVerifyRequest(BaseModel):
    account_id: uuid.UUID
    login: str
    server: str
    password: str


class AgentStartRequest(AgentVerifyRequest):
    requested_port: int | None = None


class AgentStartResponse(BaseModel):
    started: bool
    session_id: str
    gateway_url: str | None = None
    gateway_port: int | None = None
    terminal_instance: str | None = None
    status: str


class AgentStopResponse(BaseModel):
    stopped: bool
    session_id: str
    status: str
