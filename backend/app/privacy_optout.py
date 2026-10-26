"""Proposed opt-out lookup for Abutron identity service.

Review-only component. This does NOT enforce opt-out until authentication
routes and the reviewed SQL migration are integrated. Do not deploy alone.
"""
from __future__ import annotations

import hashlib
import hmac
import os

from fastapi import HTTPException
from sqlalchemy import text

DOMAIN = b"abutron-v7-customer-optout-v1\x00"


def email_fingerprint(email: str, key_hex: str | None = None) -> str:
    secret = os.environ.get("ABUTRON_V7_PRIVACY_OPTOUT_KEY", "") if key_hex is None else key_hex
    if len(secret) != 64:
        raise HTTPException(status_code=503, detail="REGISTRATION_POLICY_UNAVAILABLE")
    try:
        key = bytes.fromhex(secret)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail="REGISTRATION_POLICY_UNAVAILABLE") from exc
    if len(key) != 32 or key == bytes(32):
        raise HTTPException(status_code=503, detail="REGISTRATION_POLICY_UNAVAILABLE")
    normalized_email = email.strip().casefold()
    return hmac.new(key, DOMAIN + normalized_email.encode("utf-8"), hashlib.sha256).hexdigest()


async def is_opted_out(db, email: str) -> bool:
    digest = email_fingerprint(email)
    try:
        found = await db.scalar(
            text("SELECT EXISTS (SELECT 1 FROM public.customer_email_optouts "
                 "WHERE email_hmac = :fingerprint)"),
            {"fingerprint": digest},
        )
    except Exception as exc:
        # If the opt-out registry cannot be read, do not admit a new signup.
        raise HTTPException(status_code=503, detail="REGISTRATION_POLICY_UNAVAILABLE") from exc
    if found is None:
        raise HTTPException(status_code=503, detail="REGISTRATION_POLICY_UNAVAILABLE")
    return found is True


async def reject_opted_out_registration(db, email: str) -> None:
    if await is_opted_out(db, email):
        raise HTTPException(status_code=409, detail="Registration unavailable")
