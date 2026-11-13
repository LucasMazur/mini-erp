from fractions import Fraction

from app.database.connection import get_connection
from app.services.stock_service import (
    _get_balances,
    _register_stock_movement,
)

COMMISSION_TYPES = {"percentage", "fixed"}


def _validate_commission(commission_type, commission_value):
    if commission_type not in COMMISSION_TYPES:
        raise ValueError("Tipo de comissão inválido.")
    if (
        not isinstance(commission_value, int)
        or isinstance(commission_value, bool)
        or commission_value < 0
    ):
        raise ValueError("Informe uma comissão válida.")
    if commission_type == "percentage" and commission_value > 10000:
        raise ValueError("A comissão percentual não pode ultrapassar 100%.")


def create_seller(
    name,
    commission_type,
    commission_value,
    contact_name=None,
    phone=None,
    address=None,
    notes=None,
):
    name = (name or "").strip()
    if not name:
        raise ValueError("Informe o nome da loja.")
    _validate_commission(commission_type, commission_value)

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO sellers (
                name, contact_name, phone, address,
                commission_type, commission_value, notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                (contact_name or "").strip() or None,
                (phone or "").strip() or None,
                (address or "").strip() or None,
                commission_type,
                commission_value,
                (notes or "").strip() or None,
            ),
        )
        return cursor.lastrowid


def update_seller(seller_id, **values):
    allowed = {
        "name", "contact_name", "phone", "address",
        "commission_type", "commission_value", "notes", "active",
    }
    if not values or set(values) - allowed:
        raise ValueError("Dados de atualização inválidos.")
    if "name" in values:
        values["name"] = (values["name"] or "").strip()
        if not values["name"]:
            raise ValueError("Informe o nome da loja.")
    if "commission_type" in values or "commission_value" in values:
        with get_connection() as connection:
            current = connection.execute(
                "SELECT commission_type, commission_value FROM sellers WHERE id = ?",
                (seller_id,),
            ).fetchone()
        if current is None:
            raise ValueError("Loja não encontrada.")
        _validate_commission(
            values.get("commission_type", current["commission_type"]),
            values.get("commission_value", current["commission_value"]),
        )
    assignments = ", ".join(f"{key} = ?" for key in values)
    params = [
        (value.strip() or None) if key in {
            "contact_name", "phone", "address", "notes"
        } and isinstance(value, str) else value
        for key, value in values.items()
    ]
    with get_connection() as connection:
        cursor = connection.execute(
            f"UPDATE sellers SET {assignments} WHERE id = ?",
            (*params, seller_id),
        )
        if cursor.rowcount == 0:
            raise ValueError("Loja não encontrada.")


def list_sellers(include_inactive=False, search=""):
    sql = """
        SELECT s.*,
            COALESCE((
                SELECT SUM(si.delivered_quantity_milli
                           - si.sold_quantity_milli
                           - si.returned_quantity_milli)
                FROM consignment_items si
                JOIN consignments c ON c.id = si.consignment_id
                WHERE c.seller_id = s.id
            ), 0) AS custody_quantity_milli,
            COALESCE((
                SELECT SUM(cs.net_cents)
                FROM consignment_settlements cs
                JOIN consignments c ON c.id = cs.consignment_id
                WHERE c.seller_id = s.id
            ), 0) - COALESCE((
                SELECT SUM(cp.amount_cents)
                FROM consignment_payments cp
                JOIN consignments c ON c.id = cp.consignment_id
                WHERE c.seller_id = s.id
            ), 0) AS pending_cents
        FROM sellers s
        WHERE (? = 1 OR s.active = 1)
          AND s.name LIKE ?
        ORDER BY s.name
    """
    with get_connection() as connection:
        rows = connection.execute(
            sql, (1 if include_inactive else 0, f"%{search.strip()}%")
        ).fetchall()
    return [dict(row) for row in rows]


def create_consignment(seller_id, dispatch_date, items, notes=None):
    if not dispatch_date:
        raise ValueError("Informe a data da remessa.")
    if not items:
        raise ValueError("Adicione pelo menos um produto à remessa.")

    normalized = []
    seen = set()
    for item in items:
        product_id = item.get("product_id")
        quantity = item.get("quantity")
        if not isinstance(product_id, int) or isinstance(product_id, bool):
            raise ValueError("Produto inválido.")
        if (
            not isinstance(quantity, int) or isinstance(quantity, bool)
            or quantity <= 0
        ):
            raise ValueError("A quantidade deve ser um número inteiro positivo.")
        if product_id in seen:
            raise ValueError("Não repita o mesmo produto na remessa.")
        seen.add(product_id)
        normalized.append((product_id, quantity * 1_000_000))

    connection = get_connection()
    try:
        connection.execute("BEGIN IMMEDIATE")
        seller = connection.execute(
            "SELECT id FROM sellers WHERE id = ? AND active = 1",
            (seller_id,),
        ).fetchone()
        if seller is None:
            raise ValueError("Loja não encontrada ou inativa.")

        products = {}
        for product_id, quantity_milli in normalized:
            product = connection.execute(
                """
                SELECT p.id, p.name, p.sale_price_cents, u.symbol
                FROM products p
                JOIN units u ON u.id = p.stock_unit_id
                WHERE p.id = ? AND p.active = 1
                """,
                (product_id,),
            ).fetchone()
            if product is None:
                raise ValueError("Produto não encontrado ou inativo.")
            balances = _get_balances(connection, "product_id", product_id)
            if balances["quantity_milli"] < quantity_milli:
                raise ValueError(
                    f"Estoque insuficiente para {product['name']}."
                )
            if balances["quantity_milli"] <= 0:
                raise ValueError(f"Produto sem estoque: {product['name']}.")
            average_cost = Fraction(
                balances["value_cents"], balances["quantity_milli"]
            )
            unit_cost_cents = (
                average_cost.numerator * 1_000_000 * 2
                + average_cost.denominator
            ) // (2 * average_cost.denominator)
            products[product_id] = (dict(product), unit_cost_cents)

        cursor = connection.execute(
            """
            INSERT INTO consignments (seller_id, dispatch_date, notes)
            VALUES (?, ?, ?)
            """,
            (seller_id, dispatch_date, (notes or "").strip() or None),
        )
        consignment_id = cursor.lastrowid

        for product_id, quantity_milli in normalized:
            product, unit_cost_cents = products[product_id]
            if product["sale_price_cents"] is None:
                raise ValueError(
                    f"Cadastre o preço de venda de {product['name']} "
                    "antes de enviar à loja."
                )
            _register_stock_movement(
                connection,
                "product",
                product_id,
                "adjustment_out",
                -quantity_milli,
                reference_type="consignment",
                reference_id=consignment_id,
                notes=f"Remessa em consignação para loja #{seller_id}",
            )
            connection.execute(
                """
                INSERT INTO consignment_items (
                    consignment_id, product_id, product_name_snapshot,
                    unit_symbol_snapshot, delivered_quantity_milli,
                    unit_price_cents, unit_cost_cents_per_unit
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    consignment_id, product_id, product["name"],
                    product["symbol"], quantity_milli,
                    product["sale_price_cents"], unit_cost_cents,
                ),
            )
        connection.commit()
        return consignment_id
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def list_consignments(seller_id=None):
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT c.*, s.name AS seller_name,
                COALESCE(SUM(i.delivered_quantity_milli), 0) AS delivered_milli,
                COALESCE(SUM(i.sold_quantity_milli), 0) AS sold_milli,
                COALESCE(SUM(i.returned_quantity_milli), 0) AS returned_milli,
                COALESCE(SUM(
                    i.delivered_quantity_milli - i.sold_quantity_milli
                    - i.returned_quantity_milli
                ), 0) AS custody_milli
            FROM consignments c
            JOIN sellers s ON s.id = c.seller_id
            LEFT JOIN consignment_items i ON i.consignment_id = c.id
            WHERE (? IS NULL OR c.seller_id = ?)
            GROUP BY c.id
            ORDER BY c.dispatch_date DESC, c.id DESC
            """,
            (seller_id, seller_id),
        ).fetchall()
    return [dict(row) for row in rows]


def get_consignment(consignment_id):
    with get_connection() as connection:
        consignment = connection.execute(
            """
            SELECT c.*, s.name AS seller_name, s.commission_type,
                   s.commission_value
            FROM consignments c
            JOIN sellers s ON s.id = c.seller_id
            WHERE c.id = ?
            """,
            (consignment_id,),
        ).fetchone()
        if consignment is None:
            return None
        items = connection.execute(
            """
            SELECT *,
                delivered_quantity_milli - sold_quantity_milli
                    - returned_quantity_milli AS custody_quantity_milli
            FROM consignment_items
            WHERE consignment_id = ?
            ORDER BY product_name_snapshot
            """,
            (consignment_id,),
        ).fetchall()
        settlements = connection.execute(
            """
            SELECT * FROM consignment_settlements
            WHERE consignment_id = ? ORDER BY settlement_date, id
            """,
            (consignment_id,),
        ).fetchall()
        payments = connection.execute(
            """
            SELECT * FROM consignment_payments
            WHERE consignment_id = ? ORDER BY payment_date, id
            """,
            (consignment_id,),
        ).fetchall()
    result = dict(consignment)
    result["items"] = [dict(row) for row in items]
    result["settlements"] = [dict(row) for row in settlements]
    result["payments"] = [dict(row) for row in payments]
    result["pending_cents"] = (
        sum(row["net_cents"] for row in result["settlements"])
        - sum(row["amount_cents"] for row in result["payments"])
    )
    return result


def register_settlement(consignment_id, settlement_date, items, notes=None):
    if not settlement_date:
        raise ValueError("Informe a data do acerto.")
    if not items:
        raise ValueError("Adicione os produtos vendidos no acerto.")
    normalized = []
    seen = set()
    for item in items:
        item_id = item.get("consignment_item_id")
        quantity = item.get("quantity")
        if not isinstance(item_id, int) or isinstance(item_id, bool):
            raise ValueError("Item da remessa inválido.")
        if (
            not isinstance(quantity, int) or isinstance(quantity, bool)
            or quantity <= 0
        ):
            raise ValueError("A quantidade vendida deve ser positiva.")
        if item_id in seen:
            raise ValueError("Não repita o mesmo item no acerto.")
        seen.add(item_id)
        normalized.append((item_id, quantity * 1_000_000))

    connection = get_connection()
    try:
        connection.execute("BEGIN IMMEDIATE")
        consignment = connection.execute(
            """
            SELECT c.id, c.status, s.commission_type, s.commission_value
            FROM consignments c JOIN sellers s ON s.id = c.seller_id
            WHERE c.id = ?
            """,
            (consignment_id,),
        ).fetchone()
        if consignment is None or consignment["status"] != "open":
            raise ValueError("Remessa não encontrada ou encerrada.")

        lines = []
        gross = 0
        commission = 0
        for item_id, quantity_milli in normalized:
            item = connection.execute(
                """
                SELECT * FROM consignment_items
                WHERE id = ? AND consignment_id = ?
                """,
                (item_id, consignment_id),
            ).fetchone()
            if item is None:
                raise ValueError("Produto não pertence a essa remessa.")
            custody = (
                item["delivered_quantity_milli"]
                - item["sold_quantity_milli"]
                - item["returned_quantity_milli"]
            )
            if quantity_milli > custody:
                raise ValueError(
                    f"Quantidade vendida maior que o saldo em loja de "
                    f"{item['product_name_snapshot']}."
                )
            line_total = quantity_milli * item["unit_price_cents"] // 1_000_000
            if consignment["commission_type"] == "percentage":
                line_commission = (
                    line_total * consignment["commission_value"] // 1_000_0000
                )
            else:
                line_commission = (
                    quantity_milli // 1_000_000 * consignment["commission_value"]
                )
            gross += line_total
            commission += line_commission
            lines.append((
                item_id, quantity_milli, item["unit_price_cents"], line_total
            ))

        net = gross - commission
        if net < 0:
            raise ValueError("A comissão não pode superar o valor vendido.")
        cursor = connection.execute(
            """
            INSERT INTO consignment_settlements (
                consignment_id, settlement_date, gross_cents,
                commission_cents, net_cents, commission_type_snapshot,
                commission_value_snapshot, notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                consignment_id, settlement_date, gross, commission, net,
                consignment["commission_type"], consignment["commission_value"],
                (notes or "").strip() or None,
            ),
        )
        settlement_id = cursor.lastrowid
        for item_id, quantity_milli, unit_price, line_total in lines:
            connection.execute(
                """
                UPDATE consignment_items
                SET sold_quantity_milli = sold_quantity_milli + ?
                WHERE id = ?
                """,
                (quantity_milli, item_id),
            )
            connection.execute(
                """
                INSERT INTO consignment_settlement_items (
                    settlement_id, consignment_item_id, quantity_milli,
                    unit_price_cents, line_total_cents
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (settlement_id, item_id, quantity_milli, unit_price, line_total),
            )
        # O acerto representa a venda efetiva dos produtos na loja.
        # O estoque já saiu na remessa; portanto, não registrar nova baixa.
        seller = connection.execute(
            """
            SELECT s.name FROM consignments c
            JOIN sellers s ON s.id = c.seller_id
            WHERE c.id = ?
            """,
            (consignment_id,),
        ).fetchone()
        payment_label = f"Consignação - {seller['name']}"
        sale_cursor = connection.execute(
            """
            INSERT INTO sales (
                sale_date, subtotal_cents, discount_cents,
                total_cents, payment_method, notes,
                consignment_settlement_id
            )
            VALUES (?, ?, 0, ?, ?, ?, ?)
            """,
            (
                settlement_date, gross, gross, payment_label,
                f"Venda consignada da remessa #{consignment_id}",
                settlement_id,
            ),
        )
        sale_id = sale_cursor.lastrowid
        for item_id, quantity_milli, unit_price, line_total in lines:
            item = connection.execute(
                """
                SELECT product_id, product_name_snapshot, unit_symbol_snapshot
                FROM consignment_items WHERE id = ?
                """,
                (item_id,),
            ).fetchone()
            connection.execute(
                """
                INSERT INTO sale_items (
                    sale_id, product_id, quantity_milli,
                    unit_price_cents, line_total_cents,
                    product_name_snapshot, unit_symbol_snapshot
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sale_id, item["product_id"], quantity_milli,
                    unit_price, line_total, item["product_name_snapshot"],
                    item["unit_symbol_snapshot"],
                ),
            )

        # A comissão é despesa no momento em que a loja confirma a venda.
        if commission > 0:
            connection.execute(
                """
                INSERT INTO financial_transactions (
                    transaction_date, direction, description, amount_cents,
                    category, origin, reference_id
                )
                VALUES (?, 'expense', ?, ?, 'Comissões', 'manual', NULL)
                """,
                (
                    settlement_date,
                    f"Comissão da {seller['name']} - acerto #{settlement_id}",
                    commission,
                ),
            )

        connection.commit()
        return settlement_id
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def register_return(
    consignment_id, consignment_item_id, return_date, quantity, notes=None
):
    if not return_date:
        raise ValueError("Informe a data da devolução.")
    if (
        not isinstance(quantity, int) or isinstance(quantity, bool)
        or quantity <= 0
    ):
        raise ValueError("A quantidade devolvida deve ser positiva.")
    quantity_milli = quantity * 1_000_000
    connection = get_connection()
    try:
        connection.execute("BEGIN IMMEDIATE")
        item = connection.execute(
            """
            SELECT * FROM consignment_items
            WHERE id = ? AND consignment_id = ?
            """,
            (consignment_item_id, consignment_id),
        ).fetchone()
        consignment = connection.execute(
            "SELECT status FROM consignments WHERE id = ?",
            (consignment_id,),
        ).fetchone()
        if item is None or consignment is None or consignment["status"] != "open":
            raise ValueError("Remessa ou produto não encontrado ou encerrado.")
        custody = (
            item["delivered_quantity_milli"] - item["sold_quantity_milli"]
            - item["returned_quantity_milli"]
        )
        if quantity_milli > custody:
            raise ValueError("A devolução supera a quantidade ainda na loja.")
        return_value = (
            item["unit_cost_cents_per_unit"] * quantity_milli // 1_000_000
        )
        _register_stock_movement(
            connection,
            "product",
            item["product_id"],
            "adjustment_in",
            quantity_milli,
            reference_type="consignment_return",
            reference_id=consignment_id,
            notes=(notes or "").strip() or f"Devolução da remessa #{consignment_id}",
            value_cents=return_value,
        )
        connection.execute(
            """
            UPDATE consignment_items
            SET returned_quantity_milli = returned_quantity_milli + ?
            WHERE id = ?
            """,
            (quantity_milli, consignment_item_id),
        )
        cursor = connection.execute(
            """
            INSERT INTO consignment_returns (
                consignment_id, consignment_item_id, return_date,
                quantity_milli, notes
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                consignment_id, consignment_item_id, return_date,
                quantity_milli, (notes or "").strip() or None,
            ),
        )
        connection.commit()
        return cursor.lastrowid
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def register_payment(
    consignment_id, payment_date, amount_cents, payment_method=None, notes=None
):
    if not payment_date:
        raise ValueError("Informe a data do repasse.")
    if (
        not isinstance(amount_cents, int) or isinstance(amount_cents, bool)
        or amount_cents <= 0
    ):
        raise ValueError("O valor do repasse deve ser maior que zero.")
    connection = get_connection()
    try:
        connection.execute("BEGIN IMMEDIATE")
        consignment = connection.execute(
            """
            SELECT c.id, s.name AS seller_name
            FROM consignments c JOIN sellers s ON s.id = c.seller_id
            WHERE c.id = ?
            """,
            (consignment_id,),
        ).fetchone()
        if consignment is None:
            raise ValueError("Remessa não encontrada.")
        totals = connection.execute(
            """
            SELECT
                COALESCE((SELECT SUM(net_cents)
                    FROM consignment_settlements WHERE consignment_id = ?), 0)
                    AS due,
                COALESCE((SELECT SUM(amount_cents)
                    FROM consignment_payments WHERE consignment_id = ?), 0)
                    AS paid
            """,
            (consignment_id, consignment_id),
        ).fetchone()
        pending = totals["due"] - totals["paid"]
        if amount_cents > pending:
            raise ValueError("O repasse não pode superar o saldo pendente.")
        cursor = connection.execute(
            """
            INSERT INTO consignment_payments (
                consignment_id, payment_date, amount_cents,
                payment_method, notes
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                consignment_id, payment_date, amount_cents,
                payment_method, (notes or "").strip() or None,
            ),
        )
        payment_id = cursor.lastrowid
        connection.execute(
            """
            INSERT INTO financial_transactions (
                transaction_date, direction, description, amount_cents,
                payment_method, category, origin, reference_id
            )
            VALUES (?, 'income', ?, ?, ?, 'Vendas consignadas', 'manual', ?)
            """,
            (
                payment_date,
                f"Repasse da {consignment['seller_name']} - remessa #{consignment_id}",
                amount_cents,
                payment_method,
                None,
            ),
        )
        connection.commit()
        return payment_id
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def close_consignment(consignment_id):
    with get_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        try:
            consignment = connection.execute(
                "SELECT status FROM consignments WHERE id = ?",
                (consignment_id,),
            ).fetchone()
            if consignment is None:
                raise ValueError("Remessa não encontrada.")
            if consignment["status"] != "open":
                raise ValueError("A remessa já está encerrada.")
            custody = connection.execute(
                """
                SELECT COALESCE(SUM(
                    delivered_quantity_milli - sold_quantity_milli
                    - returned_quantity_milli
                ), 0) AS total
                FROM consignment_items WHERE consignment_id = ?
                """,
                (consignment_id,),
            ).fetchone()["total"]
            pending = connection.execute(
                """
                SELECT
                    COALESCE((SELECT SUM(net_cents)
                        FROM consignment_settlements WHERE consignment_id = ?), 0)
                    - COALESCE((SELECT SUM(amount_cents)
                        FROM consignment_payments WHERE consignment_id = ?), 0)
                    AS total
                """,
                (consignment_id, consignment_id),
            ).fetchone()["total"]
            if custody:
                raise ValueError("Ainda existem produtos em poder da loja.")
            if pending:
                raise ValueError("Ainda existe valor pendente de repasse.")
            connection.execute(
                "UPDATE consignments SET status = 'closed' WHERE id = ?",
                (consignment_id,),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
