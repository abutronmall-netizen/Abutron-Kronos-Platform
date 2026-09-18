import pytest

from app.models import BotTier
from app.services.bot_profiles import TradeFrequency, get_bot_profile


def test_flipper_profile_matches_cheat_sheet():
    profile = get_bot_profile(BotTier.FLIPPER)

    assert profile.core_style == "adaptive_directional_grid_basket"
    assert profile.primary_tf_flow == ("M15", "M5", "M1")
    assert profile.execution_timeframe == "M1"
    assert profile.trade_frequency == TradeFrequency.HIGH
    assert profile.directional_only is True
    assert profile.basket_execution is True


def test_scalper_profile_matches_cheat_sheet():
    profile = get_bot_profile(BotTier.SCALPER)

    assert profile.core_style == "precision_sniper_scalping"
    assert profile.primary_tf_flow == ("M15", "M5", "M1")
    assert profile.execution_timeframe == "M1"
    assert profile.trade_frequency == TradeFrequency.MEDIUM_HIGH
    assert profile.directional_only is True
    assert profile.basket_execution is False


def test_master_profile_matches_cheat_sheet():
    profile = get_bot_profile(BotTier.MASTER)

    assert profile.core_style == "day_trading_trend_smc_ict"
    assert profile.primary_tf_flow == ("H4", "H1", "M15", "M5")
    assert profile.execution_timeframe == "M5"
    assert profile.trade_frequency == TradeFrequency.LOW_SELECTIVE
    assert profile.directional_only is True
    assert profile.basket_execution is False
    assert profile.smc_ict_confirmation is True


def test_profile_payload_is_json_ready():
    payload = get_bot_profile(BotTier.MASTER).to_payload()

    assert payload["tier"] == "master"
    assert payload["profile_id"] == "master-v1"
    assert payload["profile_version"] == 1
    assert payload["primary_tf_flow"] == ["H4", "H1", "M15", "M5"]


def test_ineligible_tier_has_no_execution_profile():
    with pytest.raises(ValueError):
        get_bot_profile(BotTier.INELIGIBLE)
