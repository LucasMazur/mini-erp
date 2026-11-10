from app.database.connection import get_connection
from app.services.average_cost_calculator import (
    calculate_consumption_cost_cents,
)

MOVEMENT_RULES = {
    "purchase": ("material", 1),
    "production_consumption": ("material", -1),
    "production_output": ("product", 1),
    "sale": ("product", -1),
    "adjustment_in": (None, 1),
    "adjustment_out": (None, -1),
}


def _validate_item(item_type: str, item_id: int) -> None:
    if item_type not in ("material", "product"):
        raise ValueError("Tipo de item inválido.")

    table = "materials" if item_type == "material" else "products"

    with get_connection() as connection:
        item = connection.execute(
            f"SELECT id FROM {table} WHERE id = ? AND active = 1",
            (item_id,),
        ).fetchone()

    if item is None:
        raise ValueError("Material ou produto não encontrado ou inativo.")


def _get_balances(connection, item_column: str, item_id: int) -> dict:
    result = connection.execute(
        f"""
        SELECT
            COALESCE(SUM(quantity_milli), 0) AS quantity,
            COALESCE(SUM(value_cents), 0) AS value
        FROM stock_movements
        WHERE {item_column} = ?
        """,
        (item_id,),
    ).fetchone()

    return {
        "quantity_milli": result["quantity"],
        "value_cents": result["value"],
    }


def get_stock_balance(item_type: str, item_id: int) -> int:
    _validate_item(item_type, item_id)

    column = "material_id" if item_type == "material" else "product_id"

    with get_connection() as connection:
        balances = _get_balances(connection, column, item_id)

    return balances["quantity_milli"]


def get_stock_valuation(item_type: str, item_id: int) -> dict:
    """Retorna quantidade, valor financeiro e custo médio."""

    _validate_item(item_type, item_id)

    column = "material_id" if item_type == "material" else "product_id"

    with get_connection() as connection:
        balances = _get_balances(connection, column, item_id)

    quantity = balances["quantity_milli"]
    value = balances["value_cents"]

    if quantity == 0:
        average_cost = 0
    else:
        from fractions import Fraction
        average_cost = Fraction(value, quantity)

    return {
        "quantity_milli": quantity,
        "value_cents": value,
        "average_cost_cents_per_milli": average_cost,
    }



def _register_stock_movement(
    connection,
    item_type: str,
    item_id: int,
    movement_type: str,
    quantity_milli: int,
    reference_type: str | None = None,
    reference_id: int | None = None,
    notes: str | None = None,
    value_cents: int | None = None,
) -> int:
    """Registra uma movimentação usando uma conexão existente."""

    if movement_type not in MOVEMENT_RULES:
        raise ValueError("Tipo de movimentação inválido.")

    if item_type not in ("material", "product"):
        raise ValueError("Tipo de item inválido.")

    expected_item_type, expected_sign = MOVEMENT_RULES[movement_type]

    if expected_item_type is not None and item_type != expected_item_type:
        raise ValueError(
            "Esse tipo de movimentação não corresponde ao item informado."
        )

    if not isinstance(quantity_milli, int) or isinstance(quantity_milli, bool):
        raise TypeError("A quantidade deve ser um número inteiro.")

    if quantity_milli == 0:
        raise ValueError("A quantidade não pode ser zero.")

    if (quantity_milli > 0 and expected_sign < 0) or (
        quantity_milli < 0 and expected_sign > 0
    ):
        raise ValueError("O sinal da quantidade não corresponde à movimentação.")

    if value_cents is not None and (
        not isinstance(value_cents, int) or isinstance(value_cents, bool)
    ):
        raise ValueError("O valor financeiro deve ser um número inteiro.")

    column = "material_id" if item_type == "material" else "product_id"
    table = "materials" if item_type == "material" else "products"

    item = connection.execute(
        f"SELECT id FROM {table} WHERE id = ? AND active = 1",
        (item_id,),
    ).fetchone()

    if item is None:
        raise ValueError("Material ou produto não encontrado ou inativo.")

    balances = _get_balances(connection, column, item_id)

    current_quantity = balances["quantity_milli"]
    current_value = balances["value_cents"]
    new_quantity = current_quantity + quantity_milli

    if new_quantity < 0:
        raise ValueError(
            f"Estoque insuficiente. Saldo atual: {current_quantity} "
            f"milésimos; operação solicitada: "
            f"{abs(quantity_milli)} milésimos."
        )

    if quantity_milli > 0:
        if value_cents is None:
            raise ValueError(
                "Informe o valor financeiro da entrada em centavos."
            )

        if value_cents < 0:
            raise ValueError("O valor da entrada não pode ser negativo.")

        movement_value = value_cents

    else:
        if current_quantity <= 0:
            raise ValueError("Não existe estoque disponível.")

        movement_value = calculate_consumption_cost_cents(
            current_quantity,
            current_value,
            abs(quantity_milli),
        )
        movement_value = -movement_value

    new_value = current_value + movement_value

    if new_value < 0:
        raise ValueError("A operação deixaria o valor do estoque negativo.")

    if new_quantity == 0 and new_value != 0:
        movement_value = -current_value
        new_value = 0

    cursor = connection.execute(
        f"""
        INSERT INTO stock_movements (
            {column},
            movement_type,
            quantity_milli,
            value_cents,
            reference_type,
            reference_id,
            notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            item_id,
            movement_type,
            quantity_milli,
            movement_value,
            reference_type,
            reference_id,
            notes.strip() if notes and notes.strip() else None,
        ),
    )

    return cursor.lastrowid


def register_stock_movement(
    item_type: str,
    item_id: int,
    movement_type: str,
    quantity_milli: int,
    reference_type: str | None = None,
    reference_id: int | None = None,
    notes: str | None = None,
    value_cents: int | None = None,
) -> int:
    """Registra uma movimentação em sua própria transação."""

    connection = get_connection()

    try:
        connection.execute("BEGIN IMMEDIATE")

        movement_id = _register_stock_movement(
            connection=connection,
            item_type=item_type,
            item_id=item_id,
            movement_type=movement_type,
            quantity_milli=quantity_milli,
            reference_type=reference_type,
            reference_id=reference_id,
            notes=notes,
            value_cents=value_cents,
        )

        connection.commit()
        return movement_id

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def _reverse_stock_movement(
    connection,
    movement_id: int,
    notes: str | None = None,
) -> int:
    """Estorna uma movimentação usando uma conexão existente."""

    original = connection.execute(
        """
        SELECT *
        FROM stock_movements
        WHERE id = ?
        """,
        (movement_id,),
    ).fetchone()

    if original is None:
        raise ValueError("Movimentação não encontrada.")

    if original["movement_type"] == "reversal":
        raise ValueError("Não é permitido estornar um estorno.")

    if original["reversal_of_id"] is not None:
        raise ValueError("Essa movimentação já é um estorno.")

    existing = connection.execute(
        """
        SELECT id
        FROM stock_movements
        WHERE reversal_of_id = ?
        """,
        (movement_id,),
    ).fetchone()

    if existing is not None:
        raise ValueError("Essa movimentação já foi estornada.")

    item_column = (
        "material_id"
        if original["material_id"] is not None
        else "product_id"
    )

    item_id = original[item_column]
    reversal_quantity = -original["quantity_milli"]
    reversal_value = -original["value_cents"]

    balances = _get_balances(connection, item_column, item_id)

    new_quantity = balances["quantity_milli"] + reversal_quantity
    new_value = balances["value_cents"] + reversal_value

    if new_quantity < 0:
        raise ValueError(
            "Estorno não permitido: ele deixaria o estoque negativo."
        )

    if new_value < 0:
        raise ValueError(
            "Estorno não permitido: ele deixaria o valor do estoque negativo."
        )

    cursor = connection.execute(
        f"""
        INSERT INTO stock_movements (
            {item_column},
            movement_type,
            quantity_milli,
            value_cents,
            reference_type,
            reference_id,
            notes,
            reversal_of_id
        )
        VALUES (?, 'reversal', ?, ?, 'stock_movement', ?, ?, ?)
        """,
        (
            item_id,
            reversal_quantity,
            reversal_value,
            movement_id,
            notes.strip() if notes and notes.strip() else None,
            movement_id,
        ),
    )

    return cursor.lastrowid


def reverse_stock_movement(
    movement_id: int,
    notes: str | None = None,
) -> int:
    """Estorna quantidade e valor financeiro em sua própria transação."""

    connection = get_connection()

    try:
        connection.execute("BEGIN IMMEDIATE")

        reversal_id = _reverse_stock_movement(
            connection,
            movement_id,
            notes,
        )

        connection.commit()
        return reversal_id

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()
def list_stock_movements(
    item_type: str,
    item_id: int,
) -> list[dict]:
    """Lista o histórico de movimentações de um material ou produto."""

    if item_type not in ("material", "product"):
        raise ValueError("Tipo de item inválido.")

    column = "material_id" if item_type == "material" else "product_id"
    table = "materials" if item_type == "material" else "products"

    with get_connection() as connection:
        item = connection.execute(
            f"SELECT id FROM {table} WHERE id = ?",
            (item_id,),
        ).fetchone()

        if item is None:
            raise ValueError("Material ou produto não encontrado.")

        movements = connection.execute(
            f"""
            SELECT
                id,
                movement_type,
                quantity_milli,
                value_cents,
                occurred_at,
                reference_type,
                reference_id,
                notes,
                reversal_of_id,
                created_at
            FROM stock_movements
            WHERE {column} = ?
            ORDER BY occurred_at DESC, id DESC
            """,
            (item_id,),
        ).fetchall()

    return [dict(movement) for movement in movements]