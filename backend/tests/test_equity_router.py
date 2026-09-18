from decimal import Decimal

import pytest

from app.models import BotTier
from app.services.equity_router import select_bot


@pytest.mark.parametrize(
    ("equity", "eligible", "tier"),
    [
        ("0", False, BotTier.INELIGIBLE),
        ("19.99", False, BotTier.INELIGIBLE),
        ("20.00", True, BotTier.FLIPPER),
        ("3000.00", True, BotTier.FLIPPER),
        ("3000.01", True, BotTier.FLIPPER),
        ("3000.99", True, BotTier.FLIPPER),
        ("3001.00", True, BotTier.SCALPER),
        ("5000.00", True, BotTier.SCALPER),
        ("5000.99", True, BotTier.SCALPER),
        ("5001.00", True, BotTier.MASTER),
        ("10000.00", True, BotTier.MASTER),
        ("10000.01", False, BotTier.INELIGIBLE),
    ],
)
def test_equity_routing_boundaries(equity, eligible, tier):
    decision = select_bot(Decimal(equity))
    assert decision.eligible is eligible
    assert decision.tier == tier


def test_negative_equity_rejected():
    with pytest.raises(ValueError):
        select_bot("-0.01")
