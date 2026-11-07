
import sqlite3

import pytest

from app.services import supplier_service


@pytest.fixture
def test_database(tmp_path, monkeypatch):
    """Cria um banco isolado para os testes."""

    database_path = tmp_path / "test.db"

    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row

    connection.execute(
        """
        CREATE TABLE suppliers (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            document TEXT,
            phone TEXT,
            email TEXT,
            address TEXT,
            notes TEXT,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    connection.commit()
    connection.close()

    def get_test_connection():
        connection = sqlite3.connect(database_path)
        connection.row_factory = sqlite3.Row
        return connection

    monkeypatch.setattr(
        supplier_service,
        "get_connection",
        get_test_connection,
    )

    return database_path


def test_create_supplier_without_document(test_database):
    supplier_id = supplier_service.create_supplier(
        name="Fornecedor de PLA"
    )

    supplier = supplier_service.get_supplier(supplier_id)

    assert supplier["name"] == "Fornecedor de PLA"
    assert supplier["document"] is None
    assert supplier["active"] == 1


def test_search_supplier_by_name(test_database):
    supplier_service.create_supplier("Fornecedor de PLA")

    results = supplier_service.list_suppliers("PLA")

    assert len(results) == 1
    assert results[0]["name"] == "Fornecedor de PLA"


def test_update_supplier(test_database):
    supplier_id = supplier_service.create_supplier("Fornecedor antigo")

    supplier_service.update_supplier(
        supplier_id,
        name="Fornecedor atualizado",
        phone="11999999999",
    )

    supplier = supplier_service.get_supplier(supplier_id)

    assert supplier["name"] == "Fornecedor atualizado"
    assert supplier["phone"] == "11999999999"


def test_deactivate_supplier_without_deleting(test_database):
    supplier_id = supplier_service.create_supplier("Fornecedor teste")

    supplier_service.deactivate_supplier(supplier_id)

    supplier = supplier_service.get_supplier(supplier_id)

    assert supplier is not None
    assert supplier["active"] == 0
    assert supplier_service.list_suppliers() == []


def test_supplier_name_is_required(test_database):
    with pytest.raises(ValueError):
        supplier_service.create_supplier("   ")
