
import sqlite3

import pytest

from app.services import purchase_service, stock_service


@pytest.fixture
def test_db(tmp_path, monkeypatch):
    database_path = tmp_path / "test_purchases.db"

    def get_test_connection():
        connection = sqlite3.connect(database_path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    monkeypatch.setattr(
        purchase_service,
        "get_connection",
        get_test_connection,
    )
    monkeypatch.setattr(
        stock_service,
        "get_connection",
        get_test_connection,
    )

    with get_test_connection() as connection:
        connection.executescript("""
            CREATE TABLE units (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                symbol TEXT NOT NULL,
                dimension TEXT NOT NULL,
                factor_num INTEGER NOT NULL,
                factor_den INTEGER NOT NULL,
                is_base INTEGER NOT NULL DEFAULT 0,
                active INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE suppliers (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE materials (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                stock_unit_id INTEGER NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (stock_unit_id) REFERENCES units(id)
            );

            CREATE TABLE purchases (
                id INTEGER PRIMARY KEY,
                supplier_id INTEGER,
                purchase_date TEXT NOT NULL,
                invoice_number TEXT,
                freight_cents INTEGER NOT NULL DEFAULT 0,
                discount_cents INTEGER NOT NULL DEFAULT 0,
                notes TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
            );

            CREATE TABLE purchase_items (
                id INTEGER PRIMARY KEY,
                purchase_id INTEGER NOT NULL,
                material_id INTEGER NOT NULL,
                unit_id INTEGER NOT NULL,
                quantity_milli INTEGER NOT NULL,
                unit_cost_cents INTEGER NOT NULL,
                line_total_cents INTEGER NOT NULL,
                material_name_snapshot TEXT NOT NULL,
                unit_symbol_snapshot TEXT NOT NULL,
                landed_cost_cents INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (purchase_id) REFERENCES purchases(id),
                FOREIGN KEY (material_id) REFERENCES materials(id),
                FOREIGN KEY (unit_id) REFERENCES units(id)
            );

            CREATE TABLE financial_transactions (
                id INTEGER PRIMARY KEY,
                transaction_date TEXT NOT NULL,
                direction TEXT NOT NULL,
                description TEXT NOT NULL,
                amount_cents INTEGER NOT NULL,
                payment_method TEXT,
                category TEXT,
                origin TEXT NOT NULL,
                reference_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
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
                FOREIGN KEY (material_id) REFERENCES materials(id)
            );

            INSERT INTO units
                (id, name, symbol, dimension, factor_num, factor_den, is_base)
            VALUES
                (1, 'Grama', 'g', 'mass', 1000, 1, 1),
                (2, 'Quilograma', 'kg', 'mass', 1000000, 1, 0),
                (3, 'Unidade', 'un', 'count', 1000, 1, 1);

            INSERT INTO suppliers (id, name)
            VALUES (1, 'Fornecedor de teste');

            INSERT INTO materials (id, name, stock_unit_id)
            VALUES
                (1, 'PLA', 1),
                (2, 'PETG', 1);
        """)

    return get_test_connection


def test_create_purchase_without_supplier_or_invoice(test_db):
    purchase_id = purchase_service.create_purchase(
        purchase_date="2026-11-07",
        items=[
            {
                "material_id": 1,
                "unit_id": 1,
                "quantity_milli": 1000000,
                "line_total_cents": 8500,
            }
        ],
    )

    with test_db() as connection:
        purchase = connection.execute(
            "SELECT * FROM purchases WHERE id = ?",
            (purchase_id,),
        ).fetchone()

        item = connection.execute(
            "SELECT * FROM purchase_items WHERE purchase_id = ?",
            (purchase_id,),
        ).fetchone()

        movement = connection.execute(
            """
            SELECT * FROM stock_movements
            WHERE reference_type = 'purchase' AND reference_id = ?
            """,
            (purchase_id,),
        ).fetchone()

    assert purchase["supplier_id"] is None
    assert purchase["invoice_number"] is None
    assert item["line_total_cents"] == 8500
    assert item["landed_cost_cents"] == 8500
    assert movement["quantity_milli"] == 1000000
    assert movement["value_cents"] == 8500


def test_purchase_converts_kg_to_grams(test_db):
    purchase_service.create_purchase(
        purchase_date="2026-11-07",
        items=[
            {
                "material_id": 1,
                "unit_id": 2,
                "quantity_milli": 1000000,
                "line_total_cents": 8500,
            }
        ],
    )

    valuation = stock_service.get_stock_valuation("material", 1)

    assert valuation["quantity_milli"] == 1000000000
    assert valuation["value_cents"] == 8500


def test_purchase_allocates_freight_and_discount(test_db):
    purchase_id = purchase_service.create_purchase(
        purchase_date="2026-11-07",
        freight_cents=1000,
        discount_cents=500,
        items=[
            {
                "material_id": 1,
                "unit_id": 1,
                "quantity_milli": 1000000,
                "line_total_cents": 8000,
            },
            {
                "material_id": 2,
                "unit_id": 1,
                "quantity_milli": 1000000,
                "line_total_cents": 4000,
            },
        ],
    )

    with test_db() as connection:
        items = connection.execute(
            """
            SELECT landed_cost_cents
            FROM purchase_items
            WHERE purchase_id = ?
            ORDER BY id
            """,
            (purchase_id,),
        ).fetchall()

    assert [item["landed_cost_cents"] for item in items] == [
        8334,
        4166,
    ]
    assert sum(item["landed_cost_cents"] for item in items) == 12500


def test_purchase_with_incompatible_unit_fails(test_db):
    with pytest.raises(ValueError, match="incompatível"):
        purchase_service.create_purchase(
            purchase_date="2026-11-07",
            items=[
                {
                    "material_id": 1,
                    "unit_id": 3,
                    "quantity_milli": 1000,
                    "line_total_cents": 100,
                }
            ],
        )

    with test_db() as connection:
        count = connection.execute(
            "SELECT COUNT(*) AS total FROM purchases"
        ).fetchone()["total"]

    assert count == 0


def test_purchase_failure_rolls_back_everything(test_db):
    with pytest.raises(ValueError, match="Material não encontrado"):
        purchase_service.create_purchase(
            purchase_date="2026-11-07",
            items=[
                {
                    "material_id": 1,
                    "unit_id": 1,
                    "quantity_milli": 1000000,
                    "line_total_cents": 8500,
                },
                {
                    "material_id": 999,
                    "unit_id": 1,
                    "quantity_milli": 1000000,
                    "line_total_cents": 4000,
                },
            ],
        )

    with test_db() as connection:
        purchase_count = connection.execute(
            "SELECT COUNT(*) AS total FROM purchases"
        ).fetchone()["total"]

        item_count = connection.execute(
            "SELECT COUNT(*) AS total FROM purchase_items"
        ).fetchone()["total"]

        movement_count = connection.execute(
            "SELECT COUNT(*) AS total FROM stock_movements"
        ).fetchone()["total"]

    assert purchase_count == 0
    assert item_count == 0
    assert movement_count == 0

def test_get_purchase_with_items(test_db):
    purchase_id = purchase_service.create_purchase(
        purchase_date="2026-11-07",
        supplier_id=1,
        invoice_number="NF-123",
        items=[
            {
                "material_id": 1,
                "unit_id": 1,
                "quantity_milli": 1000000,
                "line_total_cents": 8500,
            },
            {
                "material_id": 2,
                "unit_id": 1,
                "quantity_milli": 500000,
                "line_total_cents": 4000,
            },
        ],
    )

    purchase = purchase_service.get_purchase(purchase_id)

    assert purchase["id"] == purchase_id
    assert purchase["supplier_name"] == "Fornecedor de teste"
    assert purchase["invoice_number"] == "NF-123"
    assert len(purchase["items"]) == 2
    assert purchase["items"][0]["material_name_snapshot"] == "PLA"
    assert purchase["items"][1]["material_name_snapshot"] == "PETG"


def test_get_nonexistent_purchase_returns_none(test_db):
    purchase = purchase_service.get_purchase(999)

    assert purchase is None


def test_list_purchases(test_db):
    purchase_service.create_purchase(
        purchase_date="2026-11-06",
        supplier_id=1,
        invoice_number="NF-100",
        items=[
            {
                "material_id": 1,
                "unit_id": 1,
                "quantity_milli": 1000000,
                "line_total_cents": 8500,
            }
        ],
    )

    purchase_service.create_purchase(
        purchase_date="2026-11-07",
        items=[
            {
                "material_id": 2,
                "unit_id": 1,
                "quantity_milli": 500000,
                "line_total_cents": 4000,
            }
        ],
    )

    purchases = purchase_service.list_purchases()

    assert len(purchases) == 2
    assert purchases[0]["purchase_date"] == "2026-11-07"
    assert purchases[1]["supplier_name"] == "Fornecedor de teste"
    assert purchases[1]["item_count"] == 1


def test_list_purchases_with_filters(test_db):
    purchase_service.create_purchase(
        purchase_date="2026-11-06",
        supplier_id=1,
        invoice_number="NF-100",
        items=[
            {
                "material_id": 1,
                "unit_id": 1,
                "quantity_milli": 1000000,
                "line_total_cents": 8500,
            }
        ],
    )

    purchase_service.create_purchase(
        purchase_date="2026-11-07",
        items=[
            {
                "material_id": 2,
                "unit_id": 1,
                "quantity_milli": 500000,
                "line_total_cents": 4000,
            }
        ],
    )

    purchases = purchase_service.list_purchases(
        supplier_id=1,
        invoice_number="100",
    )

    assert len(purchases) == 1
    assert purchases[0]["invoice_number"] == "NF-100"

    purchases = purchase_service.list_purchases(
        start_date="2026-11-07",
    )

    assert len(purchases) == 1
    assert purchases[0]["purchase_date"] == "2026-11-07"


def test_reverse_purchase_restores_stock(test_db):
    purchase_id = purchase_service.create_purchase(
        purchase_date="2026-11-07",
        items=[
            {
                "material_id": 1,
                "unit_id": 1,
                "quantity_milli": 1000000,
                "line_total_cents": 8500,
            },
            {
                "material_id": 2,
                "unit_id": 1,
                "quantity_milli": 500000,
                "line_total_cents": 4000,
            },
        ],
    )

    purchase_service.reverse_purchase(purchase_id)

    assert stock_service.get_stock_balance("material", 1) == 0
    assert stock_service.get_stock_balance("material", 2) == 0

    purchase = purchase_service.get_purchase(purchase_id)

    assert purchase is not None


def test_cannot_reverse_purchase_twice(test_db):
    purchase_id = purchase_service.create_purchase(
        purchase_date="2026-11-07",
        items=[
            {
                "material_id": 1,
                "unit_id": 1,
                "quantity_milli": 1000000,
                "line_total_cents": 8500,
            }
        ],
    )

    purchase_service.reverse_purchase(purchase_id)

    with pytest.raises(ValueError, match="já foi estornada"):
        purchase_service.reverse_purchase(purchase_id)


def test_cannot_reverse_purchase_after_material_consumption(test_db):
    purchase_id = purchase_service.create_purchase(
        purchase_date="2026-11-07",
        items=[
            {
                "material_id": 1,
                "unit_id": 1,
                "quantity_milli": 100000,
                "line_total_cents": 850,
            }
        ],
    )

    stock_service.register_stock_movement(
        "material",
        1,
        "production_consumption",
        -40000,
    )

    with pytest.raises(ValueError, match="estoque negativo"):
        purchase_service.reverse_purchase(purchase_id)

    assert stock_service.get_stock_balance("material", 1) == 60000
