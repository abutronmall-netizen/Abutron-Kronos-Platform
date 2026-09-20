from __future__ import annotations

import sqlite3
import threading
from pathlib import Path


class FleetStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._init()

    def _db(self):
        return sqlite3.connect(self.path, timeout=10)

    def _init(self) -> None:
        with self._db() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS sessions(session_id TEXT PRIMARY KEY,account_id TEXT NOT NULL UNIQUE,login TEXT NOT NULL,server TEXT NOT NULL,port INTEGER NOT NULL UNIQUE,terminal_instance TEXT NOT NULL,pid INTEGER,status TEXT NOT NULL,last_error TEXT DEFAULT '')""")
            db.commit()

    def list_ports(self) -> set[int]:
        with self._db() as db:
            return {int(row[0]) for row in db.execute("SELECT port FROM sessions").fetchall()}

    def get_by_account(self, account_id: str) -> dict | None:
        with self._db() as db:
            row = db.execute("SELECT session_id,account_id,login,server,port,terminal_instance,pid,status,last_error FROM sessions WHERE account_id=?", (str(account_id),)).fetchone()
        return self._row(row)

    def get(self, session_id: str) -> dict | None:
        with self._db() as db:
            row = db.execute("SELECT session_id,account_id,login,server,port,terminal_instance,pid,status,last_error FROM sessions WHERE session_id=?", (str(session_id),)).fetchone()
        return self._row(row)

    def upsert(self, item: dict) -> None:
        with self._lock, self._db() as db:
            db.execute("""INSERT INTO sessions(session_id,account_id,login,server,port,terminal_instance,pid,status,last_error) VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(account_id) DO UPDATE SET session_id=excluded.session_id,login=excluded.login,server=excluded.server,port=excluded.port,terminal_instance=excluded.terminal_instance,pid=excluded.pid,status=excluded.status,last_error=excluded.last_error""", (item["session_id"], item["account_id"], item["login"], item["server"], item["port"], item["terminal_instance"], item.get("pid"), item["status"], item.get("last_error", "")))
            db.commit()

    def update_status(self, session_id: str, status: str, last_error: str = "") -> None:
        with self._lock, self._db() as db:
            db.execute("UPDATE sessions SET status=?, last_error=? WHERE session_id=?", (status, last_error, str(session_id)))
            db.commit()

    @staticmethod
    def _row(row) -> dict | None:
        if not row:
            return None
        keys = ("session_id", "account_id", "login", "server", "port", "terminal_instance", "pid", "status", "last_error")
        return dict(zip(keys, row))
