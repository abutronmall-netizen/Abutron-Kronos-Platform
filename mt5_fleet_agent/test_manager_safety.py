import subprocess
import unittest
from types import SimpleNamespace
from unittest.mock import patch

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
