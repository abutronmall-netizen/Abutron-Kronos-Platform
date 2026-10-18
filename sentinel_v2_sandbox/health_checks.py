"""Safe, deterministic Sentinel acceptance checks for isolated CI runners.
No production imports, broker API, secrets, or privileged operations.
"""
from datetime import datetime, timezone

VALID = {"HEALTHY", "PARTIAL", "DEGRADED", "UNKNOWN", "NOT_INSTRUMENTED"}

def validate_telemetry(timestamp: str, state: str, now: datetime, max_age_seconds: int = 180) -> bool:
    """Reject stale, future-dated, malformed and unexpected state telemetry."""
    if state not in VALID:
        return False
    try:
        observed = datetime.fromisoformat(timestamp)
    except (ValueError, TypeError):
        return False
    if observed.tzinfo is None or now.tzinfo is None:
        return False
    age = (now.astimezone(timezone.utc) - observed.astimezone(timezone.utc)).total_seconds()
    return 0 <= age <= max_age_seconds

def release_gate(*, reviewed: bool, checks_passed: bool, staged: bool, rollback_tested: bool) -> bool:
    """Fail-closed eligibility predicate, NOT an executable deployment."""
    return all((reviewed, checks_passed, staged, rollback_tested))
