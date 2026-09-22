import asyncio
import uuid
from unittest.mock import patch

import httpx
import pytest

from app.mt5_fleet.client import (
    MT5FleetClient,
    MT5FleetClientError,
)
from app.mt5_fleet.schemas import AgentStartRequest


class TimeoutAsyncClient:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(
        self,
        exc_type,
        exc,
        traceback,
    ):
        return False

    async def post(self, *args, **kwargs):
        raise httpx.ReadTimeout(
            "forced timeout"
        )

    async def get(self, *args, **kwargs):
        raise httpx.ReadTimeout(
            "forced timeout"
        )


def make_request():
    return AgentStartRequest(
        account_id=uuid.uuid4(),
        login="53054439",
        server="ICMarketsSC-Demo",
        password="test-only-password",
    )


def test_start_maps_timeout_to_fleet_error():
    async def scenario():
        client = MT5FleetClient(
            "http://127.0.0.1:8180",
            "test-token",
        )

        with patch(
            "app.mt5_fleet.client.httpx.AsyncClient",
            TimeoutAsyncClient,
        ), pytest.raises(
            MT5FleetClientError,
            match="MT5 session start timed out",
        ):
            await client.start(make_request())

    asyncio.run(scenario())


def test_stop_maps_timeout_to_fleet_error():
    async def scenario():
        client = MT5FleetClient(
            "http://127.0.0.1:8180",
            "test-token",
        )

        with patch(
            "app.mt5_fleet.client.httpx.AsyncClient",
            TimeoutAsyncClient,
        ), pytest.raises(
            MT5FleetClientError,
            match="MT5 session stop timed out",
        ):
            await client.stop("session-123")

    asyncio.run(scenario())


def test_status_maps_timeout_to_fleet_error():
    async def scenario():
        client = MT5FleetClient(
            "http://127.0.0.1:8180",
            "test-token",
        )

        with patch(
            "app.mt5_fleet.client.httpx.AsyncClient",
            TimeoutAsyncClient,
        ), pytest.raises(
            MT5FleetClientError,
            match="MT5 session status timed out",
        ):
            await client.status("session-123")

    asyncio.run(scenario())


class RequestErrorAsyncClient:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(
        self,
        exc_type,
        exc,
        traceback,
    ):
        return False

    @staticmethod
    def _error():
        return httpx.ConnectError(
            "forced unavailable",
            request=httpx.Request(
                "GET",
                "http://127.0.0.1:8180",
            ),
        )

    async def post(self, *args, **kwargs):
        raise self._error()

    async def get(self, *args, **kwargs):
        raise self._error()


def test_start_maps_request_error_to_fleet_error():
    async def scenario():
        client = MT5FleetClient(
            "http://127.0.0.1:8180",
            "test-token",
        )

        with patch(
            "app.mt5_fleet.client.httpx.AsyncClient",
            RequestErrorAsyncClient,
        ), pytest.raises(
            MT5FleetClientError,
            match="MT5 fleet agent unavailable",
        ):
            await client.start(make_request())

    asyncio.run(scenario())


def test_stop_maps_request_error_to_fleet_error():
    async def scenario():
        client = MT5FleetClient(
            "http://127.0.0.1:8180",
            "test-token",
        )

        with patch(
            "app.mt5_fleet.client.httpx.AsyncClient",
            RequestErrorAsyncClient,
        ), pytest.raises(
            MT5FleetClientError,
            match="MT5 fleet agent unavailable",
        ):
            await client.stop("session-123")

    asyncio.run(scenario())


def test_status_maps_request_error_to_fleet_error():
    async def scenario():
        client = MT5FleetClient(
            "http://127.0.0.1:8180",
            "test-token",
        )

        with patch(
            "app.mt5_fleet.client.httpx.AsyncClient",
            RequestErrorAsyncClient,
        ), pytest.raises(
            MT5FleetClientError,
            match="MT5 fleet agent unavailable",
        ):
            await client.status("session-123")

    asyncio.run(scenario())
