from app.database.connection import get_connection


MOVEMENT_RULES = {
    "purchase": ("material", 1),
    "production_consumption": ("material", -1),
    "production_output": ("product", 1),
    "sale": ("product", -1),
    "adjustment_in": (None, 1),
    "adjustment_out": (None, -1),
}


def _validate_item(item_type: str, item_id: int) -> str:
    """Confere se o material ou produto existe e está ativo."""

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

    return table


def get_stock_balance(item_type: str, item_id: int) -> int:
    """Retorna o saldo em milésimos da unidade de estoque."""

    _validate_item(item_type, item_id)

    column = "material_id" if item_type == "material" else "product_id"

    with get_connection() as connection:
        result = connection.execute(
            f"""
            SELECT COALESCE(SUM(quantity_milli), 0) AS balance
            FROM stock_movements
            WHERE {column} = ?
            """,
            (item_id,),
        ).fetchone()

    return result["balance"]


def register_stock_movement(
    item_type: str,
    item_id: int,
    movement_type: str,
    quantity_milli: int,
    reference_type: str | None = None,
    reference_id: int | None = None,
    notes: str | None = None,
) -> int:
    """
    Registra uma movimentação e retorna seu ID.

    Entradas usam quantidades positivas.
    Saídas usam quantidades negativas.
    O saldo nunca pode ficar negativo.
    """

    if movement_type not in MOVEMENT_RULES:
        raise ValueError("Tipo de movimentação inválido.")

    expected_item_type, expected_sign = MOVEMENT_RULES[movement_type]

    if expected_item_type is not None and item_type != expected_item_type:
        raise ValueError(
            "Esse tipo de movimentação não corresponde ao item informado."
        )

    if not isinstance(quantity_milli, int) or isinstance(quantity_milli, bool):
        raise ValueError("A quantidade deve ser um número inteiro.")

    if quantity_milli == 0:
        raise ValueError("A quantidade não pode ser zero.")

    if (quantity_milli > 0 and expected_sign < 0) or (
        quantity_milli < 0 and expected_sign > 0
    ):
        raise ValueError("O sinal da quantidade não corresponde à movimentação.")

    column = "material_id" if item_type == "material" else "product_id"

    if item_type not in ("material", "product"):
        raise ValueError("Tipo de item inválido.")

    table = "materials" if item_type == "material" else "products"

    connection = get_connection()

    try:
        # Reserva a escrita antes de consultar o saldo.
        connection.execute("BEGIN IMMEDIATE")

        item = connection.execute(
            f"SELECT id FROM {table} WHERE id = ? AND active = 1",
            (item_id,),
        ).fetchone()

        if item is None:
            raise ValueError("Material ou produto não encontrado ou inativo.")

        current_balance = connection.execute(
            f"""
            SELECT COALESCE(SUM(quantity_milli), 0) AS balance
            FROM stock_movements
            WHERE {column} = ?
            """,
            (item_id,),
        ).fetchone()["balance"]

        new_balance = current_balance + quantity_milli

        if new_balance < 0:
            raise ValueError(
                f"Estoque insuficiente. Saldo atual: {current_balance} "
                f"milésimos; operação solicitada: "
                f"{abs(quantity_milli)} milésimos."
            )

        cursor = connection.execute(
            f"""
            INSERT INTO stock_movements (
                {column},
                movement_type,
                quantity_milli,
                reference_type,
                reference_id,
                notes
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                item_id,
                movement_type,
                quantity_milli,
                reference_type,
                reference_id,
                notes.strip() if notes and notes.strip() else None,
            ),
        )

        movement_id = cursor.lastrowid
        connection.commit()

        return movement_id

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

def reverse_stock_movement(
    movement_id: int,
    notes: str | None = None,
) -> int:
    """
    Estorna uma movimentação original sem apagar seu histórico.
    Uma movimentação só pode ser estornada uma vez.
    """

    connection = get_connection()

    try:
        connection.execute("BEGIN IMMEDIATE")

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

        existing_reversal = connection.execute(
            """
            SELECT id
            FROM stock_movements
            WHERE reversal_of_id = ?
            """,
            (movement_id,),
        ).fetchone()

        if existing_reversal is not None:
            raise ValueError("Essa movimentação já foi estornada.")

        item_column = (
            "material_id"
            if original["material_id"] is not None
            else "product_id"
        )

        item_id = original[item_column]
        reversal_quantity = -original["quantity_milli"]

        current_balance = connection.execute(
            f"""
            SELECT COALESCE(SUM(quantity_milli), 0) AS balance
            FROM stock_movements
            WHERE {item_column} = ?
            """,
            (item_id,),
        ).fetchone()["balance"]

        new_balance = current_balance + reversal_quantity

        if new_balance < 0:
            raise ValueError(
                "Estorno não permitido: ele deixaria o estoque negativo."
            )

        cursor = connection.execute(
            f"""
            INSERT INTO stock_movements (
                {item_column},
                movement_type,
                quantity_milli,
                reference_type,
                reference_id,
                notes,
                reversal_of_id
            )
            VALUES (?, 'reversal', ?, 'stock_movement', ?, ?, ?)
            """,
            (
                item_id,
                reversal_quantity,
                movement_id,
                notes.strip() if notes and notes.strip() else None,
                movement_id,
            ),
        )

        reversal_id = cursor.lastrowid
        connection.commit()

        return reversal_id

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()