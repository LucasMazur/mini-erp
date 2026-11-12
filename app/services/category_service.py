from app.database.connection import get_connection

CATEGORY_KINDS = {
    "Produto": "product",
    "Material": "material",
}


def list_categories(kind=None, include_inactive=False):
    if kind not in (None, "product", "material"):
        raise ValueError("Tipo de categoria inválido.")

    query = """
        SELECT
            c.id,
            c.name,
            c.kind,
            c.active,
            CASE c.kind
                WHEN 'product' THEN 'Produto'
                WHEN 'material' THEN 'Material'
            END AS kind_label,
            CASE c.kind
                WHEN 'product' THEN (
                    SELECT COUNT(*) FROM products p
                    WHERE p.category_id = c.id
                )
                WHEN 'material' THEN (
                    SELECT COUNT(*) FROM materials m
                    WHERE m.category_id = c.id
                )
            END AS linked_items
        FROM categories c
        WHERE 1 = 1
    """
    params = []

    if kind:
        query += " AND c.kind = ?"
        params.append(kind)

    if not include_inactive:
        query += " AND c.active = 1"

    query += " ORDER BY c.kind, c.name COLLATE NOCASE"

    with get_connection() as connection:
        rows = connection.execute(query, params).fetchall()
        return [dict(row) for row in rows]


def create_category(name, kind):
    name = name.strip() if name else ""
    if not name:
        raise ValueError("Informe o nome da categoria.")
    if kind not in ("product", "material"):
        raise ValueError("Selecione um tipo de categoria.")

    with get_connection() as connection:
        try:
            cursor = connection.execute(
                "INSERT INTO categories (name, kind) VALUES (?, ?)",
                (name, kind),
            )
        except Exception as error:
            if "UNIQUE constraint failed" in str(error):
                raise ValueError(
                    "Já existe uma categoria com esse nome para esse tipo."
                ) from error
            raise
        return cursor.lastrowid


def update_category(category_id, name):
    name = name.strip() if name else ""
    if not name:
        raise ValueError("Informe o nome da categoria.")

    with get_connection() as connection:
        try:
            cursor = connection.execute(
                "UPDATE categories SET name = ? WHERE id = ? AND active = 1",
                (name, category_id),
            )
        except Exception as error:
            if "UNIQUE constraint failed" in str(error):
                raise ValueError(
                    "Já existe uma categoria com esse nome para esse tipo."
                ) from error
            raise

        if cursor.rowcount == 0:
            raise ValueError("Categoria não encontrada ou inativa.")


def deactivate_category(category_id):
    with get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE categories
            SET active = 0
            WHERE id = ? AND active = 1
            """,
            (category_id,),
        )
        if cursor.rowcount == 0:
            raise ValueError("Categoria não encontrada ou já inativa.")
