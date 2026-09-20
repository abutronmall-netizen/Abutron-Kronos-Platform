import uuid

from app.mt5_fleet.schemas import AgentStartRequest, MT5ConnectRequest


def test_connect_request_keeps_password_secret():
    request = MT5ConnectRequest(trading_account_id=uuid.uuid4(), login="53054439", server="ICMarketsSC-Demo", password="secret-password")
    assert request.password.get_secret_value() == "secret-password"
    assert "secret-password" not in repr(request)


def test_agent_request_contract():
    request = AgentStartRequest(account_id=uuid.uuid4(), login="53054439", server="ICMarketsSC-Demo", password="secret-password")
    assert request.login == "53054439"
    assert request.server == "ICMarketsSC-Demo"
