from __future__ import annotations

import argparse
import json
import logging
import time
import urllib.error
import urllib.request
from pathlib import Path

import MetaTrader5 as mt5

LOG = logging.getLogger("abutron-equity-agent")


def load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def read_token(path: str) -> str:
    token = Path(path).read_text(encoding="utf-8").strip()
    if not token:
        raise RuntimeError("Service token file is empty")
    return token


def sync(platform_origin: str, account_id: str, token: str, equity: float) -> dict:
    url = platform_origin.rstrip("/") + "/api/v1/internal/accounts/" + account_id + "/equity"
    body = json.dumps({"equity_usd": f"{equity:.2f}", "account_status": "active"}).encode("utf-8")
    request = urllib.request.Request(
        url, data=body, method="PUT",
        headers={"Content-Type": "application/json", "X-Abutron-Service-Token": token},
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def run(config: dict) -> None:
    terminal_path = str(config["terminal_path"])
    expected_login = int(config["expected_login"])
    poll_seconds = max(5, int(config.get("poll_seconds", 15)))
    token = read_token(str(config["service_token_file"]))

    if not mt5.initialize(terminal_path):
        raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")

    try:
        last_sent: tuple[float, str] | None = None
        while True:
            info = mt5.account_info()
            if info is None:
                LOG.error("MT5 account_info unavailable: %s", mt5.last_error())
                time.sleep(poll_seconds)
                continue
            if int(info.login) != expected_login:
                raise RuntimeError(f"MT5 login mismatch: expected {expected_login}, got {info.login}")
            if str(info.currency).upper() != "USD":
                raise RuntimeError("Production equity router currently requires USD-denominated MT5 accounts")

            equity = round(float(info.equity), 2)
            try:
                decision = sync(str(config["platform_origin"]), str(config["account_id"]), token, equity)
                fingerprint = (equity, str(decision.get("tier")))
                if fingerprint != last_sent:
                    LOG.info("Equity %.2f -> %s (%s)", equity, decision.get("tier"), decision.get("reason"))
                    last_sent = fingerprint
            except urllib.error.HTTPError as exc:
                LOG.error("Platform rejected equity sync: HTTP %s %s", exc.code, exc.read().decode("utf-8", "replace"))
            except (urllib.error.URLError, TimeoutError) as exc:
                LOG.error("Platform equity sync unavailable: %s", exc)

            time.sleep(poll_seconds)
    finally:
        mt5.shutdown()


def main() -> None:
    parser = argparse.ArgumentParser(description="Abutron Windows MT5 equity sync agent")
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run(load_config(Path(args.config)))


if __name__ == "__main__":
    main()
