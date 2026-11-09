
from app.database.connection import get_connection


def generate_next_product_code():
    """Gera o próximo código numérico de quatro dígitos."""

    with get_connection() as connection:
        result = connection.execute(
            """
            SELECT MAX(CAST(code AS INTEGER)) AS last_code
            FROM products
            WHERE code GLOB '[0-9][0-9][0-9][0-9]'
            """
        ).fetchone()

    last_code = result["last_code"] or 0
    next_code = last_code + 1

    if next_code > 9999:
        raise ValueError(
            "A sequência de códigos de produtos foi esgotada."
        )

    return f"{next_code:04d}"


def _validate_product(
    name,
    stock_unit_id,
    sale_price_cents,
    category_id=None,
):
    if not name or not name.strip():
        raise ValueError("O nome do produto é obrigatório.")

    if (
        sale_price_cents is not None
        and (
            isinstance(sale_price_cents, bool)
            or not isinstance(sale_price_cents, int)
            or sale_price_cents < 0
        )
    ):
        raise ValueError("O preço de venda deve ser um valor inteiro não negativo.")

    with get_connection() as connection:
        unit = connection.execute(
            "SELECT id FROM units WHERE id = ? AND active = 1",
            (stock_unit_id,),
        ).fetchone()

        if unit is None:
            raise ValueError("A unidade de estoque não existe ou está inativa.")

        if category_id is not None:
            category = connection.execute(
                """
                SELECT id FROM categories
                WHERE id = ? AND kind = 'product' AND active = 1
                """,
                (category_id,),
            ).fetchone()

            if category is None:
                raise ValueError("A categoria não existe, está inativa ou não é de produto.")


def create_product(
    name,
    stock_unit_id,
    code=None,
    category_id=None,
    sale_price_cents=None,
    notes=None,
):
    _validate_product(name, stock_unit_id, sale_price_cents, category_id)

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO products (
                code, name, category_id, stock_unit_id,
                sale_price_cents, notes
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                code.strip() if code else None,
                name.strip(),
                category_id,
                stock_unit_id,
                sale_price_cents,
                notes,
            ),
        )

        return cursor.lastrowid


def get_product(product_id):
    with get_connection() as connection:
        product = connection.execute(
            """
            SELECT
                p.*,
                u.name AS unit_name,
                u.symbol AS unit_symbol,
                c.name AS category_name
            FROM products p
            JOIN units u ON u.id = p.stock_unit_id
            LEFT JOIN categories c ON c.id = p.category_id
            WHERE p.id = ?
            """,
            (product_id,),
        ).fetchone()

        return dict(product) if product else None


def list_products(search="", include_inactive=False):
    query = """
        SELECT
            p.*,
            u.name AS unit_name,
            u.symbol AS unit_symbol,
            c.name AS category_name
        FROM products p
        JOIN units u ON u.id = p.stock_unit_id
        LEFT JOIN categories c ON c.id = p.category_id
        WHERE 1 = 1
    """
    params = []

    if not include_inactive:
        query += " AND p.active = 1"

    if search:
        query += " AND (p.name LIKE ? OR p.code LIKE ?)"
        term = f"%{search.strip()}%"
        params.extend([term, term])

    query += " ORDER BY p.name"

    with get_connection() as connection:
        products = connection.execute(query, params).fetchall()
        return [dict(product) for product in products]


def update_product(
    product_id,
    name,
    stock_unit_id,
    code=None,
    category_id=None,
    sale_price_cents=None,
    notes=None,
):
    _validate_product(name, stock_unit_id, sale_price_cents, category_id)

    with get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE products
            SET
                code = ?,
                name = ?,
                category_id = ?,
                stock_unit_id = ?,
                sale_price_cents = ?,
                notes = ?
            WHERE id = ?
            """,
            (
                code.strip() if code else None,
                name.strip(),
                category_id,
                stock_unit_id,
                sale_price_cents,
                notes,
                product_id,
            ),
        )

        if cursor.rowcount == 0:
            raise ValueError("Produto não encontrado.")


def deactivate_product(product_id):
    with get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE products
            SET active = 0
            WHERE id = ? AND active = 1
            """,
            (product_id,),
        )

        if cursor.rowcount == 0:
            raise ValueError("Produto não encontrado ou já está inativo.")
