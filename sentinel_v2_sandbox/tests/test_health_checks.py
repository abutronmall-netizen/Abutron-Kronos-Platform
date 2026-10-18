"""Checks execute on an ephemeral GitHub-hosted runner, never on Abutron production."""
from datetime import datetime, timedelta, timezone
from sentinel_v2_sandbox.health_checks import validate_telemetry, release_gate

def test_fresh_valid_observation():
    now=datetime.now(timezone.utc)
    assert validate_telemetry((now-timedelta(seconds=3)).isoformat(),"DEGRADED",now)

def test_stale_future_naive_invalid_state_fail_closed():
    now=datetime.now(timezone.utc)
    assert not validate_telemetry((now-timedelta(minutes=10)).isoformat(),"HEALTHY",now)
    assert not validate_telemetry((now+timedelta(seconds=2)).isoformat(),"HEALTHY",now)
    assert not validate_telemetry(now.replace(tzinfo=None).isoformat(),"HEALTHY",now)
    assert not validate_telemetry(now.isoformat(),"TRADING_ENABLED",now)

def test_release_rejects_missing_independent_review():
    assert not release_gate(reviewed=False,checks_passed=True,staged=True,rollback_tested=True)
    assert not release_gate(reviewed=True,checks_passed=False,staged=True,rollback_tested=True)
    assert not release_gate(reviewed=True,checks_passed=True,staged=True,rollback_tested=False)
    assert release_gate(reviewed=True,checks_passed=True,staged=True,rollback_tested=True)
