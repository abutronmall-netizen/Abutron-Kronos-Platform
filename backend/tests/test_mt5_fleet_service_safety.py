import asyncio
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.mt5_fleet.models import MT5SessionStatus
from app.mt5_fleet.service import disconnect_mt5_account


class FakeDB:
    def __init__(self, session):
        self.session = session
        self.commits = 0
        self.refreshes = 0

    async def scalar(self, statement):
        return self.session

    async def commit(self):
        self.commits += 1

    async def refresh(self, value):
        self.refreshes += 1


def test_disconnect_clears_agent_session_id():
    async def scenario():
        account = SimpleNamespace(
            id=uuid.uuid4(),
        )
        customer = SimpleNamespace(
            id=uuid.uuid4(),
        )

        session = SimpleNamespace(
            agent_session_id="session-123",
            agent_url="http://127.0.0.1:8180",
            gateway_url="http://127.0.0.1:8200",
            gateway_port=8200,
            terminal_instance=(
                r"C:\Abutron\MT5\accounts\account-1"
            ),
            status=MT5SessionStatus.RUNNING,
            last_error=None,
            last_health_at=None,
        )

        db = FakeDB(session)
        stopped = []

        class FakeFleetClient:
            def __init__(self, base_url, token):
                pass

            async def stop(self, session_id):
                stopped.append(session_id)

        with (
            patch(
                "app.mt5_fleet.service."
                "owned_ic_markets_account",
                new=AsyncMock(
                    return_value=(
                        account,
                        SimpleNamespace(),
                    )
                ),
            ),
            patch(
                "app.mt5_fleet.service.MT5FleetClient",
                FakeFleetClient,
            ),
        ):
            result = await disconnect_mt5_account(
                db,
                customer,
                account.id,
            )

        assert stopped == ["session-123"]
        assert result.status == MT5SessionStatus.DISCONNECTED
        assert result.gateway_url is None
        assert result.gateway_port is None

        # A successful disconnect must not retain
        # the now-invalid Agent session identity.
        assert result.agent_session_id is None

    asyncio.run(scenario())
