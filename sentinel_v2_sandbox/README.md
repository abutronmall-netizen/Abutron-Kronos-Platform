# Sentinel V2 isolated engineering workspace (candidate)

This sandbox runs on **ephemeral GitHub-hosted Ubuntu Actions runners**, not on
ABUTRON-PROD-02. Repo token has **contents: read**, and no production secrets or
broker credentials are supplied. Its output is an evidence artifact, not a live
trading or production deployment approval.

- Coding changes arrive on an isolated feature branch or pull request.
- Pytest and Ruff check the source and accepted behavior.
- Security checks scan the source and the filesystem artifact.
- Staging package is archived, checksum-hashed and uploaded as an Actions artifact.
- A signed independent deployment approval, health-check window and verified
  rollback are still required for any production promotion.
- Never run AI-generated code on the production broker server.

The sample health checks are deterministic acceptance fixtures. They are not
evidence of certification for live broker orders or payment infrastructure.
