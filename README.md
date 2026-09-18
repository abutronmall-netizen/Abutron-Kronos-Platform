# Abutron Kronos Platform

Production control plane for the Abutron Trading Software ecosystem.

## Scope

This repository is intentionally separate from the live Kronos trading engine. It owns:

- customer identity and authentication;
- broker and trading-account registration;
- account equity synchronization;
- equity-based bot selection;
- license/entitlement state;
- admin APIs and audit events;
- Android/iOS mobile bootstrap and device registration;
- notification queue persistence;
- multi-broker adapter contracts;
- the guarded API boundary to the live Kronos execution engine.

The trading core remains isolated. Platform code does not import or mutate Kronos internals.

## Equity routing

The automatic account router currently follows the approved Abutron bands:

| USD equity | Bot |
| --- | --- |
| below $20 | Ineligible |
| $20.00 – $3,000.00 | Flipper |
| $3,000.01 – $5,000.00 | Scalper |
| $5,000.01 – $10,000.00 | Master |
| above $10,000.00 | Manual review |

An equity match selects the product tier. It does **not** bypass licensing: a license must be active before execution is enabled.

## Architecture

```text
Android / iOS / Web Admin
          |
          v
   Abutron Platform API
      |          |
      |          +--> Redis
      |
      +--> PostgreSQL
      |
      +--> Broker adapters
      |
      +--> guarded Kronos execution adapter
                   |
                   v
              Kronos V2.x
```

## Local startup

1. Copy `.env.example` to `.env`.
2. Replace all example passwords and tokens.
3. Start the stack:

```bash
docker compose up --build -d
```

4. Bootstrap the first administrator:

```bash
docker compose exec api python -m app.bootstrap
```

5. Development API documentation is available at `/docs`.

## Security defaults

- JWT authenticated customer/admin API.
- Separate service token for broker/equity synchronization.
- Separate engine token for Kronos execution commands.
- Kronos command push is disabled by default with
  `ABUTRON_KRONOS_PUSH_ENABLED=false`.
- No broker or MT5 passwords are stored in the current platform schema.
- Admin changes are written to the audit-event table.
- Production Swagger docs are disabled.

## Current production foundation

Implemented in the first platform milestone:

- FastAPI application and health/readiness endpoints;
- PostgreSQL + Redis Docker stack;
- customer registration/login;
- broker catalogue and multi-broker adapter registry;
- customer trading accounts;
- equity-based Flipper/Scalper/Master routing;
- license creation/reconciliation and admin activation state;
- device registration for Android/iOS;
- mobile bootstrap endpoint;
- notification persistence model;
- admin dashboard counters;
- broker creation endpoint;
- license administration;
- audit trail;
- Kronos execution boundary;
- backend unit tests and GitHub Actions CI.

## Next production milestones

1. Alembic migrations and production database lifecycle.
2. Billing provider integration, plans, invoices and webhook reconciliation.
3. FCM/APNs push delivery workers with retry/dead-letter handling.
4. Concrete HFM/Headway/IC Markets/Pepperstone broker adapters.
5. Full admin web UI.
6. React Native mobile application against the mobile bootstrap contract.
7. Live Kronos assignment event outbox with retries and idempotency.
8. Monitoring, metrics, structured logging and alerting.
