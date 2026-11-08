import pytest
from fractions import Fraction

from app.services.average_cost_calculator import (
    calculate_weighted_average_cost,
    calculate_consumption_cost_cents,
)


def test_average_cost_of_two_purchases():
    average = calculate_weighted_average_cost(
        0, 0,
        1_000_000, 8_500,
    )

    average = calculate_weighted_average_cost(
        1_000_000, 8_500,
        1_000_000, 10_000,
    )

    assert average == Fraction(18500, 2000000)


def test_consumption_cost_from_average():
    cost = calculate_consumption_cost_cents(
        2_000_000,
        18_500,
        100_000,
    )

    assert cost == 925


def test_zero_stock_has_zero_average():
    average = calculate_weighted_average_cost(0, 0, 0, 0)

    assert average == 0


def test_cannot_have_value_without_stock():
    with pytest.raises(ValueError):
        calculate_weighted_average_cost(0, 100, 0, 0)


def test_consumption_cannot_exceed_stock():
    with pytest.raises(ValueError):
        calculate_consumption_cost_cents(1000, 500, 2000)


def test_negative_quantity_is_invalid():
    with pytest.raises(ValueError):
        calculate_weighted_average_cost(-100, 0, 0, 0)