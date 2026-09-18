from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis
from sqlalchemy import text

from app.api import router
from app.config import get_settings
from app.db import SessionLocal, engine
from app.models import Base
from app.observability import RequestContextMiddleware

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.auto_create_schema:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="Abutron Kronos Platform",
    version="2.42.0",
    docs_url="/docs" if settings.env != "production" else None,
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(RequestContextMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-Abutron-Service-Token",
        "X-Abutron-Signature",
        "X-Request-ID",
    ],
    expose_headers=["X-Request-ID"],
)

app.include_router(router)


@app.get("/health/live")
async def live() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
async def ready() -> dict[str, str]:
    try:
        async with SessionLocal() as db:
            await db.execute(text("SELECT 1"))

        redis = Redis.from_url(settings.redis_url, decode_responses=True)
        try:
            await redis.ping()
        finally:
            await redis.aclose()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Platform dependency unavailable") from exc

    return {"status": "ready"}
