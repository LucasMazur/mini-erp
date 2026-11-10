import sqlite3

import pytest

from app.services import stock_service


@pytest.fixture
def test_db(tmp_path, monkeypatch):
    database_path = tmp_path / "test_stock.db"

    def get_test_connection():
        connection = sqlite3.connect(database_path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    monkeypatch.setattr(
        stock_service,
        "get_connection",
        get_test_connection,
    )

    with get_test_connection() as connection:
        connection.executescript("""
            CREATE TABLE materials (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE products (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE stock_movements (
                id INTEGER PRIMARY KEY,
                material_id INTEGER,
                product_id INTEGER,
                movement_type TEXT NOT NULL,
                quantity_milli INTEGER NOT NULL,
                value_cents INTEGER NOT NULL DEFAULT 0,
                occurred_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                reference_type TEXT,
                reference_id INTEGER,
                notes TEXT,
                reversal_of_id INTEGER UNIQUE,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

                CHECK (
                    (material_id IS NOT NULL AND product_id IS NULL)
                    OR
                    (material_id IS NULL AND product_id IS NOT NULL)
                ),

                FOREIGN KEY (material_id) REFERENCES materials(id),
                FOREIGN KEY (product_id) REFERENCES products(id)
            );

            INSERT INTO materials (id, name)
            VALUES (1, 'PLA');

            INSERT INTO products (id, name)
            VALUES (1, 'Brinco Lua');
        """)

    return get_test_connection


def test_initial_balance_is_zero(test_db):
    balance = stock_service.get_stock_balance("material", 1)

    assert balance == 0


def test_register_material_entry(test_db):
    stock_service.register_stock_movement(
        item_type="material",
        item_id=1,
        movement_type="purchase",
        quantity_milli=1000000,
        value_cents=8500,
    )

    balance = stock_service.get_stock_balance("material", 1)

    assert balance == 1000000


def test_register_material_consumption(test_db):
    stock_service.register_stock_movement(
        "material", 1, "purchase", 1000000, value_cents=8500
    )

    stock_service.register_stock_movement(
        "material", 1, "production_consumption", -40000
    )

    balance = stock_service.get_stock_balance("material", 1)

    assert balance == 960000


def test_register_product_output_and_sale(test_db):
    stock_service.register_stock_movement(
        "product", 1, "production_output", 5000,
        value_cents=2500,
    )

    stock_service.register_stock_movement(
        "product", 1, "sale", -2000
    )

    balance = stock_service.get_stock_balance("product", 1)

    assert balance == 3000


def test_insufficient_stock_is_rejected(test_db):
    stock_service.register_stock_movement(
        "material", 1, "purchase", 10000, value_cents=100
    )

    with pytest.raises(ValueError, match="Estoque insuficiente"):
        stock_service.register_stock_movement(
            "material", 1, "production_consumption", -15000
        )

    balance = stock_service.get_stock_balance("material", 1)

    assert balance == 10000


def test_zero_quantity_is_rejected(test_db):
    with pytest.raises(ValueError, match="não pode ser zero"):
        stock_service.register_stock_movement(
            "material", 1, "purchase", 0
        )


def test_wrong_movement_type_for_item_is_rejected(test_db):
    with pytest.raises(ValueError, match="não corresponde"):
        stock_service.register_stock_movement(
            "product", 1, "purchase", 10000
        )


def test_negative_quantity_for_purchase_is_rejected(test_db):
    with pytest.raises(ValueError, match="sinal"):
        stock_service.register_stock_movement(
            "material", 1, "purchase", -10000
        )


def test_inactive_material_is_rejected(test_db):
    with test_db() as connection:
        connection.execute(
            "UPDATE materials SET active = 0 WHERE id = 1"
        )

    with pytest.raises(ValueError, match="não encontrado ou inativo"):
        stock_service.register_stock_movement(
            "material", 1, "purchase", 10000
        )
def test_reverse_purchase(test_db):
    purchase_id = stock_service.register_stock_movement(
        "material", 1, "purchase", 100000, value_cents=100,
    )

    stock_service.reverse_stock_movement(purchase_id)

    assert stock_service.get_stock_balance("material", 1) == 0


def test_cannot_reverse_same_movement_twice(test_db):
    purchase_id = stock_service.register_stock_movement(
        "material", 1, "purchase", 100000,
        value_cents=100,
    )

    stock_service.reverse_stock_movement(purchase_id)

    with pytest.raises(ValueError, match="já foi estornada"):
        stock_service.reverse_stock_movement(purchase_id)


def test_cannot_reverse_movement_if_it_causes_negative_stock(test_db):
    purchase_id = stock_service.register_stock_movement(
        "material", 1, "purchase", 100000,
        value_cents=100,
    )

    stock_service.register_stock_movement(
        "material", 1, "production_consumption", -40000
    )

    with pytest.raises(ValueError, match="estoque negativo"):
        stock_service.reverse_stock_movement(purchase_id)

    assert stock_service.get_stock_balance("material", 1) == 60000


def test_reverse_product_sale(test_db):
    stock_service.register_stock_movement(
        "product", 1, "production_output", 5000,
        value_cents=2500,
    )

    sale_id = stock_service.register_stock_movement(
        "product", 1, "sale", -2000
    )

    stock_service.reverse_stock_movement(sale_id)

    assert stock_service.get_stock_balance("product", 1) == 5000


def test_purchase_records_financial_value(test_db):
    stock_service.register_stock_movement(
        "material", 1, "purchase", 1000000,
        value_cents=8500,
    )

    valuation = stock_service.get_stock_valuation("material", 1)

    assert valuation["quantity_milli"] == 1000000
    assert valuation["value_cents"] == 8500


def test_consumption_reduces_stock_value_by_average_cost(test_db):
    stock_service.register_stock_movement(
        "material", 1, "purchase", 1000000,
        value_cents=8500,
    )

    stock_service.register_stock_movement(
        "material", 1, "purchase", 1000000,
        value_cents=10000,
    )

    stock_service.register_stock_movement(
        "material", 1, "production_consumption", -100000,
    )

    valuation = stock_service.get_stock_valuation("material", 1)

    assert valuation["quantity_milli"] == 1900000
    assert valuation["value_cents"] == 17575


def test_reversal_restores_quantity_and_financial_value(test_db):
    purchase_id = stock_service.register_stock_movement(
        "material", 1, "purchase", 1000000,
        value_cents=8500,
    )

    stock_service.reverse_stock_movement(purchase_id)

    valuation = stock_service.get_stock_valuation("material", 1)

    assert valuation["quantity_milli"] == 0
    assert valuation["value_cents"] == 0


def test_entry_requires_financial_value(test_db):
    with pytest.raises(ValueError, match="valor financeiro"):
        stock_service.register_stock_movement(
            "material", 1, "purchase", 1000000,
        )


def test_negative_financial_value_is_rejected(test_db):
    with pytest.raises(ValueError, match="não pode ser negativo"):
        stock_service.register_stock_movement(
            "material", 1, "purchase", 1000000,
            value_cents=-100,
        )
def test_list_stock_movements_returns_material_history(test_db):
    stock_service.register_stock_movement(
        "material", 1, "purchase", 1000000,
        value_cents=8500,
        notes="Compra de PLA",
    )

    stock_service.register_stock_movement(
        "material", 1, "production_consumption", -100000,
        notes="Consumo na produção",
    )

    movements = stock_service.list_stock_movements(
        "material", 1
    )

    assert len(movements) == 2

    # Mais recente primeiro
    assert movements[0]["movement_type"] == "production_consumption"
    assert movements[0]["quantity_milli"] == -100000

    assert movements[1]["movement_type"] == "purchase"
    assert movements[1]["quantity_milli"] == 1000000
    assert movements[1]["value_cents"] == 8500
    assert movements[1]["notes"] == "Compra de PLA"


def test_list_stock_movements_includes_reversals(test_db):
    purchase_id = stock_service.register_stock_movement(
        "material", 1, "purchase", 100000,
        value_cents=100,
    )

    stock_service.reverse_stock_movement(purchase_id)

    movements = stock_service.list_stock_movements(
        "material", 1
    )

    assert len(movements) == 2
    assert movements[0]["movement_type"] == "reversal"
    assert movements[0]["reversal_of_id"] == purchase_id


def test_list_stock_movements_includes_inactive_material(test_db):
    stock_service.register_stock_movement(
        "material", 1, "purchase", 100000,
        value_cents=100,
    )

    with test_db() as connection:
        connection.execute(
            "UPDATE materials SET active = 0 WHERE id = 1"
        )

    movements = stock_service.list_stock_movements(
        "material", 1
    )

    assert len(movements) == 1
    assert movements[0]["movement_type"] == "purchase"


def test_list_stock_movements_rejects_invalid_item(test_db):
    with pytest.raises(ValueError, match="Tipo de item inválido"):
        stock_service.list_stock_movements("invalid", 1)

    with pytest.raises(ValueError, match="não encontrado"):
        stock_service.list_stock_movements("material", 999)