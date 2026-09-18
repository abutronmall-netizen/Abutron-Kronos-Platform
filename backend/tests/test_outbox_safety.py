import pytest

from app.workers import outbox


@pytest.mark.asyncio
async def test_outbox_does_not_touch_database_when_kronos_push_disabled(monkeypatch):
    monkeypatch.setattr(outbox.settings, "kronos_push_enabled", False)

    class ForbiddenSession:
        def __call__(self):
            raise AssertionError("database must not be opened while Kronos push is disabled")

    monkeypatch.setattr(outbox, "SessionLocal", ForbiddenSession())

    assert await outbox.process_once() == 0
