
from fractions import Fraction

from app.database.connection import get_connection
from app.services.recipe_service import get_recipe
from app.services.stock_service import (
    _get_balances,
    _register_stock_movement,
    get_stock_balance,
)


def _validate_production_quantity(quantity):
    """Aceita somente quantidades inteiras e positivas."""

    if (
        not isinstance(quantity, int)
        or isinstance(quantity, bool)
        or quantity <= 0
    ):
        raise ValueError(
            "A quantidade produzida deve ser um número inteiro maior que zero."
        )


def calculate_required_materials(recipe_id, quantity, version_number=None):
    """
    Calcula os materiais necessários para produzir um lote.

    Não altera estoque nem registra movimentações.
    """

    _validate_production_quantity(quantity)

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

    if version["finalized_at"] is None:
        raise ValueError("A versão da receita ainda não foi finalizada.")

    items = version["items"]

    if not items:
        raise ValueError("A receita não possui materiais.")

    required_materials = []

    for item in items:
        required_quantity = (
            item["quantity_milli"] * quantity
        )

        required_materials.append({
            "material_id": item["material_id"],
            "material_name": item["material_name_snapshot"],
            "quantity_milli": required_quantity,
            "unit_symbol": item["unit_symbol_snapshot"],
        })

    return {
        "recipe_id": recipe_id,
        "recipe_name": recipe["name"],
        "version_number": version["version_number"],
        "production_quantity": quantity,
        "materials": required_materials,
    }

def check_production_stock(required_materials):
    """Verifica se há estoque suficiente para todos os materiais."""

    shortages = []
    stock_check = []

    for material in required_materials:
        available = get_stock_balance(
            "material",
            material["material_id"],
        )

        required = material["quantity_milli"]

        item_result = {
            **material,
            "available_quantity_milli": available,
            "sufficient": available >= required,
        }

        stock_check.append(item_result)

        if available < required:
            shortages.append(item_result)

    return {
        "sufficient": len(shortages) == 0,
        "items": stock_check,
        "shortages": shortages,
    }

def _validate_production_data(
    connection,
    product_id,
    recipe_id,
    version_number=None,
):
    """Valida produto, receita e versão dentro da transação."""

    product = connection.execute(
        """
        SELECT id, name
        FROM products
        WHERE id = ? AND active = 1
        """,
        (product_id,),
    ).fetchone()

    if product is None:
        raise ValueError("Produto não encontrado ou inativo.")

    recipe = connection.execute(
        """
        SELECT id, product_id, name, active
        FROM product_recipes
        WHERE id = ?
        """,
        (recipe_id,),
    ).fetchone()

    if recipe is None or not recipe["active"]:
        raise ValueError("Receita não encontrada ou inativa.")

    if recipe["product_id"] != product_id:
        raise ValueError("A receita não pertence ao produto informado.")

    if version_number is None:
        version = connection.execute(
            """
            SELECT id, version_number, finalized_at
            FROM recipe_versions
            WHERE recipe_id = ?
            ORDER BY version_number DESC
            LIMIT 1
            """,
            (recipe_id,),
        ).fetchone()
    else:
        version = connection.execute(
            """
            SELECT id, version_number, finalized_at
            FROM recipe_versions
            WHERE recipe_id = ? AND version_number = ?
            """,
            (recipe_id, version_number),
        ).fetchone()

    if version is None:
        raise ValueError("Versão da receita não encontrada.")

    if version["finalized_at"] is None:
        raise ValueError("A versão da receita ainda não foi finalizada.")

    items = connection.execute(
        """
        SELECT
            material_id,
            quantity_milli,
            material_name_snapshot,
            unit_symbol_snapshot
        FROM recipe_items
        WHERE recipe_version_id = ?
        ORDER BY material_name_snapshot
        """,
        (version["id"],),
    ).fetchall()

    if not items:
        raise ValueError("A receita não possui materiais.")

    return {
        "product": dict(product),
        "recipe": dict(recipe),
        "version": dict(version),
        "items": [dict(item) for item in items],
    }

def _calculate_production_materials(
    connection,
    recipe_items,
    production_quantity,
):
    """Calcula quantidades e custos dos materiais dentro da transação."""

    materials = []
    total_cost = Fraction(0)
    shortages = []

    for item in recipe_items:
        required_quantity = (
            item["quantity_milli"] * production_quantity
        )

        balances = _get_balances(
            connection,
            "material_id",
            item["material_id"],
        )

        available_quantity = balances["quantity_milli"]
        available_value = balances["value_cents"]

        if available_quantity < required_quantity:
            shortages.append({
                "material_id": item["material_id"],
                "material_name": item["material_name_snapshot"],
                "required_quantity_milli": required_quantity,
                "available_quantity_milli": available_quantity,
                "unit_symbol": item["unit_symbol_snapshot"],
            })
            continue

        if available_quantity <= 0:
            raise ValueError(
                f"Material sem estoque disponível: "
                f"{item['material_name_snapshot']}."
            )

        average_cost = Fraction(
            available_value,
            available_quantity,
        )

        exact_cost = average_cost * required_quantity

        total_cost += exact_cost

        materials.append({
            "material_id": item["material_id"],
            "material_name": item["material_name_snapshot"],
            "quantity_milli": required_quantity,
            "unit_symbol": item["unit_symbol_snapshot"],
            "exact_cost_cents": exact_cost,
        })

    if shortages:
        raise ValueError(
            f"Estoque insuficiente para produzir. "
            f"Materiais com saldo insuficiente: "
            f"{', '.join(item['material_name'] for item in shortages)}."
        )

    return {
        "materials": materials,
        "total_cost_exact_cents": total_cost,
    }

def register_production(
    product_id,
    recipe_id,
    quantity,
    version_number=None,
    notes=None,
):
    """Registra uma produção completa em uma única transação."""

    _validate_production_quantity(quantity)

    connection = get_connection()

    try:
        connection.execute("BEGIN IMMEDIATE")

        data = _validate_production_data(
            connection,
            product_id,
            recipe_id,
            version_number,
        )

        calculation = _calculate_production_materials(
            connection,
            data["items"],
            quantity,
        )

        cursor = connection.execute(
            """
            INSERT INTO productions (
                product_id,
                recipe_id,
                recipe_version_id,
                product_name_snapshot,
                recipe_name_snapshot,
                recipe_version_number,
                quantity_milli,
                total_cost_cents,
                notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)
            """,
            (
                product_id,
                recipe_id,
                data["version"]["id"],
                data["product"]["name"],
                data["recipe"]["name"],
                data["version"]["version_number"],
                quantity * 1_000_000,
                notes.strip() if notes and notes.strip() else None,
            ),
        )

        production_id = cursor.lastrowid
        total_cost_cents = 0

        for material in calculation["materials"]:
            movement_id = _register_stock_movement(
                connection=connection,
                item_type="material",
                item_id=material["material_id"],
                movement_type="production_consumption",
                quantity_milli=-material["quantity_milli"],
                reference_type="production",
                reference_id=production_id,
                notes=f"Consumo da produção #{production_id}",
            )

            movement = connection.execute(
                """
                SELECT value_cents
                FROM stock_movements
                WHERE id = ?
                """,
                (movement_id,),
            ).fetchone()

            material_cost = abs(movement["value_cents"])
            total_cost_cents += material_cost

            connection.execute(
                """
                INSERT INTO production_items (
                    production_id,
                    material_id,
                    quantity_milli,
                    total_cost_cents,
                    material_name_snapshot,
                    unit_symbol_snapshot
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    production_id,
                    material["material_id"],
                    material["quantity_milli"],
                    material_cost,
                    material["material_name"],
                    material["unit_symbol"],
                ),
            )

        connection.execute(
            """
            UPDATE productions
            SET total_cost_cents = ?
            WHERE id = ?
            """,
            (total_cost_cents, production_id),
        )

        _register_stock_movement(
            connection=connection,
            item_type="product",
            item_id=product_id,
            movement_type="production_output",
            quantity_milli=quantity * 1_000_000,
            reference_type="production",
            reference_id=production_id,
            notes=f"Entrada da produção #{production_id}",
            value_cents=total_cost_cents,
        )

        connection.commit()

        return production_id

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def list_productions():
    """Lista o histórico de produções, da mais recente para a mais antiga."""

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                product_name_snapshot,
                recipe_name_snapshot,
                recipe_version_number,
                quantity_milli,
                total_cost_cents,
                occurred_at,
                notes
            FROM productions
            ORDER BY occurred_at DESC, id DESC
            """
        ).fetchall()

        return [dict(row) for row in rows]
