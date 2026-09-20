from __future__ import annotations

from decimal import Decimal
import shutil
import time
import uuid

from fastapi import FastAPI, Header, HTTPException

from .manager import FleetManager, FleetManagerError
from .models import StartRequest, StartResponse, StopResponse, VerifyRequest, VerifyResponse
from .settings import settings
from .store import FleetStore

try:
    import MetaTrader5 as mt5
except Exception:
    mt5 = None

store = FleetStore(settings.state_db)
manager = FleetManager(settings, store)
app = FastAPI(title="Abutron MT5 Fleet Agent", version="4.1.0")


def auth(token: str | None) -> None:
    if not settings.service_token:
        raise HTTPException(status_code=503, detail="Fleet service token is not configured")
    if token != settings.service_token:
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.get("/health")
def health():
    return {"status": "ok", "version": "4.1.0", "mt5_package": mt5 is not None}


@app.post("/v1/verify", response_model=VerifyResponse)
def verify(request: VerifyRequest, x_abutron_fleet_token: str | None = Header(default=None)):
    auth(x_abutron_fleet_token)
    if mt5 is None:
        raise HTTPException(status_code=503, detail="MetaTrader5 package unavailable")
    if not request.login.isdigit():
        raise HTTPException(status_code=400, detail="MT5 login must be numeric")
    template_terminal = settings.terminal_template_dir / "terminal64.exe"
    if not template_terminal.exists():
        raise HTTPException(status_code=503, detail="IC Markets MT5 template is not installed")
    verify_root = settings.instances_root / "_verify" / str(uuid.uuid4())
    shutil.copytree(settings.terminal_template_dir, verify_root, dirs_exist_ok=True)
    terminal = verify_root / "terminal64.exe"
    try:
        ok = mt5.initialize(path=str(terminal), login=int(request.login), password=request.password, server=request.server, portable=True)
        if not ok:
            raise HTTPException(status_code=401, detail="MT5 credentials rejected")
        info = mt5.account_info()
        if info is None:
            raise HTTPException(status_code=502, detail="MT5 account info unavailable")
        login = str(getattr(info, "login", ""))
        server = str(getattr(info, "server", ""))
        if login != request.login or server.casefold() != request.server.casefold():
            raise HTTPException(status_code=409, detail="MT5 identity mismatch")
        return VerifyResponse(
            verified=True,
            login=login,
            server=server,
            currency=str(getattr(info, "currency", "USD") or "USD"),
            equity=Decimal(str(getattr(info, "equity", 0) or 0)).quantize(Decimal("0.01")),
            company=str(getattr(info, "company", "") or ""),
            terminal=str(terminal),
        )
    finally:
        try:
            mt5.shutdown()
        except Exception:
            pass
        time.sleep(0.25)
        shutil.rmtree(verify_root, ignore_errors=True)


@app.post("/v1/sessions/start", response_model=StartResponse)
def start(request: StartRequest, x_abutron_fleet_token: str | None = Header(default=None)):
    auth(x_abutron_fleet_token)
    try:
        item = manager.start(request)
    except FleetManagerError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return StartResponse(started=item["status"] == "running", session_id=item["session_id"], gateway_url=f"http://127.0.0.1:{item['port']}", gateway_port=item["port"], terminal_instance=item["terminal_instance"], status=item["status"])


@app.get("/v1/sessions/{session_id}")
def status(session_id: str, x_abutron_fleet_token: str | None = Header(default=None)):
    auth(x_abutron_fleet_token)
    item = store.get(session_id)
    if not item:
        raise HTTPException(status_code=404, detail="MT5 session not found")
    return {"session_id": item["session_id"], "account_id": item["account_id"], "login": item["login"], "server": item["server"], "gateway_url": f"http://127.0.0.1:{item['port']}", "gateway_port": item["port"], "terminal_instance": item["terminal_instance"], "status": item["status"], "last_error": item["last_error"]}


@app.post("/v1/sessions/{session_id}/stop", response_model=StopResponse)
def stop(session_id: str, x_abutron_fleet_token: str | None = Header(default=None)):
    auth(x_abutron_fleet_token)
    try:
        item = manager.stop(session_id)
    except FleetManagerError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return StopResponse(stopped=True, session_id=item["session_id"], status=item["status"])
