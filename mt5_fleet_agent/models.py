from __future__ import annotations

import uuid
from decimal import Decimal
from pydantic import BaseModel, Field


class VerifyRequest(BaseModel):
    account_id: uuid.UUID
    login: str = Field(min_length=1, max_length=120)
    server: str = Field(min_length=2, max_length=160)
    password: str = Field(min_length=1, max_length=256)


class VerifyResponse(BaseModel):
    verified: bool
    login: str
    server: str
    currency: str = "USD"
    equity: Decimal = Decimal("0.00")
    company: str = ""
    terminal: str = ""


class StartRequest(VerifyRequest):
    requested_port: int | None = None


class StartResponse(BaseModel):
    started: bool
    session_id: str
    gateway_url: str | None = None
    gateway_port: int | None = None
    terminal_instance: str | None = None
    status: str


class StopResponse(BaseModel):
    stopped: bool
    session_id: str
    status: str
