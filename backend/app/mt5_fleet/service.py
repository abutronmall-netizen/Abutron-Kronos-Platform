from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import AccountStatus, AuditEvent, Broker, Customer, TradingAccount
from app.mt5_fleet.client import MT5FleetClient, MT5FleetClientError
from app.mt5_fleet.crypto import CredentialVault
from app.mt5_fleet.models import MT5Credential, MT5Session, MT5SessionStatus
from app.mt5_fleet.schemas import (
    AgentStartRequest,
    MT5ConnectRequest,
    MT5ConnectResponse,
    MT5SessionPublic,
)
from app.services.equity_router import select_bot

settings = get_settings()


def _ensure_fleet_enabled() -> None:
    if not settings.mt5_fleet_enabled:
        raise HTTPException(status_code=503, detail="MT5 fleet is disabled")


def _allowed_broker_slugs() -> set[str]:
    return {item.strip().lower() for item in settings.mt5_allowed_broker_slugs if item.strip()}


async def owned_ic_markets_account(db: AsyncSession, customer: Customer, account_id) -> tuple[TradingAccount, Broker]:
    row = await db.execute(
        select(TradingAccount, Broker)
        .join(Broker, Broker.id == TradingAccount.broker_id)
        .where(TradingAccount.id == account_id, TradingAccount.customer_id == customer.id)
    )
    result = row.first()
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trading account not found")
    account, broker = result
    if broker.slug.lower() not in _allowed_broker_slugs():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only approved IC Markets MT5 accounts are supported")
    return account, broker


async def connect_mt5_account(db: AsyncSession, customer: Customer, request: MT5ConnectRequest) -> MT5ConnectResponse:
    _ensure_fleet_enabled()
    account, broker = await owned_ic_markets_account(db, customer, request.trading_account_id)
    login = request.login.strip()
    server = request.server.strip()
    if login != account.broker_login:
        raise HTTPException(status_code=409, detail="MT5 login does not match trading account")
    if account.server_name and account.server_name.strip().casefold() != server.casefold():
        raise HTTPException(status_code=409, detail="MT5 server does not match trading account")

    fleet = MT5FleetClient(settings.mt5_fleet_agent_url, settings.mt5_fleet_agent_token)
    agent_request = AgentStartRequest(account_id=account.id, login=login, server=server, password=request.password.get_secret_value())
    try:
        verified = await fleet.verify(agent_request)
    except MT5FleetClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    if not verified.verified:
        raise HTTPException(status_code=401, detail="MT5 credentials were rejected")
    if verified.login != login or verified.server.casefold() != server.casefold():
        raise HTTPException(status_code=409, detail="MT5 identity mismatch after verification")

    vault = CredentialVault(settings.mt5_credential_key, settings.mt5_credential_key_version)
    encrypted = vault.encrypt(request.password.get_secret_value())
    credential = await db.scalar(select(MT5Credential).where(MT5Credential.trading_account_id == account.id))
    if credential is None:
        credential = MT5Credential(trading_account_id=account.id, encrypted_password=encrypted)
        db.add(credential)
    credential.encrypted_password = encrypted
    credential.key_version = settings.mt5_credential_key_version

    session = await db.scalar(select(MT5Session).where(MT5Session.trading_account_id == account.id))
    if session is None:
        session = MT5Session(trading_account_id=account.id, broker_login=login, server_name=server, agent_url=settings.mt5_fleet_agent_url, status=MT5SessionStatus.VERIFYING)
        db.add(session)
    else:
        session.broker_login = login
        session.server_name = server
        session.agent_url = settings.mt5_fleet_agent_url
        session.status = MT5SessionStatus.VERIFYING
        session.last_error = None

    account.server_name = server
    account.currency = verified.currency.upper()[:3]
    account.equity_usd = Decimal(str(verified.equity)).quantize(Decimal("0.01"))
    decision = select_bot(account.equity_usd)
    account.bot_tier = decision.tier
    account.route_reason = decision.reason
    account.status = AccountStatus.ACTIVE if decision.eligible else AccountStatus.PENDING
    account.last_synced_at = datetime.now(UTC)

    if request.start_session:
        try:
            started = await fleet.start(agent_request)
            session.agent_session_id = started.session_id
            session.gateway_url = started.gateway_url
            session.gateway_port = started.gateway_port
            session.terminal_instance = started.terminal_instance
            session.status = MT5SessionStatus.RUNNING if started.started else MT5SessionStatus.PROVISIONING
            session.last_health_at = datetime.now(UTC)
        except MT5FleetClientError as exc:
            session.status = MT5SessionStatus.ERROR
            session.last_error = str(exc)
    else:
        if session.agent_session_id:
            try:
                await fleet.stop(
                    session.agent_session_id
                )
            except MT5FleetClientError as exc:
                session.status = MT5SessionStatus.ERROR
                session.last_error = str(exc)
                await db.commit()

                raise HTTPException(
                    status_code=502,
                    detail=str(exc),
                ) from exc

        session.status = MT5SessionStatus.DISCONNECTED
        session.agent_session_id = None
        session.gateway_url = None
        session.gateway_port = None
        session.terminal_instance = None
        session.last_error = None
        session.last_health_at = datetime.now(UTC)

    db.add(AuditEvent(actor_customer_id=customer.id, action="mt5_account_connected", entity_type="trading_account", entity_id=str(account.id), payload={"broker": broker.slug, "login": login, "server": server, "tier": decision.tier.value, "route_reason": decision.reason}))
    await db.commit()
    await db.refresh(session)
    return MT5ConnectResponse(
        connected=session.status == MT5SessionStatus.RUNNING,
        broker=broker.display_name,
        login=login,
        server=server,
        currency=account.currency,
        equity=account.equity_usd,
        tier=account.bot_tier,
        route_reason=account.route_reason,
        session=MT5SessionPublic(trading_account_id=account.id, status=session.status, login=login, server=server, last_error=session.last_error, last_health_at=session.last_health_at),
    )


async def reconnect_mt5_account(db: AsyncSession, customer: Customer, account_id) -> MT5Session:
    _ensure_fleet_enabled()
    account, _ = await owned_ic_markets_account(db, customer, account_id)
    credential = await db.scalar(select(MT5Credential).where(MT5Credential.trading_account_id == account.id))
    if credential is None:
        raise HTTPException(status_code=409, detail="MT5 credentials have not been stored")
    if not account.server_name:
        raise HTTPException(status_code=409, detail="MT5 server is not configured")
    vault = CredentialVault(settings.mt5_credential_key, credential.key_version)
    password = vault.decrypt(credential.encrypted_password)
    fleet = MT5FleetClient(settings.mt5_fleet_agent_url, settings.mt5_fleet_agent_token)
    payload = AgentStartRequest(account_id=account.id, login=account.broker_login, server=account.server_name, password=password)
    try:
        started = await fleet.start(payload)
    except MT5FleetClientError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc
    finally:
        password = ""

    session = await db.scalar(select(MT5Session).where(MT5Session.trading_account_id == account.id))
    if session is None:
        session = MT5Session(trading_account_id=account.id, broker_login=account.broker_login, server_name=account.server_name, agent_url=settings.mt5_fleet_agent_url)
        db.add(session)
    session.agent_session_id = started.session_id
    session.gateway_url = started.gateway_url
    session.gateway_port = started.gateway_port
    session.terminal_instance = started.terminal_instance
    session.status = MT5SessionStatus.RUNNING if started.started else MT5SessionStatus.PROVISIONING
    session.last_error = None
    session.last_health_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(session)
    return session


async def disconnect_mt5_account(db: AsyncSession, customer: Customer, account_id) -> MT5Session:
    account, _ = await owned_ic_markets_account(db, customer, account_id)
    session = await db.scalar(select(MT5Session).where(MT5Session.trading_account_id == account.id))
    if session is None:
        raise HTTPException(status_code=404, detail="MT5 session not found")
    if session.agent_session_id:
        fleet = MT5FleetClient(session.agent_url, settings.mt5_fleet_agent_token)
        try:
            await fleet.stop(session.agent_session_id)
        except MT5FleetClientError as exc:
            session.last_error = str(exc)
            session.status = MT5SessionStatus.ERROR
            await db.commit()
            raise HTTPException(status_code=502, detail=str(exc)) from exc
    session.status = MT5SessionStatus.DISCONNECTED
    session.agent_session_id = None
    session.gateway_url = None
    session.gateway_port = None
    session.terminal_instance = None
    session.last_error = None
    session.last_health_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(session)
    return session
