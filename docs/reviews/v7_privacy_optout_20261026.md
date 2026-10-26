# Abutron V7 account withdrawal: privacy opt-out security review

**Draft only. Not production authorized. Never merge or deploy this branch unchanged.**

Tracked by #20.

## Why this PR is intentionally incomplete

The live API at `/opt/abutron/v7/backend/app/api.py` is newer than
the GitHub `backend/app/api.py` on `main`. It includes production MFA,
email verification, password recovery and customer visibility changes.
Overwriting it with this repository's older source would be unsafe.

This branch contributes only a pure privacy fingerprint helper, 11 synthetic
unit tests, and a review-only SQL schema. It does not integrate the helper
into live authentication and does not alter any production database.

**Important: current helper uses SELECT only. It does not close the race
between signup and a concurrent opt-out insertion. It must not be considered
a complete fix.**

## Before integration or production release

1. Obtain a reviewed, scrubbed authoritative V7 source branch that preserves
   current Admin MFA, customer verification, recovery, permissions and release gates.
2. Obtain and document valid opt-out authorization and retention requirements.
   HMAC digests are pseudonymous personal data; they are not anonymous.
3. Add root-protected stable 32-byte HMAC secret to approved V7 service
   configuration; define key rotation and encrypted escrow, never commit key.
4. Migrate the opt-out table; runtime app has SELECT privilege only.
   All customer opt-out writes must come from a separately audited privacy operator.
5. Add same per-email transaction lock in BOTH opt-out writes and
   public registration. A standalone SELECT-then-INSERT is not race-safe.
6. Check opt-out **before** signup insert/email, email-proof redemption,
   resend-verification, login, forgotten-password email and reset redemption.
   Generic errors; no account enumeration, plaintext HMAC or secrets in logs.
7. Disallow old verification tokens, block verification emails after opt-out,
   and test that an unrelated consenting customer can still register.
8. Run disposable PostgreSQL and ASGI integration tests, concurrency tests,
   the 202-test staging backend suite and independent security review.
9. Validate encrypted DB backup, Google Drive checksum readback, rollback
   and exact pre/post SHA-256 source baseline.
10. Only after an approved production check confirms suppression is active:
    remove the withdrawn pending record via guarded, audited account operation.
    Confirm Cloud SUPERADMIN, OG CUSTOMER, three unrelated inactive records,
    trading locks and customer MFA unaffected.

## Review gate

Never enable LIVE/DEMO trading or licensing through this privacy PR.
Do not delete the pending user before the prevention mechanism is live.
Do not send any verification email or ask the withdrawn person for credentials.

**Passing unit tests are NOT proof of live enforcement.**
