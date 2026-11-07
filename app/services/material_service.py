
from app.database.connection import get_connection


def _validate_material(
    name: str,
    stock_unit_id: int,
    minimum_stock_quantity_milli: int,
    category_id: int | None = None,
) -> None:
    if not name.strip():
        raise ValueError("O nome do material é obrigatório.")

    if minimum_stock_quantity_milli < 0:
        raise ValueError("O estoque mínimo não pode ser negativo.")

    with get_connection() as connection:
        unit = connection.execute(
            """
            SELECT id FROM units
            WHERE id = ? AND active = 1
            """,
            (stock_unit_id,),
        ).fetchone()

        if unit is None:
            raise ValueError("Unidade de medida inválida ou inativa.")

        if category_id is not None:
            category = connection.execute(
                """
                SELECT id FROM categories
                WHERE id = ? AND kind = 'material' AND active = 1
                """,
                (category_id,),
            ).fetchone()

            if category is None:
                raise ValueError("Categoria de material inválida.")


def create_material(
    name: str,
    stock_unit_id: int,
    code: str | None = None,
    category_id: int | None = None,
    minimum_stock_quantity_milli: int = 0,
    notes: str | None = None,
) -> int:
    """Cadastra uma matéria-prima e retorna seu ID."""

    _validate_material(
        name,
        stock_unit_id,
        minimum_stock_quantity_milli,
        category_id,
    )

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO materials (
                code,
                name,
                category_id,
                stock_unit_id,
                minimum_stock_quantity_milli,
                notes
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                code.strip() or None if code else None,
                name.strip(),
                category_id,
                stock_unit_id,
                minimum_stock_quantity_milli,
                notes or None,
            ),
        )

        return cursor.lastrowid


def get_material(material_id: int) -> dict | None:
    """Consulta uma matéria-prima pelo ID."""

    with get_connection() as connection:
        material = connection.execute(
            """
            SELECT
                m.*,
                u.name AS unit_name,
                u.symbol AS unit_symbol
            FROM materials m
            JOIN units u ON u.id = m.stock_unit_id
            WHERE m.id = ?
            """,
            (material_id,),
        ).fetchone()

        return dict(material) if material else None


def list_materials(
    search: str = "",
    include_inactive: bool = False,
) -> list[dict]:
    """Lista e pesquisa matérias-primas."""

    query = """
        SELECT
            m.*,
            u.name AS unit_name,
            u.symbol AS unit_symbol
        FROM materials m
        JOIN units u ON u.id = m.stock_unit_id
        WHERE (m.name LIKE ? OR m.code LIKE ?)
    """

    term = f"%{search.strip()}%"

    if not include_inactive:
        query += " AND m.active = 1"

    query += " ORDER BY m.name"

    with get_connection() as connection:
        results = connection.execute(
            query,
            (term, term),
        ).fetchall()

        return [dict(row) for row in results]


def update_material(
    material_id: int,
    name: str,
    stock_unit_id: int,
    code: str | None = None,
    category_id: int | None = None,
    minimum_stock_quantity_milli: int = 0,
    notes: str | None = None,
) -> None:
    """Atualiza os dados de uma matéria-prima."""

    _validate_material(
        name,
        stock_unit_id,
        minimum_stock_quantity_milli,
        category_id,
    )

    with get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE materials
            SET code = ?,
                name = ?,
                category_id = ?,
                stock_unit_id = ?,
                minimum_stock_quantity_milli = ?,
                notes = ?
            WHERE id = ?
            """,
            (
                code.strip() or None if code else None,
                name.strip(),
                category_id,
                stock_unit_id,
                minimum_stock_quantity_milli,
                notes or None,
                material_id,
            ),
        )

        if cursor.rowcount == 0:
            raise ValueError("Matéria-prima não encontrada.")


def deactivate_material(material_id: int) -> None:
    """Desativa uma matéria-prima sem excluir seu histórico."""

    with get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE materials
            SET active = 0
            WHERE id = ? AND active = 1
            """,
            (material_id,),
        )

        if cursor.rowcount == 0:
            raise ValueError(
                "Matéria-prima não encontrada ou já desativada."
            )
