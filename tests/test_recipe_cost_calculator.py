
from fractions import Fraction

import pytest

from app.services import recipe_cost_calculator


def test_calculate_recipe_cost(monkeypatch):
    recipe = {
        "id": 1,
        "name": "Brinco Lua",
        "versions": [
            {
                "version_number": 1,
                "items": [
                    {
                        "material_id": 10,
                        "material_name_snapshot": "PLA",
                        "unit_symbol_snapshot": "g",
                        "quantity_milli": 4000,
                    },
                    {
                        "material_id": 20,
                        "material_name_snapshot": "Argola",
                        "unit_symbol_snapshot": "un",
                        "quantity_milli": 2000,
                    },
                ],
            }
        ],
    }

    monkeypatch.setattr(
        recipe_cost_calculator,
        "get_recipe",
        lambda recipe_id: recipe,
    )

    def fake_get_stock_valuation(item_type, item_id):
        if item_id == 10:
            return {
                "quantity_milli": 1_000_000,
                "value_cents": 8500,
                "average_cost_cents_per_milli": Fraction(8500, 1_000_000),
            }

        if item_id == 20:
            return {
                "quantity_milli": 10_000,
                "value_cents": 5000,
                "average_cost_cents_per_milli": Fraction(500, 1000),
            }

        raise ValueError("Material não encontrado.")

    monkeypatch.setattr(
        recipe_cost_calculator,
        "get_stock_valuation",
        fake_get_stock_valuation,
    )

    result = recipe_cost_calculator.calculate_recipe_cost(1)

    assert result["recipe_name"] == "Brinco Lua"
    assert result["version_number"] == 1
    assert result["total_cost_cents"] == 1034
    assert len(result["items"]) == 2
    assert result["items"][0]["cost_cents"] == 34
    assert result["items"][1]["cost_cents"] == 1000


def test_recipe_not_found(monkeypatch):
    monkeypatch.setattr(
        recipe_cost_calculator,
        "get_recipe",
        lambda recipe_id: None,
    )

    with pytest.raises(ValueError, match="Receita não encontrada"):
        recipe_cost_calculator.calculate_recipe_cost(999)


def test_recipe_without_materials(monkeypatch):
    recipe = {
        "id": 1,
        "name": "Brinco Lua",
        "versions": [
            {
                "version_number": 1,
                "items": [],
            }
        ],
    }

    monkeypatch.setattr(
        recipe_cost_calculator,
        "get_recipe",
        lambda recipe_id: recipe,
    )

    with pytest.raises(ValueError, match="sem materiais"):
        recipe_cost_calculator.calculate_recipe_cost(1)


def test_material_without_stock(monkeypatch):
    recipe = {
        "id": 1,
        "name": "Brinco Lua",
        "versions": [
            {
                "version_number": 1,
                "items": [
                    {
                        "material_id": 10,
                        "material_name_snapshot": "PLA",
                        "unit_symbol_snapshot": "g",
                        "quantity_milli": 4000,
                    }
                ],
            }
        ],
    }

    monkeypatch.setattr(
        recipe_cost_calculator,
        "get_recipe",
        lambda recipe_id: recipe,
    )

    monkeypatch.setattr(
        recipe_cost_calculator,
        "get_stock_valuation",
        lambda item_type, item_id: {
            "quantity_milli": 0,
            "value_cents": 0,
            "average_cost_cents_per_milli": Fraction(0),
        },
    )

    with pytest.raises(ValueError, match="sem estoque"):
        recipe_cost_calculator.calculate_recipe_cost(1)
