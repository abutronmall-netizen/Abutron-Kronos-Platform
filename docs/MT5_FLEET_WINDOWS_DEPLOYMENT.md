# Windows deployment — MT5 Fleet Agent v4.1

1. Create `C:\Abutron\MT5\template` and `C:\Abutron\MT5\accounts`.
2. Put a clean IC Markets MT5 installation in the template so `terminal64.exe` exists.
3. Install `mt5_fleet_agent/requirements.txt` in a Windows Python virtual environment.
4. Configure `ABUTRON_FLEET_SERVICE_TOKEN`, template path, instance path, state DB, and port range 8200-8999.
5. Start the agent on `127.0.0.1:8180` only.
6. Generate a Fernet key for the backend and configure `ABUTRON_MT5_CREDENTIAL_KEY` plus the same fleet token.
7. Run `alembic upgrade head` and `python -m app.bootstrap_icmarkets`.
8. Do not expose 8180 or 8200-8999 publicly.
9. Do not add order endpoints until isolated-session execution certification is complete.
