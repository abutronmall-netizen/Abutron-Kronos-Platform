# Unattended draft-PR verification (2026-10-18)

Purpose: confirm that the repository owner's updated GitHub Actions permission
allows the **isolated** Qwen3-4B worker to open a review-only **draft** PR.

Expected sequence:
1. A GitHub-hosted ephemeral worker downloads checksum-pinned model/binaries.
2. It generates and validates exactly one bounded Python candidate.
3. It executes acceptance tests only inside a no-network, read-only,
   capability-stripped Docker container with capped retries.
4. It pushes a uniquely named sandbox branch and creates a **draft** PR.
5. It does NOT approve, merge, deploy, start broker services or trade.
6. Independent reviewer and production disaster recovery remain separate gates.

This is documentation, not an authorization for production execution.
