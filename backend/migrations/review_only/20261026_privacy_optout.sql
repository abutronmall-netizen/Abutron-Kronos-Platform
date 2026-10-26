-- SECURITY REVIEW ONLY. Do not apply before reconciled V7 source and approval.
-- Application role may SELECT only; privacy operator owns inserts/deletions.
BEGIN;
SET LOCAL lock_timeout = '5s';
CREATE TABLE IF NOT EXISTS public.customer_email_optouts (
    email_hmac varchar(64) PRIMARY KEY,
    created_at timestamptz NOT NULL DEFAULT now(),
    consent_basis varchar(80) NOT NULL,
    created_by varchar(80) NOT NULL DEFAULT 'reviewed_root_privacy_operator',
    CONSTRAINT valid_privacy_fingerprint CHECK (email_hmac ~ '^[0-9a-f]{64}$'),
    CONSTRAINT valid_privacy_basis CHECK (consent_basis IN
      ('user_requested_account_erasure_optout','user_requested_suppression'))
);
REVOKE ALL ON public.customer_email_optouts FROM PUBLIC;
REVOKE ALL ON public.customer_email_optouts FROM abutron_v7_release_app;
GRANT SELECT ON public.customer_email_optouts TO abutron_v7_release_app;
COMMIT;

-- This migration intentionally contains NO customer email, fingerprint, seed,
-- HMAC key, deletion or grant of application-write rights.
-- Race-safe opt-out operator and signup must take an identical per-email
-- transactional advisory lock before checking/inserting records. Current
-- proposal is only a partial building block; DO NOT DEPLOY ALONE.
