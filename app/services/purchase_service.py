
from fractions import Fraction

from app.database.connection import get_connection
from app.services.stock_service import _register_stock_movement


def _validate_non_negative_integer(value, field_name):
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{field_name} deve ser um inteiro não negativo.")


def _round_fraction(value: Fraction) -> int:
    """Arredonda uma fração para o inteiro mais próximo, meio para cima."""
    quotient, remainder = divmod(value.numerator, value.denominator)

    if remainder * 2 >= value.denominator:
        return quotient + 1

    return quotient


def _allocate_amount(total: int, weights: list[int]) -> list[int]:
    """Distribui centavos proporcionalmente, sem perder valores residuais."""

    weight_sum = sum(weights)

    if weight_sum == 0:
        if total != 0:
            raise ValueError(
                "Não é possível ratear valores quando o total dos itens é zero."
            )
        return [0] * len(weights)

    exact_values = [
        Fraction(total * weight, weight_sum)
        for weight in weights
    ]

    allocations = [
        value.numerator // value.denominator
        for value in exact_values
    ]

    remaining = total - sum(allocations)

    order = sorted(
        range(len(weights)),
        key=lambda index: (
            exact_values[index] - allocations[index],
            -index,
        ),
        reverse=True,
    )

    for index in order[:remaining]:
        allocations[index] += 1

    return allocations


def _convert_quantity_milli(
    quantity_milli: int,
    from_unit,
    to_unit,
) -> int:
    """Converte milésimos da unidade informada para a unidade do estoque."""

    if from_unit["dimension"] != to_unit["dimension"]:
        raise ValueError(
            "A unidade da compra é incompatível com a unidade do material."
        )

    quantity = Fraction(quantity_milli, 1000)

    source_factor = Fraction(
        from_unit["factor_num"],
        from_unit["factor_den"],
    )

    target_factor = Fraction(
        to_unit["factor_num"],
        to_unit["factor_den"],
    )

    converted = quantity * source_factor / target_factor
    converted_milli = converted * 1000

    if converted_milli.denominator != 1:
        raise ValueError(
            "A conversão resulta em uma quantidade menor que "
            "a precisão de milésimos permitida pelo estoque."
        )

    return converted_milli.numerator


def create_purchase(
    purchase_date: str,
    items: list[dict],
    supplier_id: int | None = None,
    invoice_number: str | None = None,
    freight_cents: int = 0,
    discount_cents: int = 0,
    notes: str | None = None,
) -> int:
    """Registra uma compra e suas entradas de estoque atomicamente."""

    if not isinstance(purchase_date, str) or not purchase_date.strip():
        raise ValueError("A data da compra é obrigatória.")

    if not isinstance(items, list) or not items:
        raise ValueError("A compra deve possuir pelo menos um item.")

    _validate_non_negative_integer(freight_cents, "O frete")
    _validate_non_negative_integer(discount_cents, "O desconto")

    connection = get_connection()

    try:
        connection.execute("BEGIN IMMEDIATE")

        if supplier_id is not None:
            supplier = connection.execute(
                """
                SELECT id
                FROM suppliers
                WHERE id = ? AND active = 1
                """,
                (supplier_id,),
            ).fetchone()

            if supplier is None:
                raise ValueError("Fornecedor não encontrado ou inativo.")

        prepared_items = []

        for item in items:
            material_id = item.get("material_id")
            unit_id = item.get("unit_id")
            quantity_milli = item.get("quantity_milli")
            line_total_cents = item.get("line_total_cents")

            if not isinstance(material_id, int) or isinstance(material_id, bool):
                raise TypeError("ID do material inválido.")

            if not isinstance(unit_id, int) or isinstance(unit_id, bool):
                raise TypeError("ID da unidade inválido.")  

            if (
                not isinstance(quantity_milli, int)
                or isinstance(quantity_milli, bool)
                or quantity_milli <= 0
            ):
                raise ValueError("A quantidade deve ser um inteiro positivo.")

            _validate_non_negative_integer(
                line_total_cents,
                "O valor do item",
            )

            material = connection.execute(
                """
                SELECT
                    m.id,
                    m.name,
                    m.stock_unit_id,
                    u.symbol AS stock_unit_symbol,
                    u.dimension AS stock_dimension,
                    u.factor_num AS stock_factor_num,
                    u.factor_den AS stock_factor_den
                FROM materials m
                JOIN units u ON u.id = m.stock_unit_id
                WHERE m.id = ? AND m.active = 1 AND u.active = 1
                """,
                (material_id,),
            ).fetchone()

            if material is None:
                raise ValueError("Material não encontrado ou inativo.")

            purchase_unit = connection.execute(
                """
                SELECT id, name, symbol, dimension, factor_num, factor_den
                FROM units
                WHERE id = ? AND active = 1
                """,
                (unit_id,),
            ).fetchone()

            if purchase_unit is None:
                raise ValueError("Unidade da compra inválida ou inativa.")

            stock_unit = {
                "dimension": material["stock_dimension"],
                "factor_num": material["stock_factor_num"],
                "factor_den": material["stock_factor_den"],
            }

            stock_quantity_milli = _convert_quantity_milli(
                quantity_milli,
                dict(purchase_unit),
                stock_unit,
            )

            prepared_items.append({
                "material_id": material_id,
                "material_name": material["name"],
                "unit_id": unit_id,
                "unit_symbol": purchase_unit["symbol"],
                "quantity_milli": quantity_milli,
                "stock_quantity_milli": stock_quantity_milli,
                "line_total_cents": line_total_cents,
            })

        subtotal = sum(
            item["line_total_cents"]
            for item in prepared_items
        )

        if discount_cents > subtotal:
            raise ValueError(
                "O desconto não pode ser maior que o subtotal dos itens."
            )

        weights = [
            item["line_total_cents"]
            for item in prepared_items
        ]

        freight_allocations = _allocate_amount(
            freight_cents,
            weights,
        )

        discount_allocations = _allocate_amount(
            discount_cents,
            weights,
        )

        for index, item in enumerate(prepared_items):
            landed_cost = (
                item["line_total_cents"]
                + freight_allocations[index]
                - discount_allocations[index]
            )

            if landed_cost < 0:
                raise ValueError(
                    "O custo final de um item não pode ser negativo."
                )

            item["landed_cost_cents"] = landed_cost

            item["unit_cost_cents"] = _round_fraction(
                Fraction(
                    item["line_total_cents"] * 1000,
                    item["quantity_milli"],
                )
            )

        cursor = connection.execute(
            """
            INSERT INTO purchases (
                supplier_id,
                purchase_date,
                invoice_number,
                freight_cents,
                discount_cents,
                notes
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                supplier_id,
                purchase_date.strip(),
                invoice_number.strip() or None if invoice_number else None,
                freight_cents,
                discount_cents,
                notes.strip() or None if notes else None,
            ),
        )

        purchase_id = cursor.lastrowid

        total_expense_cents = subtotal + freight_cents - discount_cents
        if total_expense_cents > 0:
            connection.execute(
                """
                INSERT INTO financial_transactions (
                    transaction_date, direction, description,
                    amount_cents, category, origin, reference_id
                )
                VALUES (?, 'expense', ?, ?, 'Compras', 'purchase', ?)
                """,
                (
                    purchase_date.strip(),
                    f"Compra #{purchase_id}",
                    total_expense_cents,
                    purchase_id,
                ),
            )

        for item in prepared_items:
            connection.execute(
                """
                INSERT INTO purchase_items (
                    purchase_id,
                    material_id,
                    unit_id,
                    quantity_milli,
                    unit_cost_cents,
                    line_total_cents,
                    material_name_snapshot,
                    unit_symbol_snapshot,
                    landed_cost_cents
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    purchase_id,
                    item["material_id"],
                    item["unit_id"],
                    item["quantity_milli"],
                    item["unit_cost_cents"],
                    item["line_total_cents"],
                    item["material_name"],
                    item["unit_symbol"],
                    item["landed_cost_cents"],
                ),
            )

            _register_stock_movement(
                connection=connection,
                item_type="material",
                item_id=item["material_id"],
                movement_type="purchase",
                quantity_milli=item["stock_quantity_milli"],
                reference_type="purchase",
                reference_id=purchase_id,
                notes=f"Compra #{purchase_id}",
                value_cents=item["landed_cost_cents"],
            )

        connection.commit()
        return purchase_id

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def get_purchase(purchase_id: int) -> dict | None:
    """Consulta uma compra e seus itens pelo ID."""

    with get_connection() as connection:
        purchase = connection.execute(
            """
            SELECT
                p.*,
                s.name AS supplier_name,
                (
                    SELECT MAX(reversal.occurred_at)
                    FROM stock_movements original
                    JOIN stock_movements reversal
                        ON reversal.reversal_of_id = original.id
                    WHERE original.reference_type = 'purchase'
                      AND original.reference_id = p.id
                      AND original.movement_type = 'purchase'
                ) AS reversed_at
            FROM purchases p
            LEFT JOIN suppliers s ON s.id = p.supplier_id
            WHERE p.id = ?
            """,
            (purchase_id,),
        ).fetchone()

        if purchase is None:
            return None

        items = connection.execute(
            """
            SELECT *
            FROM purchase_items
            WHERE purchase_id = ?
            ORDER BY id
            """,
            (purchase_id,),
        ).fetchall()

        result = dict(purchase)
        result["items"] = [dict(item) for item in items]

        return result


def list_purchases(
    supplier_id: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    invoice_number: str | None = None,
) -> list[dict]:
    """Lista compras com filtros opcionais."""

    query = """
        SELECT
            p.*,
            s.name AS supplier_name,
            COUNT(pi.id) AS item_count,
            COALESCE(SUM(pi.line_total_cents), 0) AS subtotal_cents,
            COALESCE(SUM(pi.landed_cost_cents), 0) AS total_cost_cents,
            CASE
                WHEN EXISTS (
                    SELECT 1
                    FROM stock_movements original
                    WHERE original.reference_type = 'purchase'
                      AND original.reference_id = p.id
                      AND original.movement_type = 'purchase'
                )
                AND NOT EXISTS (
                    SELECT 1
                    FROM stock_movements original
                    WHERE original.reference_type = 'purchase'
                      AND original.reference_id = p.id
                      AND original.movement_type = 'purchase'
                      AND NOT EXISTS (
                          SELECT 1
                          FROM stock_movements reversal
                          WHERE reversal.reversal_of_id = original.id
                      )
                )
                THEN 1
                ELSE 0
            END AS is_reversed
        FROM purchases p
        LEFT JOIN suppliers s ON s.id = p.supplier_id
        LEFT JOIN purchase_items pi ON pi.purchase_id = p.id
        WHERE 1 = 1
    """

    parameters = []

    if supplier_id is not None:
        query += " AND p.supplier_id = ?"
        parameters.append(supplier_id)

    if start_date is not None:
        query += " AND p.purchase_date >= ?"
        parameters.append(start_date)

    if end_date is not None:
        query += " AND p.purchase_date <= ?"
        parameters.append(end_date)

    if invoice_number is not None:
        query += " AND p.invoice_number LIKE ?"
        parameters.append(f"%{invoice_number.strip()}%")

    query += """
        GROUP BY p.id
        ORDER BY p.purchase_date DESC, p.id DESC
    """

    with get_connection() as connection:
        purchases = connection.execute(
            query,
            parameters,
        ).fetchall()

        return [dict(purchase) for purchase in purchases]


from app.services.stock_service import _reverse_stock_movement


def reverse_purchase(
    purchase_id: int,
    notes: str | None = None,
) -> None:
    """Estorna uma compra inteira sem apagar seu histórico."""

    connection = get_connection()

    try:
        connection.execute("BEGIN IMMEDIATE")

        purchase = connection.execute(
            """
            SELECT
                p.*,
                s.name AS supplier_name,
                (
                    SELECT MAX(reversal.occurred_at)
                    FROM stock_movements original
                    JOIN stock_movements reversal
                        ON reversal.reversal_of_id = original.id
                    WHERE original.reference_type = 'purchase'
                      AND original.reference_id = p.id
                      AND original.movement_type = 'purchase'
                ) AS reversed_at
            FROM purchases p
            LEFT JOIN suppliers s ON s.id = p.supplier_id
            WHERE p.id = ?
            """,
            (purchase_id,),
        ).fetchone()

        if purchase is None:
            raise ValueError("Compra não encontrada.")

        movements = connection.execute(
            """
            SELECT id
            FROM stock_movements
            WHERE reference_type = 'purchase'
              AND reference_id = ?
              AND movement_type = 'purchase'
            ORDER BY id
            """,
            (purchase_id,),
        ).fetchall()

        if not movements:
            raise ValueError(
                "Nenhuma movimentação de estoque encontrada para essa compra."
            )

        for movement in movements:
            _reverse_stock_movement(
                connection,
                movement["id"],
                notes or f"Estorno da compra #{purchase_id}",
            )

        original_finance = connection.execute(
            """
            SELECT amount_cents
            FROM financial_transactions
            WHERE origin = 'purchase' AND reference_id = ?
            """,
            (purchase_id,),
        ).fetchone()
        if original_finance is not None:
            connection.execute(
                """
                INSERT INTO financial_transactions (
                    transaction_date, direction, description,
                    amount_cents, category, origin, reference_id
                )
                VALUES (date('now', 'localtime'), 'income', ?, ?,
                        'Estornos', 'purchase_reversal', ?)
                """,
                (
                    f"Estorno da compra #{purchase_id}",
                    original_finance["amount_cents"],
                    purchase_id,
                ),
            )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()
