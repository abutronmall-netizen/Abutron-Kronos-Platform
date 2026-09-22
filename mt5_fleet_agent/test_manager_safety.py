import socket
import subprocess
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import psutil

from mt5_fleet_agent.manager import FleetManager, FleetManagerError


class FakeStore:
    def __init__(self):
        self.deleted = False
        self.status_updates = []

    def get(self, session_id):
        return {
            "session_id": session_id,
            "account_id": "account-1",
            "login": "53054439",
            "server": "ICMarketsSC-Demo",
            "port": 8200,
            "terminal_instance":
                r"C:\Abutron\MT5\accounts\account-1",
            "pid": 12345,
            "status": "running",
            "last_error": "",
        }

    def update_status(
        self,
        session_id,
        status,
        last_error="",
    ):
        self.status_updates.append(
            (session_id, status, last_error)
        )

    def delete(self, session_id):
        self.deleted = True


class FleetManagerSafetyTests(unittest.TestCase):
    def make_manager(self):
        manager = object.__new__(FleetManager)
        manager.store = FakeStore()
        manager.settings = SimpleNamespace(
            service_token="test-token"
        )
        return manager

    def test_stop_never_kills_unverified_reused_pid(self):
        manager = self.make_manager()

        unrelated_process = SimpleNamespace(
            cmdline=lambda: [
                r"C:\Windows\System32\notepad.exe"
            ],
            children=lambda recursive=True: [],
        )

        with (
            patch.object(
                manager,
                "_pid_alive",
                return_value=True,
            ),
            patch(
                "mt5_fleet_agent.manager.psutil.Process",
                return_value=unrelated_process,
            ),
            patch.object(
                subprocess,
                "run",
            ) as kill,
        ):
            with self.assertRaisesRegex(
                FleetManagerError,
                "Unable to verify MT5 session identity",
            ):
                manager.stop("session-1")

        kill.assert_not_called()
        self.assertFalse(manager.store.deleted)

    def test_start_deletes_dead_stale_existing_session(self):
        manager = object.__new__(FleetManager)

        existing = {
            "session_id": "stale-session",
            "account_id": "account-1",
            "login": "53054439",
            "server": "ICMarketsSC-Demo",
            "port": 8200,
            "terminal_instance":
                r"C:\Abutron\MT5\accounts\account-1",
            "pid": 12345,
            "status": "running",
            "last_error": "",
        }

        deleted = []

        manager.store = SimpleNamespace(
            get_by_account=lambda account_id: existing,
            delete=lambda session_id: deleted.append(
                session_id
            ),
        )

        request = SimpleNamespace(
            account_id="account-1",
            login="53054439",
            server="ICMarketsSC-Demo",
            password="test-only",
            requested_port=None,
        )

        def stop_after_cleanup(requested_port):
            self.assertEqual(
                deleted,
                ["stale-session"],
            )
            raise RuntimeError(
                "stop-after-stale-cleanup"
            )

        with (
            patch.object(
                manager,
                "_existing_session_healthy",
                return_value=False,
            ),
            patch.object(
                manager,
                "_pid_alive",
                return_value=False,
            ),
            patch.object(
                manager,
                "allocate_port",
                side_effect=stop_after_cleanup,
            ),
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "stop-after-stale-cleanup",
            ):
                manager.start(request)

        self.assertEqual(
            deleted,
            ["stale-session"],
        )


    def test_start_reuses_healthy_exact_existing_session(self):
        manager = object.__new__(FleetManager)

        existing = {
            "session_id": "existing-session",
            "account_id": "account-1",
            "login": "53054439",
            "server": "ICMarketsSC-Demo",
            "port": 8200,
            "terminal_instance":
                r"C:\Abutron\MT5\accounts\account-1",
            "pid": 12345,
            "status": "running",
            "last_error": "",
        }

        deleted = []

        manager.store = SimpleNamespace(
            get_by_account=lambda account_id: existing,
            delete=lambda session_id: deleted.append(
                session_id
            ),
        )

        request = SimpleNamespace(
            account_id="account-1",
            login="53054439",
            server="ICMarketsSC-Demo",
            password="test-only",
            requested_port=None,
        )

        with (
            patch.object(
                manager,
                "_existing_session_healthy",
                return_value=True,
            ) as healthy,
            patch.object(
                manager,
                "allocate_port",
                side_effect=AssertionError(
                    "must not allocate a new port"
                ),
            ) as allocate,
            patch.object(
                manager,
                "provision_terminal",
                side_effect=AssertionError(
                    "must not provision a duplicate terminal"
                ),
            ) as provision,
            patch(
                "mt5_fleet_agent.manager.subprocess.Popen",
                side_effect=AssertionError(
                    "must not spawn a duplicate runner"
                ),
            ) as spawn,
        ):
            result = manager.start(request)

        self.assertIs(result, existing)
        healthy.assert_called_once_with(
            existing,
            request,
        )
        allocate.assert_not_called()
        provision.assert_not_called()
        spawn.assert_not_called()
        self.assertEqual(deleted, [])


    def test_start_refuses_unverified_live_existing_session(self):
        manager = object.__new__(FleetManager)

        existing = {
            "session_id": "existing-session",
            "account_id": "account-1",
            "login": "53054439",
            "server": "ICMarketsSC-Demo",
            "port": 8200,
            "terminal_instance":
                r"C:\Abutron\MT5\accounts\account-1",
            "pid": 12345,
            "status": "running",
            "last_error": "",
        }

        deleted = []

        manager.store = SimpleNamespace(
            get_by_account=lambda account_id: existing,
            delete=lambda session_id: deleted.append(
                session_id
            ),
        )

        manager.settings = SimpleNamespace()

        request = SimpleNamespace(
            account_id="account-1",
            login="53054439",
            server="ICMarketsSC-Demo",
            password="test-only",
            requested_port=None,
        )

        with (
            patch.object(
                manager,
                "_existing_session_healthy",
                return_value=False,
            ),
            patch.object(
                manager,
                "_pid_alive",
                return_value=True,
            ),
            patch.object(
                manager,
                "allocate_port",
                side_effect=AssertionError(
                    "must not allocate while an "
                    "unverified live session exists"
                ),
            ) as allocate,
        ):
            with self.assertRaises(FleetManagerError):
                manager.start(request)

        allocate.assert_not_called()
        self.assertEqual(deleted, [])


    def test_start_deletes_row_when_runner_exits_early(self):
        manager = object.__new__(FleetManager)

        upserted = []
        updated = []
        deleted = []

        manager.store = SimpleNamespace(
            get_by_account=lambda account_id: None,
            upsert=lambda item: upserted.append(item.copy()),
            update_status=lambda session_id, status, last_error="": (
                updated.append(
                    (session_id, status, last_error)
                )
            ),
            delete=lambda session_id: deleted.append(
                session_id
            ),
        )

        manager.settings = SimpleNamespace(
            service_token="test-token",
            startup_timeout_seconds=1,
        )

        request = SimpleNamespace(
            account_id="account-1",
            login="53054439",
            server="ICMarketsSC-Demo",
            password="test-only",
            requested_port=None,
        )

        terminal = SimpleNamespace(
            parent=r"C:\Abutron\MT5\accounts\account-1"
        )

        process = SimpleNamespace(
            pid=54321,
            poll=lambda: 1,
        )

        with (
            patch.object(
                manager,
                "allocate_port",
                return_value=8200,
            ),
            patch.object(
                manager,
                "provision_terminal",
                return_value=terminal,
            ),
            patch(
                "mt5_fleet_agent.manager.protect_for_current_user",
                return_value="protected-test-value",
            ),
            patch(
                "mt5_fleet_agent.manager.subprocess.Popen",
                return_value=process,
            ),
            patch(
                "mt5_fleet_agent.manager.psutil.Process",
                return_value=SimpleNamespace(
                    create_time=lambda: 1234.5,
                ),
            ),
        ):
            with self.assertRaisesRegex(
                FleetManagerError,
                "runner exited during startup",
            ):
                manager.start(request)

        self.assertEqual(len(upserted), 1)

        session_id = upserted[0]["session_id"]

        self.assertIn(
            (session_id, "error", "Session runner exited"),
            updated,
        )

        self.assertIn(session_id, deleted)


    def test_allocate_port_rejects_os_occupied_port(self):
        manager = object.__new__(FleetManager)

        with socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM,
        ) as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen(1)

            occupied_port = listener.getsockname()[1]

            manager.settings = SimpleNamespace(
                port_start=occupied_port,
                port_end=occupied_port,
            )
            manager.store = SimpleNamespace(
                list_ports=lambda: set(),
            )

            with self.assertRaises(FleetManagerError):
                manager.allocate_port(
                    requested=occupied_port,
                )


    def test_allocate_port_skips_os_occupied_port(self):
        manager = object.__new__(FleetManager)

        with socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM,
        ) as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen(1)

            occupied_port = listener.getsockname()[1]
            next_port = occupied_port + 1

            manager.settings = SimpleNamespace(
                port_start=occupied_port,
                port_end=next_port,
            )
            manager.store = SimpleNamespace(
                list_ports=lambda: set(),
            )

            selected = manager.allocate_port()

            self.assertEqual(selected, next_port)


    def test_session_identity_rejects_process_creation_time_mismatch(self):
        manager = self.make_manager()

        item = manager.store.get("expected-session")
        item["process_create_time"] = 1000.0

        process = SimpleNamespace(
            cmdline=lambda: [
                "python.exe",
                "-m",
                "mt5_fleet_agent.session_runner",
            ],
            children=lambda recursive=True: [],
            create_time=lambda: 2000.0,
        )

        exact_health = SimpleNamespace(
            status_code=200,
            json=lambda: {
                "status": "ok",
                "session_id": "expected-session",
                "account_id": "account-1",
                "login": "53054439",
                "server": "ICMarketsSC-Demo",
            },
        )

        listener = SimpleNamespace(
            status=psutil.CONN_LISTEN,
            laddr=SimpleNamespace(port=8200),
            pid=12345,
        )

        with (
            patch(
                "mt5_fleet_agent.manager.psutil.Process",
                return_value=process,
            ),
            patch(
                "mt5_fleet_agent.manager.httpx.get",
                return_value=exact_health,
            ),
            patch(
                "mt5_fleet_agent.manager.psutil.net_connections",
                return_value=[listener],
            ),
        ):
            verified = manager._session_identity_verified(
                item
            )

        self.assertFalse(verified)


    def test_existing_session_requires_process_listener_identity(self):
        manager = self.make_manager()

        item = manager.store.get("expected-session")

        request = SimpleNamespace(
            account_id="account-1",
            login="53054439",
            server="ICMarketsSC-Demo",
        )

        exact_health = SimpleNamespace(
            status_code=200,
            json=lambda: {
                "status": "ok",
                "session_id": "expected-session",
                "account_id": "account-1",
                "login": "53054439",
                "server": "ICMarketsSC-Demo",
            },
        )

        with (
            patch.object(
                manager,
                "_pid_alive",
                return_value=True,
            ),
            patch.object(
                manager,
                "_session_identity_verified",
                return_value=False,
            ) as identity,
            patch(
                "mt5_fleet_agent.manager.httpx.get",
                return_value=exact_health,
            ),
        ):
            healthy = manager._existing_session_healthy(
                item,
                request,
            )

        self.assertFalse(healthy)
        identity.assert_called_once_with(item)


    def test_existing_session_rejects_wrong_session_id(self):
        manager = self.make_manager()

        item = manager.store.get("expected-session")

        request = SimpleNamespace(
            account_id="account-1",
            login="53054439",
            server="ICMarketsSC-Demo",
        )

        wrong_health = SimpleNamespace(
            status_code=200,
            json=lambda: {
                "status": "ok",
                "session_id": "different-session",
                "account_id": "account-1",
                "login": "53054439",
                "server": "ICMarketsSC-Demo",
            },
        )

        with (
            patch.object(
                manager,
                "_pid_alive",
                return_value=True,
            ),
            patch(
                "mt5_fleet_agent.manager.httpx.get",
                return_value=wrong_health,
            ),
        ):
            healthy = manager._existing_session_healthy(
                item,
                request,
            )

        self.assertFalse(healthy)


    def test_stop_allows_exact_trusted_spawn_cleanup(self):
        manager = self.make_manager()

        trusted_process = SimpleNamespace(
            pid=12345,
            poll=lambda: None,
        )

        with (
            patch.object(
                manager,
                "_pid_alive",
                return_value=True,
            ),
            patch.object(
                manager,
                "_session_identity_verified",
                side_effect=AssertionError(
                    "health identity must not be required "
                    "for the exact Popen object"
                ),
            ),
            patch.object(
                subprocess,
                "run",
                return_value=SimpleNamespace(returncode=0),
            ) as kill,
        ):
            result = manager.stop(
                "session-1",
                trusted_process=trusted_process,
            )

        kill.assert_called_once()
        self.assertTrue(manager.store.deleted)
        self.assertEqual(result["status"], "disconnected")
        self.assertIsNone(result["pid"])


if __name__ == "__main__":
    unittest.main()
