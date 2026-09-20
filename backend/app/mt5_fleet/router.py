from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import Customer
from app.mt5_fleet.models import MT5Session
from app.mt5_fleet.schemas import MT5AdminSessionPublic, MT5ConnectRequest, MT5ConnectResponse, MT5SessionPublic
from app.mt5_fleet.service import connect_mt5_account, disconnect_mt5_account, owned_ic_markets_account, reconnect_mt5_account
from app.security import get_current_customer, require_admin

router = APIRouter(prefix="/api/v1", tags=["mt5-fleet"])


def public_session(session: MT5Session) -> MT5SessionPublic:
    return MT5SessionPublic(
        trading_account_id=session.trading_account_id,
        status=session.status,
        login=session.broker_login,
        server=session.server_name,
        last_error=session.last_error,
        last_health_at=session.last_health_at,
    )


@router.post("/mt5/connect", response_model=MT5ConnectResponse)
async def connect_mt5(request: MT5ConnectRequest, customer: Customer = Depends(get_current_customer), db: AsyncSession = Depends(get_db)) -> MT5ConnectResponse:
    return await connect_mt5_account(db, customer, request)


@router.get("/mt5/accounts/{account_id}/status", response_model=MT5SessionPublic)
async def mt5_status(account_id: uuid.UUID, customer: Customer = Depends(get_current_customer), db: AsyncSession = Depends(get_db)) -> MT5SessionPublic:
    account, _ = await owned_ic_markets_account(db, customer, account_id)
    session = await db.scalar(select(MT5Session).where(MT5Session.trading_account_id == account.id))
    if session is None:
        raise HTTPException(status_code=404, detail="MT5 session not found")
    return public_session(session)


@router.post("/mt5/accounts/{account_id}/reconnect", response_model=MT5SessionPublic)
async def mt5_reconnect(account_id: uuid.UUID, customer: Customer = Depends(get_current_customer), db: AsyncSession = Depends(get_db)) -> MT5SessionPublic:
    return public_session(await reconnect_mt5_account(db, customer, account_id))


@router.delete("/mt5/accounts/{account_id}/connection", response_model=MT5SessionPublic)
async def mt5_disconnect(account_id: uuid.UUID, customer: Customer = Depends(get_current_customer), db: AsyncSession = Depends(get_db)) -> MT5SessionPublic:
    return public_session(await disconnect_mt5_account(db, customer, account_id))


@router.get("/admin/mt5/sessions", response_model=list[MT5AdminSessionPublic])
async def admin_mt5_sessions(_: Customer = Depends(require_admin), db: AsyncSession = Depends(get_db)) -> list[MT5AdminSessionPublic]:
    sessions = await db.scalars(select(MT5Session).order_by(MT5Session.updated_at.desc()).limit(1000))
    return [
        MT5AdminSessionPublic(
            trading_account_id=item.trading_account_id,
            status=item.status,
            login=item.broker_login,
            server=item.server_name,
            gateway_url=item.gateway_url,
            gateway_port=item.gateway_port,
            terminal_instance=item.terminal_instance,
            last_error=item.last_error,
            last_health_at=item.last_health_at,
        )
        for item in sessions
    ]
