import asyncio
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.models import BotTier
from app.mt5_fleet.models import MT5SessionStatus
from app.mt5_fleet.service import (
    connect_mt5_account,
    disconnect_mt5_account,
    reconnect_mt5_account,
)


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


def test_connect_without_start_stops_existing_runtime():
    async def scenario():
        account_id = uuid.uuid4()

        account = SimpleNamespace(
            id=account_id,
            broker_login="53054439",
            server_name="ICMarketsSC-Demo",
            currency="USD",
            equity_usd=0,
            bot_tier=BotTier.INELIGIBLE,
            route_reason="",
            status=None,
            last_synced_at=None,
        )

        broker = SimpleNamespace(
            slug="ic-markets",
            display_name="IC Markets",
        )

        customer = SimpleNamespace(
            id=uuid.uuid4(),
        )

        credential = SimpleNamespace(
            encrypted_password="old-encrypted",
            key_version=1,
        )

        session = SimpleNamespace(
            agent_session_id="session-123",
            agent_url="http://127.0.0.1:8180",
            gateway_url="http://127.0.0.1:8200",
            gateway_port=8200,
            terminal_instance=(
                r"C:\Abutron\MT5\accounts\account-1"
            ),
            broker_login="53054439",
            server_name="ICMarketsSC-Demo",
            status=MT5SessionStatus.RUNNING,
            last_error=None,
            last_health_at=None,
        )

        class FakeConnectDB:
            def __init__(self):
                self.scalar_results = [
                    credential,
                    session,
                ]
                self.added = []
                self.commits = 0
                self.refreshes = 0

            async def scalar(self, statement):
                return self.scalar_results.pop(0)

            def add(self, value):
                self.added.append(value)

            async def commit(self):
                self.commits += 1

            async def refresh(self, value):
                self.refreshes += 1

        class FakeFleetClient:
            def __init__(self, base_url, token):
                pass

            async def verify(self, request):
                return SimpleNamespace(
                    verified=True,
                    login="53054439",
                    server="ICMarketsSC-Demo",
                    currency="USD",
                    equity="100.00",
                )

            async def start(self, request):
                raise AssertionError(
                    "start must not be called when "
                    "start_session=False"
                )

            async def stop(self, session_id):
                stopped.append(session_id)

        class FakeVault:
            def __init__(self, key, version):
                pass

            def encrypt(self, value):
                return "encrypted-test-password"

        request = SimpleNamespace(
            trading_account_id=account_id,
            login="53054439",
            server="ICMarketsSC-Demo",
            password=SimpleNamespace(
                get_secret_value=lambda: "test-only"
            ),
            start_session=False,
        )

        fake_settings = SimpleNamespace(
            mt5_fleet_enabled=True,
            mt5_fleet_agent_url="http://127.0.0.1:8180",
            mt5_fleet_agent_token="test-token",
            mt5_credential_key="test-key",
            mt5_credential_key_version=1,
            mt5_allowed_broker_slugs=["ic-markets"],
        )

        decision = SimpleNamespace(
            tier=BotTier.FLIPPER,
            reason="test-route",
            eligible=True,
        )

        db = FakeConnectDB()
        stopped = []

        with (
            patch(
                "app.mt5_fleet.service.settings",
                fake_settings,
            ),
            patch(
                "app.mt5_fleet.service."
                "owned_ic_markets_account",
                new=AsyncMock(
                    return_value=(account, broker)
                ),
            ),
            patch(
                "app.mt5_fleet.service.MT5FleetClient",
                FakeFleetClient,
            ),
            patch(
                "app.mt5_fleet.service.CredentialVault",
                FakeVault,
            ),
            patch(
                "app.mt5_fleet.service.select_bot",
                return_value=decision,
            ),
        ):
            result = await connect_mt5_account(
                db,
                customer,
                request,
            )

        assert result.session.status == (
            MT5SessionStatus.DISCONNECTED
        )

        # If a runtime already exists, a no-start connect
        # must stop it before recording disconnected state.
        assert stopped == ["session-123"]

        assert session.agent_session_id is None
        assert session.gateway_url is None
        assert session.gateway_port is None
        assert session.terminal_instance is None
        assert session.last_error is None

    asyncio.run(scenario())


def test_connect_without_start_stop_failure_preserves_runtime_identity():
    from fastapi import HTTPException

    from app.mt5_fleet.client import MT5FleetClientError

    async def scenario():
        account_id = uuid.uuid4()

        account = SimpleNamespace(
            id=account_id,
            broker_login="53054439",
            server_name="ICMarketsSC-Demo",
            currency="USD",
            equity_usd=0,
            bot_tier=BotTier.INELIGIBLE,
            route_reason="",
            status=None,
            last_synced_at=None,
        )

        broker = SimpleNamespace(
            slug="ic-markets",
            display_name="IC Markets",
        )

        customer = SimpleNamespace(
            id=uuid.uuid4(),
        )

        credential = SimpleNamespace(
            encrypted_password="old-encrypted",
            key_version=1,
        )

        terminal = (
            r"C:\Abutron\MT5\accounts\account-1"
        )

        session = SimpleNamespace(
            agent_session_id="session-123",
            agent_url="http://127.0.0.1:8180",
            gateway_url="http://127.0.0.1:8200",
            gateway_port=8200,
            terminal_instance=terminal,
            broker_login="53054439",
            server_name="ICMarketsSC-Demo",
            status=MT5SessionStatus.RUNNING,
            last_error=None,
            last_health_at=None,
        )

        class FakeConnectDB:
            def __init__(self):
                self.scalar_results = [
                    credential,
                    session,
                ]
                self.added = []
                self.commits = 0
                self.refreshes = 0

            async def scalar(self, statement):
                return self.scalar_results.pop(0)

            def add(self, value):
                self.added.append(value)

            async def commit(self):
                self.commits += 1

            async def refresh(self, value):
                self.refreshes += 1

        stopped = []

        class FakeFleetClient:
            def __init__(self, base_url, token):
                pass

            async def verify(self, request):
                return SimpleNamespace(
                    verified=True,
                    login="53054439",
                    server="ICMarketsSC-Demo",
                    currency="USD",
                    equity="100.00",
                )

            async def start(self, request):
                raise AssertionError(
                    "start must not be called when "
                    "start_session=False"
                )

            async def stop(self, session_id):
                stopped.append(session_id)

                raise MT5FleetClientError(
                    "forced stop failure"
                )

        class FakeVault:
            def __init__(self, key, version):
                pass

            def encrypt(self, value):
                return "encrypted-test-password"

        request = SimpleNamespace(
            trading_account_id=account_id,
            login="53054439",
            server="ICMarketsSC-Demo",
            password=SimpleNamespace(
                get_secret_value=lambda: "test-only"
            ),
            start_session=False,
        )

        fake_settings = SimpleNamespace(
            mt5_fleet_enabled=True,
            mt5_fleet_agent_url="http://127.0.0.1:8180",
            mt5_fleet_agent_token="test-token",
            mt5_credential_key="test-key",
            mt5_credential_key_version=1,
            mt5_allowed_broker_slugs=["ic-markets"],
        )

        decision = SimpleNamespace(
            tier=BotTier.FLIPPER,
            reason="test-route",
            eligible=True,
        )

        db = FakeConnectDB()
        caught = None

        with (
            patch(
                "app.mt5_fleet.service.settings",
                fake_settings,
            ),
            patch(
                "app.mt5_fleet.service."
                "owned_ic_markets_account",
                new=AsyncMock(
                    return_value=(account, broker)
                ),
            ),
            patch(
                "app.mt5_fleet.service.MT5FleetClient",
                FakeFleetClient,
            ),
            patch(
                "app.mt5_fleet.service.CredentialVault",
                FakeVault,
            ),
            patch(
                "app.mt5_fleet.service.select_bot",
                return_value=decision,
            ),
        ):
            try:
                await connect_mt5_account(
                    db,
                    customer,
                    request,
                )
            except HTTPException as exc:
                caught = exc

        assert stopped == ["session-123"]

        assert caught is not None
        assert caught.status_code == 502

        # Fail closed: if Agent stop failed, the backend
        # must preserve the runtime identity rather than
        # pretending that the session is disconnected.
        assert session.status == MT5SessionStatus.ERROR
        assert session.agent_session_id == "session-123"

        assert (
            session.gateway_url
            == "http://127.0.0.1:8200"
        )

        assert session.gateway_port == 8200
        assert session.terminal_instance == terminal

        assert session.last_error == (
            "forced stop failure"
        )

        assert db.commits >= 1

    asyncio.run(scenario())


def test_reconnect_maps_agent_failure_to_502():
    from fastapi import HTTPException

    from app.mt5_fleet.client import MT5FleetClientError

    async def scenario():
        account_id = uuid.uuid4()

        account = SimpleNamespace(
            id=account_id,
            broker_login="53054439",
            server_name="ICMarketsSC-Demo",
        )

        customer = SimpleNamespace(
            id=uuid.uuid4(),
        )

        credential = SimpleNamespace(
            encrypted_password="encrypted-test",
            key_version=1,
        )

        class FakeReconnectDB:
            async def scalar(self, statement):
                return credential

        class FakeVault:
            def __init__(self, key, version):
                pass

            def decrypt(self, value):
                return "test-only-password"

        class FakeFleetClient:
            def __init__(self, base_url, token):
                pass

            async def start(self, request):
                raise MT5FleetClientError(
                    "forced reconnect failure"
                )

        fake_settings = SimpleNamespace(
            mt5_fleet_enabled=True,
            mt5_fleet_agent_url=(
                "http://127.0.0.1:8180"
            ),
            mt5_fleet_agent_token="test-token",
            mt5_credential_key="test-key",
            mt5_allowed_broker_slugs=[
                "ic-markets"
            ],
        )

        caught = None

        with (
            patch(
                "app.mt5_fleet.service.settings",
                fake_settings,
            ),
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
                "app.mt5_fleet.service."
                "CredentialVault",
                FakeVault,
            ),
            patch(
                "app.mt5_fleet.service."
                "MT5FleetClient",
                FakeFleetClient,
            ),
        ):
            try:
                await reconnect_mt5_account(
                    FakeReconnectDB(),
                    customer,
                    account_id,
                )
            except HTTPException as exc:
                caught = exc

        assert caught is not None
        assert caught.status_code == 502
        assert caught.detail == (
            "forced reconnect failure"
        )

    asyncio.run(scenario())
