from __future__ import annotations

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class FleetSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ABUTRON_FLEET_", env_file=".env", extra="ignore", case_sensitive=False)
    host: str = "127.0.0.1"
    port: int = 8180
    service_token: str = ""
    terminal_template_dir: Path = Path(r"C:\Abutron\MT5\template")
    instances_root: Path = Path(r"C:\Abutron\MT5\accounts")
    state_db: Path = Path(r"C:\Abutron\MT5\fleet_sessions.db")
    port_start: int = 8200
    port_end: int = 8999
    startup_timeout_seconds: int = 30
    verify_timeout_ms: int = 30000


settings = FleetSettings()
