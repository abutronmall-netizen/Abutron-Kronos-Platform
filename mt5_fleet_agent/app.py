from __future__ import annotations

from decimal import Decimal
import json
import os
import shutil
import subprocess
import sys
import time
import uuid

from fastapi import FastAPI, Header, HTTPException
import psutil

from .dpapi import protect_for_current_user
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


def _terminate_terminal(terminal) -> None:
    target = os.path.normcase(os.path.abspath(str(terminal)))
    for proc in psutil.process_iter(["pid", "exe"]):
        try:
            exe = proc.info.get("exe")
            if exe and os.path.normcase(os.path.abspath(exe)) == target:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except psutil.TimeoutExpired:
                    proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
            continue


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
    result_path = verify_root / "verify-result.json"
    worker = None

    try:
        env = os.environ.copy()
        env.update(
            {
                "ABUTRON_VERIFY_LOGIN": request.login,
                "ABUTRON_VERIFY_SERVER": request.server,
                "ABUTRON_VERIFY_PASSWORD_DPAPI": protect_for_current_user(request.password),
                "ABUTRON_VERIFY_TERMINAL_PATH": str(terminal),
                "ABUTRON_VERIFY_TIMEOUT_MS": str(settings.verify_timeout_ms),
                "ABUTRON_VERIFY_RESULT_PATH": str(result_path),
            }
        )
        worker = subprocess.Popen(
            [sys.executable, "-m", "mt5_fleet_agent.verify_worker"],
            cwd=str(settings.terminal_template_dir.parent.parent.parent),
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

        hard_timeout = max(5.0, (settings.verify_timeout_ms / 1000.0) + 5.0)
        try:
            worker.wait(timeout=hard_timeout)
        except subprocess.TimeoutExpired as exc:
            try:
                parent = psutil.Process(worker.pid)
                children = parent.children(recursive=True)
                for child in children:
                    child.kill()
                parent.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
                pass
            raise HTTPException(status_code=504, detail="MT5 verification timed out") from exc

        if not result_path.exists():
            raise HTTPException(status_code=502, detail="MT5 verification worker returned no result")

        result = json.loads(result_path.read_text(encoding="utf-8"))
        if not result.get("ok"):
            raise HTTPException(
                status_code=502,
                detail=str(result.get("error") or "MT5 verification failed"),
            )

        return VerifyResponse(
            verified=True,
            login=str(result["login"]),
            server=str(result["server"]),
            currency=str(result.get("currency") or "USD"),
            equity=Decimal(str(result.get("equity") or "0")).quantize(Decimal("0.01")),
            company=str(result.get("company") or ""),
            terminal=str(terminal),
        )
    finally:
        if worker is not None and worker.poll() is None:
            try:
                parent = psutil.Process(worker.pid)
                children = parent.children(recursive=True)
                for child in children:
                    child.kill()
                parent.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
                pass
        _terminate_terminal(terminal)
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
