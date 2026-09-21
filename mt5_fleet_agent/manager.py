from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path

import httpx
import psutil

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
            if (
                requested < self.settings.port_start
                or requested > self.settings.port_end
            ):
                raise FleetManagerError(
                    "Requested port is outside the fleet range"
                )

            if requested in used:
                raise FleetManagerError(
                    "Requested port is already allocated"
                )

            if not self._port_available(requested):
                raise FleetManagerError(
                    "Requested port is already in use"
                )

            return requested

        for port in range(
            self.settings.port_start,
            self.settings.port_end + 1,
        ):
            if (
                port not in used
                and self._port_available(port)
            ):
                return port

        raise FleetManagerError(
            "No MT5 fleet ports are available"
        )

    @staticmethod
    def _port_available(port: int) -> bool:
        try:
            with socket.socket(
                socket.AF_INET,
                socket.SOCK_STREAM,
            ) as probe:
                if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
                    probe.setsockopt(
                        socket.SOL_SOCKET,
                        socket.SO_EXCLUSIVEADDRUSE,
                        1,
                    )

                probe.bind(("127.0.0.1", port))
                return True

        except OSError:
            return False

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
            existing_pid = int(
                existing.get("pid") or 0
            )

            if (
                existing_pid
                and self._pid_alive(existing_pid)
            ):
                raise FleetManagerError(
                    "Existing MT5 session is live but "
                    "failed identity verification"
                )

            self.store.delete(
                existing["session_id"]
            )

        port = self.allocate_port(
            request.requested_port
        )
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
                self.store.update_status(
                    session_id,
                    "error",
                    "Session runner exited",
                )
                self.store.delete(session_id)
                raise FleetManagerError(
                    "MT5 session runner exited during startup"
                )
            try:
                response = httpx.get(f"{gateway}/health", headers={"X-Abutron-Session-Token": self.settings.service_token}, timeout=2)
                if response.status_code == 200 and response.json().get("status") == "ok":
                    self.store.update_status(session_id, "running")
                    item["status"] = "running"
                    return item
            except Exception:
                pass
            time.sleep(0.5)
        self.stop(
            session_id,
            trusted_process=process,
        )
        raise FleetManagerError("MT5 session startup timed out")

    def stop(
        self,
        session_id: str,
        trusted_process: subprocess.Popen | None = None,
    ) -> dict:
        item = self.store.get(session_id)
        if not item:
            raise FleetManagerError("MT5 session not found")

        pid = int(item.get("pid") or 0)

        if pid and self._pid_alive(pid):
            trusted_spawn = (
                trusted_process is not None
                and trusted_process.pid == pid
                and trusted_process.poll() is None
            )

            if (
                not trusted_spawn
                and not self._session_identity_verified(item)
            ):
                self.store.update_status(
                    session_id,
                    "error",
                    "Unable to verify MT5 session identity",
                )
                raise FleetManagerError(
                    "Unable to verify MT5 session identity"
                )

            try:
                result = subprocess.run(
                    ["taskkill", "/PID", str(pid), "/T", "/F"],
                    check=False,
                    capture_output=True,
                    timeout=15,
                )

                if result.returncode != 0 and self._pid_alive(pid):
                    raise FleetManagerError(
                        "MT5 session process tree did not terminate"
                    )

            except FleetManagerError:
                self.store.update_status(
                    session_id,
                    "error",
                    "Stop failed: process still running",
                )
                raise

            except Exception as exc:
                self.store.update_status(
                    session_id,
                    "error",
                    f"Stop failed: {type(exc).__name__}",
                )
                raise FleetManagerError(
                    "Unable to stop MT5 session"
                ) from exc

        self.store.delete(session_id)
        item["status"] = "disconnected"
        item["pid"] = None
        return item

    def _session_identity_verified(self, item: dict) -> bool:
        pid = int(item.get("pid") or 0)
        port = int(item.get("port") or 0)

        if pid <= 0 or port <= 0:
            return False

        try:
            process = psutil.Process(pid)

            command_line = " ".join(process.cmdline()).casefold()
            if "mt5_fleet_agent.session_runner" not in command_line:
                return False

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

            if (
                health.get("status") != "ok"
                or health.get("session_id")
                    != item.get("session_id")
                or health.get("account_id")
                    != item.get("account_id")
                or str(health.get("login"))
                    != str(item.get("login"))
                or str(health.get("server", "")).casefold()
                    != str(item.get("server", "")).casefold()
            ):
                return False

            owned_pids = {pid}
            owned_pids.update(
                child.pid
                for child in process.children(recursive=True)
            )

            for connection in psutil.net_connections(kind="tcp"):
                if connection.status != psutil.CONN_LISTEN:
                    continue
                if not connection.laddr:
                    continue
                if int(connection.laddr.port) != port:
                    continue

                if connection.pid in owned_pids:
                    return True

            return False

        except (
            psutil.Error,
            httpx.HTTPError,
            ValueError,
            TypeError,
            AttributeError,
            OSError,
        ):
            return False

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

            health_matches = (
                health.get("status") == "ok"
                and health.get("session_id")
                    == item.get("session_id")
                and health.get("account_id")
                    == str(request.account_id)
                and str(health.get("login"))
                    == request.login
                and str(health.get("server", "")).casefold()
                    == request.server.casefold()
            )

            if not health_matches:
                return False

            return self._session_identity_verified(item)
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
