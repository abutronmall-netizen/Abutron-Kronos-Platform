# Reviewed baseline for isolated Sentinel telemetry freshness acceptance.
# Separate from model-generated draft PRs; no production execution.
from datetime import datetime


def telemetry_fresh(timestamp: str, now: datetime) -> bool:
    if not isinstance(timestamp, str) or not isinstance(now, datetime):
        return False
    if now.tzinfo is None or now.utcoffset() is None:
        return False
    try:
        observed = datetime.fromisoformat(timestamp)
    except (ValueError, TypeError):
        return False
    if observed.tzinfo is None or observed.utcoffset() is None:
        return False
    age = (now - observed).total_seconds()
    return 0.0 <= age <= 180.0
