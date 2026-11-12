import sqlite3

import pytest

from app.services import sales_service, stock_service


@pytest.fixture
def sales_db(tmp_path, monkeypatch):
    database_path = tmp_path / "test_sales.db"

    def get_test_connection():
        connection = sqlite3.connect(database_path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    monkeypatch.setattr(sales_service, "get_connection", get_test_connection)
    monkeypatch.setattr(stock_service, "get_connection", get_test_connection)

    with get_test_connection() as connection:
        connection.executescript("""
            CREATE TABLE units (
                id INTEGER PRIMARY KEY,
                symbol TEXT NOT NULL
            );
            CREATE TABLE products (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                stock_unit_id INTEGER NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (stock_unit_id) REFERENCES units(id)
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
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE sales (
                id INTEGER PRIMARY KEY,
                sale_date TEXT NOT NULL,
                subtotal_cents INTEGER NOT NULL,
                discount_cents INTEGER NOT NULL,
                total_cents INTEGER NOT NULL,
                payment_method TEXT NOT NULL,
                notes TEXT,
                reversed_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE sale_items (
                id INTEGER PRIMARY KEY,
                sale_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity_milli INTEGER NOT NULL,
                unit_price_cents INTEGER NOT NULL,
                line_total_cents INTEGER NOT NULL,
                product_name_snapshot TEXT NOT NULL,
                unit_symbol_snapshot TEXT NOT NULL
            );
            INSERT INTO units (id, symbol) VALUES (1, 'un');
            INSERT INTO products (id, name, stock_unit_id)
            VALUES (1, 'Brinco Lua', 1);
        """)

    stock_service._register_stock_movement(
        get_test_connection(),
        "product",
        1,
        "production_output",
        50000,
        reference_type="production",
        reference_id=1,
        value_cents=4450,
    )
    return get_test_connection


def test_create_sale_records_items_and_reduces_stock(sales_db):
    sale_id = sales_service.create_sale(
        "2026-11-12",
        [{"product_id": 1, "quantity": 2, "unit_price_cents": 1500}],
        "Pix",
        discount_cents=100,
    )

    sale = sales_service.get_sale(sale_id)
    assert sale["subtotal_cents"] == 3000
    assert sale["discount_cents"] == 100
    assert sale["total_cents"] == 2900
    assert sale["items"][0]["quantity_milli"] == 2000
    assert stock_service.get_stock_balance("product", 1) == 48000


def test_sale_rejects_insufficient_stock_without_partial_records(sales_db):
    with pytest.raises(ValueError, match="Estoque insuficiente"):
        sales_service.create_sale(
            "2026-11-12",
            [{"product_id": 1, "quantity": 51, "unit_price_cents": 1500}],
            "Pix",
        )

    with sales_db() as connection:
        assert connection.execute("SELECT COUNT(*) FROM sales").fetchone()[0] == 0
    assert stock_service.get_stock_balance("product", 1) == 50000


def test_sale_rejects_discount_above_subtotal(sales_db):
    with pytest.raises(ValueError, match="desconto"):
        sales_service.create_sale(
            "2026-11-12",
            [{"product_id": 1, "quantity": 1, "unit_price_cents": 1000}],
            "Pix",
            discount_cents=1001,
        )


def test_reverse_sale_restores_product_stock(sales_db):
    sale_id = sales_service.create_sale(
        "2026-11-12",
        [{"product_id": 1, "quantity": 3, "unit_price_cents": 1500}],
        "Dinheiro",
    )

    sales_service.reverse_sale(sale_id)

    assert stock_service.get_stock_balance("product", 1) == 50000
    assert sales_service.get_sale(sale_id)["reversed_at"] is not None


def test_sale_cannot_be_reversed_twice(sales_db):
    sale_id = sales_service.create_sale(
        "2026-11-12",
        [{"product_id": 1, "quantity": 1, "unit_price_cents": 1500}],
        "Pix",
    )
    sales_service.reverse_sale(sale_id)

    with pytest.raises(ValueError, match="já foi estornada"):
        sales_service.reverse_sale(sale_id)
