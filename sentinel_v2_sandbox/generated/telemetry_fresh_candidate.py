from datetime import datetime

def telemetry_fresh(timestamp: str, now: datetime) -> bool:
    try:
        # Parse the timestamp using fromisoformat
        parsed = datetime.fromisoformat(timestamp)

        # Check if the parsed timestamp is naive (no timezone info)
        if parsed.tzinfo is None:
            return False

        # Check if the timestamp is in the future by comparing with now
        # Ensure both are timezone-aware for comparison
        if parsed.tzinfo is None or now.tzinfo is None:
            return False

        # Check if the timestamp is in the future
        if parsed > now:
            return False

        # Check if the age is greater than 180 seconds
        age = (now - parsed).total_seconds()
        return age <= 180

    except ValueError:
        # Invalid ISO8601 format
        return False
