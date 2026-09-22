# ABUTRON MT5 Fleet Agent v4.1

Windows-only control agent for isolated IC Markets MetaTrader 5 customer sessions.

## Security model

- Binds to `127.0.0.1` by default.
- Requires `X-Abutron-Fleet-Token` for session endpoints.
- Customer MT5 passwords are never written to the fleet SQLite registry.
- Each account is provisioned into its own MT5 directory and gets its own localhost gateway port.
- Child session password handoff is protected with Windows DPAPI ciphertext.
- The per-account runner exposes health/account connectivity only in this milestone. Order execution remains disabled until the certified v4 bridge is integrated and re-certified per account.
