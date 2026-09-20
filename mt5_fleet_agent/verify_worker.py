from __future__ import annotations

from decimal import Decimal
import json
import os
from pathlib import Path
import sys

from .dpapi import unprotect_for_current_user

try:
    import MetaTrader5 as mt5
except Exception:
    mt5 = None


def write_result(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def main() -> int:
    result_path = Path(os.environ["ABUTRON_VERIFY_RESULT_PATH"])
    login = os.environ.get("ABUTRON_VERIFY_LOGIN", "")
    server = os.environ.get("ABUTRON_VERIFY_SERVER", "")
    password_dpapi = os.environ.get("ABUTRON_VERIFY_PASSWORD_DPAPI", "")
    terminal_path = os.environ.get("ABUTRON_VERIFY_TERMINAL_PATH", "")
    timeout_ms = int(os.environ.get("ABUTRON_VERIFY_TIMEOUT_MS", "30000") or 30000)

    if mt5 is None:
        write_result(result_path, {"ok": False, "error": "MetaTrader5 package unavailable"})
        return 3
    if not login.isdigit():
        write_result(result_path, {"ok": False, "error": "MT5 login must be numeric"})
        return 4

    password = ""
    try:
        password = unprotect_for_current_user(password_dpapi)
        ok = mt5.initialize(
            path=terminal_path,
            login=int(login),
            password=password,
            server=server,
            timeout=timeout_ms,
            portable=True,
        )
        password = ""
        if not ok:
            code, message = mt5.last_error()
            write_result(
                result_path,
                {"ok": False, "error": f"MT5 initialize failed ({code}): {message}"},
            )
            return 5

        info = mt5.account_info()
        if info is None:
            write_result(result_path, {"ok": False, "error": "MT5 account info unavailable"})
            return 6

        actual_login = str(getattr(info, "login", ""))
        actual_server = str(getattr(info, "server", ""))
        if actual_login != login or actual_server.casefold() != server.casefold():
            write_result(result_path, {"ok": False, "error": "MT5 identity mismatch"})
            return 7

        write_result(
            result_path,
            {
                "ok": True,
                "login": actual_login,
                "server": actual_server,
                "currency": str(getattr(info, "currency", "USD") or "USD"),
                "equity": str(
                    Decimal(str(getattr(info, "equity", 0) or 0)).quantize(Decimal("0.01"))
                ),
                "company": str(getattr(info, "company", "") or ""),
            },
        )
        return 0
    except Exception as exc:
        password = ""
        write_result(
            result_path,
            {"ok": False, "error": f"MT5 verification worker failed: {type(exc).__name__}"},
        )
        return 8
    finally:
        password = ""
        try:
            if mt5 is not None:
                mt5.shutdown()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
