import tempfile
import unittest
from pathlib import Path

from mt5_fleet_agent.store import FleetStore


class FleetStoreSafetyTests(unittest.TestCase):
    def test_list_ports_reserves_only_active_sessions(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = FleetStore(
                Path(tmp) / "fleet-test.db"
            )

            sessions = [
                {
                    "session_id": "running-session",
                    "account_id": "account-running",
                    "login": "1001",
                    "server": "ICMarketsSC-Demo",
                    "port": 8200,
                    "terminal_instance": "terminal-running",
                    "pid": 10001,
                    "status": "running",
                    "last_error": "",
                },
                {
                    "session_id": "provisioning-session",
                    "account_id": "account-provisioning",
                    "login": "1002",
                    "server": "ICMarketsSC-Demo",
                    "port": 8201,
                    "terminal_instance": "terminal-provisioning",
                    "pid": 10002,
                    "status": "provisioning",
                    "last_error": "",
                },
                {
                    "session_id": "disconnected-session",
                    "account_id": "account-disconnected",
                    "login": "1003",
                    "server": "ICMarketsSC-Demo",
                    "port": 8202,
                    "terminal_instance": "terminal-disconnected",
                    "pid": None,
                    "status": "disconnected",
                    "last_error": "",
                },
                {
                    "session_id": "error-session",
                    "account_id": "account-error",
                    "login": "1004",
                    "server": "ICMarketsSC-Demo",
                    "port": 8203,
                    "terminal_instance": "terminal-error",
                    "pid": None,
                    "status": "error",
                    "last_error": "test-only",
                },
            ]

            for item in sessions:
                store.upsert(item)

            self.assertEqual(
                store.list_ports(),
                {8200, 8201},
            )


if __name__ == "__main__":
    unittest.main()
