from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import or_, select

from app.db import SessionLocal
from app.models import BotTier, OutboxEvent, OutboxStatus
from app.services.kronos import KronosAssignment, KronosExecutionClient

MAX_ATTEMPTS = 10
BATCH_SIZE = 50


async def process_once() -> int:
    now = datetime.now(UTC)
    async with SessionLocal() as db:
        events = list(
            await db.scalars(
                select(OutboxEvent)
                .where(
                    OutboxEvent.status == OutboxStatus.PENDING,
                    or_(
                        OutboxEvent.next_attempt_at.is_(None),
                        OutboxEvent.next_attempt_at <= now,
                    ),
                )
                .order_by(OutboxEvent.created_at)
                .limit(BATCH_SIZE)
            )
        )

        client = KronosExecutionClient()
        processed = 0

        for event in events:
            event.status = OutboxStatus.PROCESSING
            await db.flush()

            try:
                if event.event_type != "kronos.account_assignment":
                    raise ValueError(f"Unsupported outbox event: {event.event_type}")

                payload = event.payload
                assignment = KronosAssignment(
                    broker_login=payload["broker_login"],
                    tier=BotTier(payload["bot_tier"]),
                    equity_usd=Decimal(payload["equity_usd"]),
                    enabled=bool(payload["enabled"]),
                )
                await client.apply_assignment(assignment)

                event.status = OutboxStatus.SENT
                event.sent_at = datetime.now(UTC)
                event.last_error = None
            except Exception as exc:
                event.attempts += 1
                event.last_error = str(exc)[:2000]
                if event.attempts >= MAX_ATTEMPTS:
                    event.status = OutboxStatus.FAILED
                else:
                    event.status = OutboxStatus.PENDING
                    delay = min(3600, 2 ** min(event.attempts, 10) * 15)
                    event.next_attempt_at = datetime.now(UTC) + timedelta(seconds=delay)

            processed += 1

        await db.commit()
        return processed


async def run_forever() -> None:
    while True:
        processed = await process_once()
        await asyncio.sleep(2 if processed else 5)


if __name__ == "__main__":
    asyncio.run(run_forever())
