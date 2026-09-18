from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import License, OutboxEvent, OutboxStatus, TradingAccount
from app.services.entitlements import license_allows_execution


async def enqueue_account_assignment(
    db: AsyncSession,
    account: TradingAccount,
    license_record: License | None,
) -> OutboxEvent:
    pending = await db.scalar(
        select(OutboxEvent)
        .where(
            OutboxEvent.event_type == "kronos.account_assignment",
            OutboxEvent.aggregate_id == str(account.id),
            OutboxEvent.status.in_([OutboxStatus.PENDING, OutboxStatus.PROCESSING]),
        )
        .order_by(OutboxEvent.created_at.desc())
    )

    payload = {
        "account_id": str(account.id),
        "broker_login": account.broker_login,
        "bot_tier": account.bot_tier.value,
        "equity_usd": str(account.equity_usd),
        "enabled": license_allows_execution(license_record),
    }

    if pending is not None:
        pending.payload = payload
        pending.status = OutboxStatus.PENDING
        pending.last_error = None
        return pending

    event = OutboxEvent(
        event_type="kronos.account_assignment",
        aggregate_type="trading_account",
        aggregate_id=str(account.id),
        idempotency_key=str(uuid.uuid4()),
        payload=payload,
        status=OutboxStatus.PENDING,
    )
    db.add(event)
    await db.flush()
    return event
