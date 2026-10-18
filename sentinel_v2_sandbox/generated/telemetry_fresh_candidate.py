from datetime import datetime, timezone

def telemetry_fresh(timestamp: str, now: datetime) -> bool:
    try:
        parsed_timestamp = datetime.fromisoformat(timestamp)
    except ValueError:
        return False
    
    # Check if now is timezone-aware before comparing
    if now.tzinfo is None:
        return False
    
    # If parsed_timestamp has no timezone, it's naive and cannot be compared
    if parsed_timestamp.tzinfo is None:
        return False
    
    # Ensure both timestamps are timezone-aware for comparison
    if parsed_timestamp.tzinfo is None:
        # Convert to timezone-aware if now has timezone info
        if now.tzinfo is not None:
            parsed_timestamp = parsed_timestamp.replace(tzinfo=now.tzinfo)
        else:
            return False
    
    # Compare timestamps: parsed_timestamp should not be in the future
    if parsed_timestamp > now:
        return False
    
    age = (now - parsed_timestamp).total_seconds()
    return 0 <= age <= 180
