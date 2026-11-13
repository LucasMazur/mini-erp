from app.database.connection import get_connection
from app.services.stock_service import (
    _get_balances,
    _register_stock_movement,
    _reverse_stock_movement,
)

PAYMENT_METHODS = {
    "Dinheiro",
    "Pix",
    "Cartão de débito",
    "Cartão de crédito",
    "Transferência",
    "Outro",
}


def create_sale(
    sale_date,
    items,
    payment_method,
    discount_cents=0,
    notes=None,
):
    """Registra uma venda e suas baixas de estoque em uma transação."""

    if not sale_date:
        raise ValueError("A data da venda é obrigatória.")
    if payment_method not in PAYMENT_METHODS:
        raise ValueError("Selecione uma forma de pagamento.")
    if not isinstance(discount_cents, int) or isinstance(discount_cents, bool) or discount_cents < 0:
        raise ValueError("O desconto deve ser um valor inteiro não negativo.")
    if not items:
        raise ValueError("Adicione pelo menos um produto à venda.")

    normalized_items = []
    seen_products = set()
    subtotal_cents = 0

    for item in items:
        product_id = item.get("product_id")
        quantity = item.get("quantity")
        unit_price_cents = item.get("unit_price_cents")

        if not isinstance(product_id, int) or isinstance(product_id, bool):
            raise ValueError("Produto inválido.")
        if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity <= 0:
            raise ValueError("A quantidade deve ser um número inteiro maior que zero.")
        if not isinstance(unit_price_cents, int) or isinstance(unit_price_cents, bool) or unit_price_cents < 0:
            raise ValueError("O preço unitário deve ser um valor inteiro não negativo.")
        if product_id in seen_products:
            raise ValueError("O mesmo produto não pode ser adicionado duas vezes.")
        seen_products.add(product_id)

        normalized_items.append({
            "product_id": product_id,
            "quantity": quantity,
            "unit_price_cents": unit_price_cents,
            "line_total_cents": quantity * unit_price_cents,
        })
        subtotal_cents += quantity * unit_price_cents

    if discount_cents > subtotal_cents:
        raise ValueError("O desconto não pode ser maior que o subtotal.")

    connection = get_connection()
    try:
        connection.execute("BEGIN IMMEDIATE")

        products = {}
        for item in normalized_items:
            product = connection.execute(
                """
                SELECT p.id, p.name, p.stock_unit_id, u.symbol AS unit_symbol
                FROM products p
                JOIN units u ON u.id = p.stock_unit_id
                WHERE p.id = ? AND p.active = 1
                """,
                (item["product_id"],),
            ).fetchone()
            if product is None:
                raise ValueError("Produto não encontrado ou inativo.")

            balance = _get_balances(
                connection, "product_id", item["product_id"]
            )
            required_quantity = item["quantity"] * 1000
            if balance["quantity_milli"] < required_quantity:
                raise ValueError(
                    f"Estoque insuficiente para {product['name']}. "
                    f"Disponível: {balance['quantity_milli'] // 1000}; "
                    f"solicitado: {item['quantity']}."
                )
            products[item["product_id"]] = dict(product)

        cursor = connection.execute(
            """
            INSERT INTO sales (
                sale_date, subtotal_cents, discount_cents,
                total_cents, payment_method, notes
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                sale_date,
                subtotal_cents,
                discount_cents,
                subtotal_cents - discount_cents,
                payment_method,
                notes.strip() if notes and notes.strip() else None,
            ),
        )
        sale_id = cursor.lastrowid

        total_income_cents = subtotal_cents - discount_cents
        if total_income_cents > 0:
            connection.execute(
                """
                INSERT INTO financial_transactions (
                    transaction_date, direction, description,
                    amount_cents, payment_method, category,
                    origin, reference_id
                )
                VALUES (?, 'income', ?, ?, ?, 'Vendas', 'sale', ?)
                """,
                (
                    sale_date,
                    f"Venda #{sale_id}",
                    total_income_cents,
                    payment_method,
                    sale_id,
                ),
            )

        for item in normalized_items:
            product = products[item["product_id"]]
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
                    sale_id,
                    item["product_id"],
                    item["quantity"] * 1000,
                    item["unit_price_cents"],
                    item["line_total_cents"],
                    product["name"],
                    product["unit_symbol"],
                ),
            )

            _register_stock_movement(
                connection=connection,
                item_type="product",
                item_id=item["product_id"],
                movement_type="sale",
                quantity_milli=-(item["quantity"] * 1000),
                reference_type="sale",
                reference_id=sale_id,
                notes=f"Saída da venda #{sale_id}",
            )

        connection.commit()
        return sale_id

    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def get_sale(sale_id):
    with get_connection() as connection:
        sale = connection.execute(
            """
            SELECT *
            FROM sales
            WHERE id = ?
            """,
            (sale_id,),
        ).fetchone()
        if sale is None:
            return None

        items = connection.execute(
            """
            SELECT *
            FROM sale_items
            WHERE sale_id = ?
            ORDER BY id
            """,
            (sale_id,),
        ).fetchall()

    result = dict(sale)
    result["items"] = [dict(item) for item in items]
    return result


def list_sales():
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                s.*,
                COUNT(si.id) AS item_count
            FROM sales s
            LEFT JOIN sale_items si ON si.sale_id = s.id
            GROUP BY s.id
            ORDER BY s.sale_date DESC, s.id DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def reverse_sale(sale_id, notes=None):
    """Estorna todas as baixas da venda sem apagar seu histórico."""

    connection = get_connection()
    try:
        connection.execute("BEGIN IMMEDIATE")

        sale = connection.execute(
            "SELECT id, reversed_at FROM sales WHERE id = ?",
            (sale_id,),
        ).fetchone()
        if sale is None:
            raise ValueError("Venda não encontrada.")
        if sale["reversed_at"] is not None:
            raise ValueError("Essa venda já foi estornada.")

        movements = connection.execute(
            """
            SELECT id
            FROM stock_movements
            WHERE reference_type = 'sale'
              AND reference_id = ?
              AND movement_type = 'sale'
            ORDER BY id
            """,
            (sale_id,),
        ).fetchall()
        if not movements:
            raise ValueError("Não foram encontradas movimentações da venda.")

        for movement in movements:
            _reverse_stock_movement(
                connection,
                movement["id"],
                notes or f"Estorno da venda #{sale_id}",
            )

        connection.execute(
            "UPDATE sales SET reversed_at = CURRENT_TIMESTAMP WHERE id = ?",
            (sale_id,),
        )

        original_finance = connection.execute(
            """
            SELECT amount_cents
            FROM financial_transactions
            WHERE origin = 'sale' AND reference_id = ?
            """,
            (sale_id,),
        ).fetchone()
        if original_finance is not None:
            connection.execute(
                """
                INSERT INTO financial_transactions (
                    transaction_date, direction, description,
                    amount_cents, category, origin, reference_id
                )
                VALUES (date('now', 'localtime'), 'expense', ?, ?,
                        'Estornos', 'sale_reversal', ?)
                """,
                (
                    f"Estorno da venda #{sale_id}",
                    original_finance["amount_cents"],
                    sale_id,
                ),
            )

        connection.commit()
        return sale_id

    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
