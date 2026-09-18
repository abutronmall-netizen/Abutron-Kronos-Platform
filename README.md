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

## Bot execution profiles

Equity routing is deliberately separated from strategy behavior. The router chooses the tier; the tier resolves to a versioned strategy profile; licensing decides whether execution is enabled.

| Product | Core style | Primary TF flow | Trade frequency |
| --- | --- | --- | --- |
| Flipper | Adaptive directional grid/basket | M15 / M5 -> M1 | High |
| Scalper | Precision sniper scalping | M15 / M5 -> M1 | Medium/high |
| Master | Day trading / Trend + SMC/ICT | H4 / H1 -> M15 -> M5 | Low/selective |

The assignment contract sends both `bot_tier` and the canonical `strategy_profile` to Kronos. Profit figures used in product material are business targets only; they are not execution guarantees and are not used to force trading frequency or risk.

## Architecture

```text
Android / iOS / React Admin
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
6. The production admin console is available on port `3000` by default.

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
- notification persistence, delivery attempts and customer read state;
- admin dashboard counters and financial/audit views;
- React/TypeScript admin console with dashboard, customer/account/license/billing/audit views and license controls;
- broker creation endpoint;
- license administration;
- audit trail;
- signed provider-neutral billing webhook boundary with idempotent payment confirmation;
- request correlation IDs and structured HTTP access logging;
- Kronos execution boundary;
- backend unit tests and GitHub Actions CI.

## Next production milestones

1. Concrete payment-provider adapters on top of the signed webhook contract, plus invoice/refund reconciliation.
2. FCM/APNs gateway implementation, invalid-token cleanup and retry/dead-letter policy.
3. Concrete HFM/Headway/IC Markets/Pepperstone broker adapters.
4. Extend the admin console with broker/referral/notification creation workflows and role-specific support tooling.
5. React Native Android/iOS application against the mobile bootstrap contract.
6. Metrics, dashboards, alerting and production SLOs.
7. Backup/restore drills, secret rotation and deployment runbooks.
