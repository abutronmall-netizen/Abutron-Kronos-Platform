import pytest

from app.services.pricing import discounted_amount


def test_seventy_percent_discount():
    assert discounted_amount(500_000, 70) == 150_000


def test_no_discount():
    assert discounted_amount(330_000, 0) == 330_000


def test_full_discount():
    assert discounted_amount(1_000_000, 100) == 0


@pytest.mark.parametrize("discount", [-1, 101])
def test_invalid_discount_rejected(discount):
    with pytest.raises(ValueError):
        discounted_amount(100_000, discount)


def test_negative_price_rejected():
    with pytest.raises(ValueError):
        discounted_amount(-1, 70)
