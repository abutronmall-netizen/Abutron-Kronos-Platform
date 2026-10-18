from datetime import datetime

def telemetry_fresh(timestamp: str, now: datetime) -> bool:
    try:
        observed = datetime.fromisoformat(timestamp)
        if not observed.tzinfo or observed.utcoffset() is None:
            return False
        if not now.tzinfo or now.utcoffset() is None:
            return False
        age = (now - observed).total_seconds()
        return 0 <= age <= 180
    except (ValueError, TypeError):
        return False
