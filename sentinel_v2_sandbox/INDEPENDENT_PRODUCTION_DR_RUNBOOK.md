# Sentinel V2 — independent production recovery certification protocol

**Release gate: BLOCKED until this drill is actually executed and externally reviewed.**

This protocol is intentionally **not** an execution script. It must not be run
on ABUTRON-PROD-02 (the production machine). The real customer and broker
environment must remain untouched during the drill.

## Verified starting position, 2026-10-18

- Production host: `ABUTRON-PROD-02`, Ubuntu, ONLINE; second registered remote
  device `ABUTRON-PROD-01` OFFLINE.
- Last Step22 V12 evidence:
  `abutron_step22_v12_completed_recovery_closeout_20261016.json` reports
  **16/24** production cutover gates, PostgreSQL restore across **66** tables,
  **54,446** rows, `remote_restic_full_file_restore_verified=true`,
  `independent_machine_dr_certified=false`,
  `full_disaster_recovery_certified=false`.
- Updated encrypted offsite readback on 2026-10-18T03:53:31Z verified cipher
  parity and same-host temporary-directory restore. It explicitly reports
  `remote_restore_mode=SAME_HOST_TEMPORARY_DIRECTORY_ONLY`.
- Off-host GitHub Action sandbox *fixture* rollback passed, but is not a
  production core backup restore.
- The source/credential inventory, encrypted archive and any customer data
  MUST NOT be uploaded as public GitHub CI artifacts.

## Required operator-controlled preparation

1. Supply a separately authorized, clean, isolated Ubuntu recovery machine or
   time-limited VM. Establish independent administrative access, a separate
   host identity, dedicated storage, and a firewall that cannot reach live
   broker order endpoints. Record machine ID, snapshot and creation time.
2. Approve secure access to the **encrypted** offsite critical-core backup
   from the existing backup service. Mount credentials from a secret manager
   on the recovery machine only. Do not copy keys or vault passwords into
   GitHub, logs, chat or the QA artifact. Keep the archive encrypted until
   isolated inside the new host.
3. Independently compare remotely fetched encrypted archive SHA-256 and size
   with the backup ledger; verify integrity and decryptability. Record original
   snapshot timestamp to calculate actual RPO.
4. Restore application configuration and secrets from approved recovery
   procedures; reject missing, mismatched and stale components. Verify
   protected files' hashes and permissions without printing values.
5. Restore PostgreSQL into a **new isolated cluster** and run schema, invalid
   constraints, row-count, and consistency checks; restore the SQLite
   databases and run `PRAGMA quick_check`; compare totals with the backup
   inventory. Do not point production services to the recovery data.
6. Start shadow/recovery services only with broker execution disabled.
   Validate internal health endpoints, authentication boundaries, customer
   portal read-only access, gateway recovery behavior and fail-closed risk
   controls. Do not place a demo or real order during this drill.
7. Exercise a forced failing release and demonstrate an **atomic rollback**
   to a known-good recovery snapshot. Confirm the rollback after a fresh
   service restart, database integrity check and API smoke test.
8. Record start and finish times. Calculate actual RTO, actual RPO, pass/fail
   for each independent test and policy acceptance against operator-approved
   RTO/RPO targets. Never invent targets, scores or results.
9. Have a DIFFERENT authorized reviewer inspect immutable evidence (machine,
   backup checksum, scope, restored row counts, rollback hashes, timestamp,
   read-only order assertions), validate source and approve the exact release
   commit. Record their signed outcome in the protected certification store.

## Deny-by-default checklist

- [ ] Distinct authorized recovery machine available and verified.
- [ ] Fresh authorized encrypted offsite backup fetched/validated remotely.
- [ ] Actual critical files, SQLite and PostgreSQL restored off production.
- [ ] Application startup, authentication and risk controls tested without
      broker orders.
- [ ] Independent RTO/RPO measurements accepted.
- [ ] Failure injection and atomic rollback independently verified.
- [ ] Different authorized reviewer approved exact tested release commit.
- [ ] Recovery evidence securely retained outside the production machine.

**Only when all boxes have independently verified evidence** may external
release management *consider* enabling the next controlled deployment gate.
No action in this document independently authorizes trading or deployment.
