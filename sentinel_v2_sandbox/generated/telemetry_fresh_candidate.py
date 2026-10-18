from datetime import datetime, timezone

def telemetry_fresh(timestamp: str, now: datetime) -> bool:
    try:
        parsed_timestamp = datetime.fromisoformat(timestamp)
    except ValueError:
        return False
    
    if parsed_timestamp.tzinfo is None:
        return False
    
    if parsed_timestamp > now:
        return False
    
    age = (now - parsed_timestamp).total_seconds()
    return 0 <= age <= 180
