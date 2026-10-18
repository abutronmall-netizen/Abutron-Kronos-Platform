from datetime import datetime

def telemetry_fresh(timestamp: str, now: datetime) -> bool:
    try:
        observed = datetime.fromisoformat(timestamp)
    except (ValueError, TypeError):
        return False

    # Check timezone awareness for both datetime objects
    if not observed.tzinfo or observed.utcoffset() is None:
        return False
    if not now.tzinfo or now.utcoffset() is None:
        return False

    # Calculate age in seconds
    age = (now - observed).total_seconds()

    # Return True only if age is between 0 and 180 seconds inclusive
    return 0 <= age <= 180
