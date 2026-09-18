from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_db
from app.models import (
    AccountStatus,
    AuditEvent,
    Broker,
    Customer,
    Device,
    License,
    LicenseStatus,
    Notification,
    NotificationStatus,
    Role,
    TradingAccount,
)
from app.schemas import (
    AdminDashboardResponse,
    BrokerCreate,
    BrokerPublic,
    CustomerPublic,
    DevicePublic,
    DeviceRegisterRequest,
    EquityDecisionPublic,
    EquitySyncRequest,
    LicensePublic,
    LicenseStatusUpdate,
    LoginRequest,
    MobileBootstrapResponse,
    RegisterRequest,
    TokenResponse,
    TradingAccountCreate,
    TradingAccountPublic,
)
from app.security import (
    create_access_token,
    get_current_customer,
    hash_password,
    require_admin,
    require_service_token,
    verify_password,
)
from app.services.entitlements import reconcile_license
from app.services.equity_router import select_bot

settings = get_settings()
router = APIRouter(prefix="/api/v1")


@router.post("/auth/register", response_model=CustomerPublic, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> Customer:
    email = request.email.strip().lower()
    if await db.scalar(select(Customer.id).where(Customer.email == email)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    customer = Customer(
        email=email,
        full_name=request.full_name.strip(),
        phone=request.phone.strip() if request.phone else None,
        password_hash=hash_password(request.password),
        role=Role.CUSTOMER,
    )
    db.add(customer)
    await db.commit()
    await db.refresh(customer)
    return customer


@router.post("/auth/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    customer = await db.scalar(
        select(Customer).where(Customer.email == request.email.strip().lower())
    )
    if customer is None or not customer.is_active or not verify_password(
        request.password, customer.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token, expires_in = create_access_token(customer)
    return TokenResponse(access_token=token, expires_in=expires_in)


@router.get("/me", response_model=CustomerPublic)
async def me(customer: Customer = Depends(get_current_customer)) -> Customer:
    return customer


@router.get("/brokers", response_model=list[BrokerPublic])
async def list_brokers(
    _: Customer = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
) -> list[Broker]:
    result = await db.scalars(
        select(Broker).where(Broker.is_active.is_(True)).order_by(Broker.display_name)
    )
    return list(result)


@router.post(
    "/accounts",
    response_model=TradingAccountPublic,
    status_code=status.HTTP_201_CREATED,
)
async def create_trading_account(
    request: TradingAccountCreate,
    customer: Customer = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
) -> TradingAccount:
    broker = await db.get(Broker, request.broker_id)
    if broker is None or not broker.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Broker unavailable")

    account = TradingAccount(
        customer_id=customer.id,
        broker_id=broker.id,
        broker_login=request.broker_login.strip(),
        server_name=request.server_name.strip() if request.server_name else None,
        status=AccountStatus.PENDING,
    )
    db.add(account)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This broker account is already registered",
        ) from exc
    await db.refresh(account)
    return account


@router.get("/accounts", response_model=list[TradingAccountPublic])
async def list_accounts(
    customer: Customer = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
) -> list[TradingAccount]:
    result = await db.scalars(
        select(TradingAccount)
        .where(TradingAccount.customer_id == customer.id)
        .order_by(TradingAccount.created_at.desc())
    )
    return list(result)


@router.put("/devices", response_model=DevicePublic)
async def register_device(
    request: DeviceRegisterRequest,
    customer: Customer = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
) -> Device:
    device = await db.scalar(select(Device).where(Device.device_id == request.device_id))
    now = datetime.now(UTC)

    if device is not None and device.customer_id != customer.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Device is registered to another account",
        )

    if device is None:
        device = Device(
            customer_id=customer.id,
            platform=request.platform,
            device_id=request.device_id,
        )
        db.add(device)

    device.platform = request.platform
    device.push_token = request.push_token
    device.app_version = request.app_version
    device.is_active = True
    device.last_seen_at = now

    await db.commit()
    await db.refresh(device)
    return device


@router.get("/mobile/bootstrap", response_model=MobileBootstrapResponse)
async def mobile_bootstrap(
    customer: Customer = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
) -> MobileBootstrapResponse:
    accounts = list(
        await db.scalars(
            select(TradingAccount)
            .where(TradingAccount.customer_id == customer.id)
            .order_by(TradingAccount.created_at.desc())
        )
    )
    licenses = list(
        await db.scalars(
            select(License)
            .where(License.customer_id == customer.id)
            .order_by(License.created_at.desc())
        )
    )
    return MobileBootstrapResponse(
        customer=CustomerPublic.model_validate(customer),
        accounts=[TradingAccountPublic.model_validate(item) for item in accounts],
        licenses=[LicensePublic.model_validate(item) for item in licenses],
        feature_flags={
            "android": True,
            "ios": True,
            "push_notifications": False,
            "billing": False,
            "live_kronos_assignment": settings.kronos_push_enabled,
        },
    )


@router.put(
    "/internal/accounts/{account_id}/equity",
    response_model=EquityDecisionPublic,
    dependencies=[Depends(require_service_token)],
)
async def sync_equity(
    account_id: uuid.UUID,
    request: EquitySyncRequest,
    db: AsyncSession = Depends(get_db),
) -> EquityDecisionPublic:
    account = await db.get(TradingAccount, account_id)
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    decision = select_bot(request.equity_usd)
    account.equity_usd = decision.equity_usd
    account.bot_tier = decision.tier
    account.route_reason = decision.reason
    account.status = request.account_status
    account.last_synced_at = datetime.now(UTC)

    await reconcile_license(db, account, decision)
    db.add(
        AuditEvent(
            action="equity_sync",
            entity_type="trading_account",
            entity_id=str(account.id),
            payload={
                "equity_usd": str(decision.equity_usd),
                "bot_tier": decision.tier.value,
                "eligible": decision.eligible,
                "reason": decision.reason,
            },
        )
    )
    await db.commit()
    return EquityDecisionPublic(
        eligible=decision.eligible,
        tier=decision.tier,
        equity_usd=decision.equity_usd,
        reason=decision.reason,
    )


@router.get("/admin/dashboard", response_model=AdminDashboardResponse)
async def admin_dashboard(
    _: Customer = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> AdminDashboardResponse:
    customers = await db.scalar(select(func.count()).select_from(Customer)) or 0
    active_accounts = (
        await db.scalar(
            select(func.count())
            .select_from(TradingAccount)
            .where(TradingAccount.status == AccountStatus.ACTIVE)
        )
        or 0
    )
    active_licenses = (
        await db.scalar(
            select(func.count())
            .select_from(License)
            .where(License.status == LicenseStatus.ACTIVE)
        )
        or 0
    )
    registered_devices = await db.scalar(select(func.count()).select_from(Device)) or 0
    queued_notifications = (
        await db.scalar(
            select(func.count())
            .select_from(Notification)
            .where(Notification.status == NotificationStatus.QUEUED)
        )
        or 0
    )

    return AdminDashboardResponse(
        customers=customers,
        active_accounts=active_accounts,
        active_licenses=active_licenses,
        registered_devices=registered_devices,
        queued_notifications=queued_notifications,
    )


@router.post(
    "/admin/brokers",
    response_model=BrokerPublic,
    status_code=status.HTTP_201_CREATED,
)
async def create_broker(
    request: BrokerCreate,
    admin: Customer = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> Broker:
    broker = Broker(
        slug=request.slug,
        display_name=request.display_name.strip(),
        adapter_key=request.adapter_key.strip(),
        api_base_url=request.api_base_url,
    )
    db.add(broker)
    db.add(
        AuditEvent(
            actor_customer_id=admin.id,
            action="broker_created",
            entity_type="broker",
            entity_id=request.slug,
            payload={"display_name": request.display_name, "adapter_key": request.adapter_key},
        )
    )
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Broker slug already exists"
        ) from exc
    await db.refresh(broker)
    return broker


@router.put("/admin/licenses/{license_id}", response_model=LicensePublic)
async def update_license_status(
    license_id: uuid.UUID,
    request: LicenseStatusUpdate,
    admin: Customer = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> License:
    license_record = await db.get(License, license_id)
    if license_record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="License not found")

    previous = license_record.status
    license_record.status = request.status
    if request.status == LicenseStatus.ACTIVE and license_record.starts_at is None:
        license_record.starts_at = datetime.now(UTC)

    db.add(
        AuditEvent(
            actor_customer_id=admin.id,
            action="license_status_changed",
            entity_type="license",
            entity_id=str(license_record.id),
            payload={"from": previous.value, "to": request.status.value},
        )
    )
    await db.commit()
    await db.refresh(license_record)
    return license_record
