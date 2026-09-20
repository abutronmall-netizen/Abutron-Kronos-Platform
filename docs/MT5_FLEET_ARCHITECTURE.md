# ABUTRON MT5 Fleet Architecture v4.1

## Purpose

Standardize Abutron on IC Markets + MetaTrader 5 while allowing many customer accounts to run independently.

```text
Mobile / Web
    |
    | HTTPS + JWT
    v
Abutron API / Customer Control Plane
    |
    +--> PostgreSQL
    |      +-- TradingAccount
    |      +-- MT5Credential (encrypted)
    |      +-- MT5Session
    |
    +--> Equity Router
    |
    +--> MT5 Fleet Agent (private/localhost)
             |
             +--> account A terminal instance -> localhost port A
             +--> account B terminal instance -> localhost port B
             +--> account N terminal instance -> localhost port N
                       |
                       v
                   IC Markets MT5
```

## Trust boundaries

- Mobile never receives MT5 credentials, fleet service tokens or internal gateway URLs.
- PostgreSQL stores only encrypted MT5 passwords.
- The Fernet master key is stored outside PostgreSQL and Git.
- Backend-to-agent calls require a separate fleet service token.
- Fleet Agent binds to `127.0.0.1` by default.
- Each customer terminal runs from an isolated directory.
- Child session password handoff uses Windows DPAPI-protected ciphertext.
- Session gateway ports are localhost-only.

## Fail-closed identity

A session is accepted only when the authenticated customer owns the trading account, the broker is IC Markets, submitted login/server match the account, MT5 accepts the credentials, and MT5 reports the same login/server after connection. Any disagreement blocks connection.

## Execution posture

The per-account runner currently exposes account identity and health only. Trading endpoints are intentionally absent until the certified Abutron v4 MT5 execution contract is integrated and re-certified per isolated session.
