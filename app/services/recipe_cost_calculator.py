
from fractions import Fraction

from app.services.recipe_service import get_recipe
from app.services.stock_service import get_stock_valuation


def _round_fraction(value):
    """Arredonda uma fração para o inteiro mais próximo, meio para cima."""

    if value < 0:
        return -_round_fraction(-value)

    return (2 * value.numerator + value.denominator) // (
        2 * value.denominator
    )


def calculate_recipe_cost(recipe_id, version_number=None):
    """
    Calcula o custo estimado de uma versão da receita.

    Utiliza o custo médio atual dos materiais em estoque.
    Não registra movimentações.
    """

    recipe = get_recipe(recipe_id)

    if recipe is None:
        raise ValueError("Receita não encontrada.")

    versions = recipe["versions"]

    if version_number is None:
        if not versions:
            raise ValueError("A receita não possui versões.")

        version = versions[-1]
    else:
        version = next(
            (
                item for item in versions
                if item["version_number"] == version_number
            ),
            None,
        )

    if version is None:
        raise ValueError("Versão da receita não encontrada.")

    items = version["items"]

    if not items:
        raise ValueError("A receita está sem materiais.")

    total_cost = Fraction(0)
    item_results = []

    for item in items:
        valuation = get_stock_valuation(
            "material",
            item["material_id"],
        )

        if valuation["quantity_milli"] <= 0:
            raise ValueError(
                f"Material sem estoque disponível: "
                f"{item['material_name_snapshot']}."
            )

        exact_cost = (
            valuation["average_cost_cents_per_milli"]
            * item["quantity_milli"]
        )

        total_cost += exact_cost

        item_results.append({
            "material_id": item["material_id"],
            "material_name": item["material_name_snapshot"],
            "quantity_milli": item["quantity_milli"],
            "unit_symbol": item["unit_symbol_snapshot"],
            "stock_quantity_milli": valuation["quantity_milli"],
            "average_cost_cents_per_milli": (
                valuation["average_cost_cents_per_milli"]
            ),
            "cost_cents": _round_fraction(exact_cost),
        })

    return {
        "recipe_id": recipe_id,
        "recipe_name": recipe["name"],
        "version_number": version["version_number"],
        "items": item_results,
        "total_cost_cents": _round_fraction(total_cost),
    }
