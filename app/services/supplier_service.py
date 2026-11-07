
from app.database.connection import get_connection


def create_supplier(
    name: str,
    document: str | None = None,
    phone: str | None = None,
    email: str | None = None,
    address: str | None = None,
    notes: str | None = None,
) -> int:
    """Cadastra um fornecedor e retorna seu ID."""

    name = name.strip()

    if not name:
        raise ValueError("O nome do fornecedor é obrigatório.")

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO suppliers (
                name, document, phone, email, address, notes
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                document or None,
                phone or None,
                email or None,
                address or None,
                notes or None,
            ),
        )

        return cursor.lastrowid


def get_supplier(supplier_id: int) -> dict | None:
    """Busca um fornecedor pelo ID."""

    with get_connection() as connection:
        supplier = connection.execute(
            "SELECT * FROM suppliers WHERE id = ?",
            (supplier_id,),
        ).fetchone()

        return dict(supplier) if supplier else None


def list_suppliers(search: str = "", include_inactive: bool = False) -> list[dict]:
    """Lista fornecedores, permitindo pesquisa por nome ou documento."""

    query = """
        SELECT * FROM suppliers
        WHERE (
            name LIKE ? OR document LIKE ?
        )
    """

    search_term = f"%{search.strip()}%"

    if not include_inactive:
        query += " AND active = 1"

    query += " ORDER BY name"

    with get_connection() as connection:
        results = connection.execute(
            query,
            (search_term, search_term),
        ).fetchall()

        return [dict(row) for row in results]


def update_supplier(
    supplier_id: int,
    name: str,
    document: str | None = None,
    phone: str | None = None,
    email: str | None = None,
    address: str | None = None,
    notes: str | None = None,
) -> None:
    """Atualiza os dados de um fornecedor."""

    name = name.strip()

    if not name:
        raise ValueError("O nome do fornecedor é obrigatório.")

    with get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE suppliers
            SET name = ?,
                document = ?,
                phone = ?,
                email = ?,
                address = ?,
                notes = ?
            WHERE id = ?
            """,
            (
                name,
                document or None,
                phone or None,
                email or None,
                address or None,
                notes or None,
                supplier_id,
            ),
        )

        if cursor.rowcount == 0:
            raise ValueError("Fornecedor não encontrado.")


def deactivate_supplier(supplier_id: int) -> None:
    """Desativa um fornecedor sem apagar seu histórico."""

    with get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE suppliers
            SET active = 0
            WHERE id = ? AND active = 1
            """,
            (supplier_id,),
        )

        if cursor.rowcount == 0:
            raise ValueError(
                "Fornecedor não encontrado ou já desativado."
            )
