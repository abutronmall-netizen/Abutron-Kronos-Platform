from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import Customer, RefreshSession

settings = get_settings()


class RefreshTokenError(ValueError):
    pass


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def issue_refresh_session(
    db: AsyncSession,
    *,
    customer_id,
    device_id: str | None = None,
) -> tuple[RefreshSession, str, int]:
    token = secrets.token_urlsafe(48)
    lifetime = timedelta(days=settings.refresh_token_days)
    now = datetime.now(UTC)

    session = RefreshSession(
        customer_id=customer_id,
        token_hash=_hash_token(token),
        device_id=device_id,
        expires_at=now + lifetime,
    )
    db.add(session)
    await db.flush()
    return session, token, int(lifetime.total_seconds())


async def rotate_refresh_session(
    db: AsyncSession,
    *,
    token: str,
) -> tuple[Customer, RefreshSession, str, int]:
    now = datetime.now(UTC)
    token_hash = _hash_token(token)

    session = await db.scalar(
        select(RefreshSession)
        .where(RefreshSession.token_hash == token_hash)
        .with_for_update()
    )
    if session is None or session.revoked_at is not None or session.expires_at <= now:
        raise RefreshTokenError("Invalid or expired refresh token")

    customer = await db.get(Customer, session.customer_id)
    if customer is None or not customer.is_active:
        raise RefreshTokenError("Customer account is unavailable")

    session.revoked_at = now
    session.last_used_at = now

    new_session, new_token, expires_in = await issue_refresh_session(
        db,
        customer_id=customer.id,
        device_id=session.device_id,
    )
    return customer, new_session, new_token, expires_in


async def revoke_refresh_session(db: AsyncSession, *, token: str) -> bool:
    token_hash = _hash_token(token)
    session = await db.scalar(
        select(RefreshSession)
        .where(RefreshSession.token_hash == token_hash)
        .with_for_update()
    )
    if session is None:
        return False
    if session.revoked_at is None:
        session.revoked_at = datetime.now(UTC)
    return True
