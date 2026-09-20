from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

import httpx

from .dpapi import protect_for_current_user
from .models import StartRequest
from .settings import FleetSettings
from .store import FleetStore


class FleetManagerError(RuntimeError):
    pass


class FleetManager:
    def __init__(self, settings: FleetSettings, store: FleetStore):
        self.settings = settings
        self.store = store

    def allocate_port(self, requested: int | None = None) -> int:
        used = self.store.list_ports()
        if requested is not None:
            if requested < self.settings.port_start or requested > self.settings.port_end:
                raise FleetManagerError("Requested port is outside the fleet range")
            if requested in used:
                raise FleetManagerError("Requested port is already allocated")
            return requested
        for port in range(self.settings.port_start, self.settings.port_end + 1):
            if port not in used:
                return port
        raise FleetManagerError("No MT5 fleet ports are available")

    def provision_terminal(self, account_id: str) -> Path:
        source = self.settings.terminal_template_dir
        target = self.settings.instances_root / str(account_id)
        terminal = target / "terminal64.exe"
        if terminal.exists():
            return terminal
        if not (source / "terminal64.exe").exists():
            raise FleetManagerError(f"IC Markets MT5 template is missing: {source / 'terminal64.exe'}")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, target, dirs_exist_ok=True)
        if not terminal.exists():
            raise FleetManagerError("Provisioned MT5 terminal is incomplete")
        return terminal

    def start(self, request: StartRequest) -> dict:
        existing = self.store.get_by_account(str(request.account_id))
        if existing and self._existing_session_healthy(existing, request):
            return existing

        if existing:
            self.store.delete(existing["session_id"])

        port = self.allocate_port(request.requested_port)
        terminal = self.provision_terminal(str(request.account_id))
        session_id = str(uuid.uuid4())
        env = os.environ.copy()
        env.update({
            "ABUTRON_SESSION_ID": session_id,
            "ABUTRON_SESSION_ACCOUNT_ID": str(request.account_id),
            "ABUTRON_SESSION_LOGIN": request.login,
            "ABUTRON_SESSION_SERVER": request.server,
            "ABUTRON_SESSION_PASSWORD_DPAPI": protect_for_current_user(request.password),
            "ABUTRON_SESSION_PORT": str(port),
            "ABUTRON_SESSION_TERMINAL_PATH": str(terminal),
            "ABUTRON_SESSION_SERVICE_TOKEN": self.settings.service_token,
        })
        process = subprocess.Popen(
            [sys.executable, "-m", "mt5_fleet_agent.session_runner"],
            cwd=str(Path(__file__).resolve().parents[1]),
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        item = {
            "session_id": session_id,
            "account_id": str(request.account_id),
            "login": request.login,
            "server": request.server,
            "port": port,
            "terminal_instance": str(terminal.parent),
            "pid": process.pid,
            "status": "provisioning",
            "last_error": "",
        }
        self.store.upsert(item)
        gateway = f"http://127.0.0.1:{port}"
        deadline = time.monotonic() + self.settings.startup_timeout_seconds
        while time.monotonic() < deadline:
            if process.poll() is not None:
                self.store.update_status(session_id, "error", "Session runner exited")
                raise FleetManagerError("MT5 session runner exited during startup")
            try:
                response = httpx.get(f"{gateway}/health", headers={"X-Abutron-Session-Token": self.settings.service_token}, timeout=2)
                if response.status_code == 200 and response.json().get("status") == "ok":
                    self.store.update_status(session_id, "running")
                    item["status"] = "running"
                    return item
            except Exception:
                pass
            time.sleep(0.5)
        self.stop(session_id)
        raise FleetManagerError("MT5 session startup timed out")

    def stop(self, session_id: str) -> dict:
        item = self.store.get(session_id)
        if not item:
            raise FleetManagerError("MT5 session not found")
        pid = int(item.get("pid") or 0)
        if pid and self._pid_alive(pid):
            try:
                subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], check=False, capture_output=True, timeout=15)
            except Exception as exc:
                self.store.update_status(session_id, "error", f"Stop failed: {type(exc).__name__}")
                raise FleetManagerError("Unable to stop MT5 session") from exc
        self.store.delete(session_id)
        item["status"] = "disconnected"
        item["pid"] = None
        return item

    def _existing_session_healthy(self, item: dict, request: StartRequest) -> bool:
        if item.get("status") != "running":
            return False

        if item.get("account_id") != str(request.account_id):
            return False
        if item.get("login") != request.login:
            return False
        if str(item.get("server", "")).casefold() != request.server.casefold():
            return False

        pid = int(item.get("pid") or 0)
        if not self._pid_alive(pid):
            return False

        port = int(item.get("port") or 0)
        if port <= 0:
            return False

        try:
            response = httpx.get(
                f"http://127.0.0.1:{port}/health",
                headers={
                    "X-Abutron-Session-Token":
                        self.settings.service_token
                },
                timeout=2,
            )

            if response.status_code != 200:
                return False

            health = response.json()

            return (
                health.get("status") == "ok"
                and health.get("account_id") == str(request.account_id)
                and str(health.get("login")) == request.login
                and str(health.get("server", "")).casefold()
                    == request.server.casefold()
            )
        except Exception:
            return False

    @staticmethod
    def _pid_alive(pid: int) -> bool:
        if pid <= 0:
            return False
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
