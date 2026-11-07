
import pytest

from app.services.cost_calculator import (
    calculate_proportional_cost_cents,
)


def test_cost_of_4g_from_1kg_purchase():
    result = calculate_proportional_cost_cents(
        8500,
        1_000_000,
        4000,
    )

    assert result == 34


def test_cost_of_100g_from_1kg_purchase():
    result = calculate_proportional_cost_cents(
        8500,
        1_000_000,
        100_000,
    )

    assert result == 850


def test_zero_consumption_has_zero_cost():
    result = calculate_proportional_cost_cents(
        8500,
        1_000_000,
        0,
    )

    assert result == 0


def test_zero_purchased_quantity_is_invalid():
    with pytest.raises(ValueError):
        calculate_proportional_cost_cents(8500, 0, 4000)
