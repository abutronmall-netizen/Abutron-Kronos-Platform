from __future__ import annotations

import os
from contextlib import asynccontextmanager
from decimal import Decimal

from fastapi import FastAPI, Header, HTTPException
import uvicorn

from .dpapi import unprotect_for_current_user

try:
    import MetaTrader5 as mt5
except Exception:
    mt5 = None

SESSION_ID = os.environ.get("ABUTRON_SESSION_ID", "")
ACCOUNT_ID = os.environ.get("ABUTRON_SESSION_ACCOUNT_ID", "")
LOGIN = os.environ.get("ABUTRON_SESSION_LOGIN", "")
SERVER = os.environ.get("ABUTRON_SESSION_SERVER", "")
PASSWORD_DPAPI = os.environ.get("ABUTRON_SESSION_PASSWORD_DPAPI", "")
PORT = int(os.environ.get("ABUTRON_SESSION_PORT", "0") or 0)
TERMINAL_PATH = os.environ.get("ABUTRON_SESSION_TERMINAL_PATH", "")
SERVICE_TOKEN = os.environ.get("ABUTRON_SESSION_SERVICE_TOKEN", "")


def auth(token: str | None) -> None:
    if not SERVICE_TOKEN or token != SERVICE_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")


def ensure_ready():
    if mt5 is None:
        raise RuntimeError("MetaTrader5 Python package is unavailable")
    if not LOGIN.isdigit():
        raise RuntimeError("MT5 login must be numeric")
    password = unprotect_for_current_user(PASSWORD_DPAPI)
    ok = mt5.initialize(path=TERMINAL_PATH, login=int(LOGIN), password=password, server=SERVER, portable=True)
    password = ""
    if not ok:
        raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")
    account = mt5.account_info()
    if account is None:
        raise RuntimeError("MT5 account info unavailable")
    if str(getattr(account, "login", "")) != LOGIN:
        raise RuntimeError("MT5 login mismatch")
    if str(getattr(account, "server", "")).casefold() != SERVER.casefold():
        raise RuntimeError("MT5 server mismatch")
    return account


@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_ready()
    yield
    if mt5 is not None:
        mt5.shutdown()


app = FastAPI(title="Abutron MT5 Session Runner", version="4.1.0", lifespan=lifespan)


@app.get("/health")
def health(x_abutron_session_token: str | None = Header(default=None)):
    auth(x_abutron_session_token)
    account = ensure_ready()
    return {"status": "ok", "session_id": SESSION_ID, "account_id": ACCOUNT_ID, "login": str(account.login), "server": str(account.server)}


@app.get("/v1/account")
def account(x_abutron_session_token: str | None = Header(default=None)):
    auth(x_abutron_session_token)
    info = ensure_ready()
    return {
        "login": str(info.login),
        "server": str(info.server),
        "currency": str(getattr(info, "currency", "USD") or "USD"),
        "equity": str(Decimal(str(getattr(info, "equity", 0) or 0)).quantize(Decimal("0.01"))),
        "company": str(getattr(info, "company", "") or ""),
    }


if __name__ == "__main__":
    if PORT <= 0:
        raise SystemExit("ABUTRON_SESSION_PORT is required")
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")
