
import sqlite3

import pytest

from app.services import product_service


@pytest.fixture
def test_db(tmp_path, monkeypatch):
    database_path = tmp_path / "test_products.db"

    def get_test_connection():
        connection = sqlite3.connect(database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    monkeypatch.setattr(
        product_service,
        "get_connection",
        get_test_connection,
    )

    with get_test_connection() as connection:
        connection.executescript("""
            CREATE TABLE units (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                symbol TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE categories (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                kind TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE products (
                id INTEGER PRIMARY KEY,
                code TEXT UNIQUE,
                name TEXT NOT NULL,
                category_id INTEGER,
                stock_unit_id INTEGER NOT NULL,
                sale_price_cents INTEGER,
                active INTEGER NOT NULL DEFAULT 1,
                notes TEXT,
                image_path TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES categories(id),
                FOREIGN KEY (stock_unit_id) REFERENCES units(id)
            );

            INSERT INTO units (id, name, symbol)
            VALUES (1, 'Unidade', 'un');

            INSERT INTO categories (id, name, kind)
            VALUES
                (1, 'Brincos', 'product'),
                (2, 'Chaveiros', 'product'),
                (3, 'Filamentos', 'material');
        """)

    return get_test_connection


def test_create_product(test_db):
    product_id = product_service.create_product(
        name="Brinco Lua",
        stock_unit_id=1,
        code="BR001",
        category_id=1,
        sale_price_cents=3500,
        notes="Brinco de filamento PLA",
    )

    product = product_service.get_product(product_id)

    assert product["name"] == "Brinco Lua"
    assert product["code"] == "BR001"
    assert product["category_id"] == 1
    assert product["stock_unit_id"] == 1
    assert product["sale_price_cents"] == 3500
    assert product["unit_symbol"] == "un"


def test_create_product_without_category(test_db):
    product_id = product_service.create_product(
        name="Produto sem categoria",
        stock_unit_id=1,
    )

    product = product_service.get_product(product_id)

    assert product["category_id"] is None


def test_create_product_with_blank_name_fails(test_db):
    with pytest.raises(ValueError, match="nome"):
        product_service.create_product(
            name="   ",
            stock_unit_id=1,
        )


def test_create_product_with_invalid_unit_fails(test_db):
    with pytest.raises(ValueError, match="unidade"):
        product_service.create_product(
            name="Brinco Lua",
            stock_unit_id=999,
        )


def test_create_product_with_material_category_fails(test_db):
    with pytest.raises(ValueError, match="categoria"):
        product_service.create_product(
            name="Brinco Lua",
            stock_unit_id=1,
            category_id=3,
        )


def test_create_product_with_negative_price_fails(test_db):
    with pytest.raises(ValueError, match="preço"):
        product_service.create_product(
            name="Brinco Lua",
            stock_unit_id=1,
            sale_price_cents=-100,
        )


def test_list_products(test_db):
    product_service.create_product(
        name="Brinco Lua",
        stock_unit_id=1,
        code="BR001",
        category_id=1,
    )
    product_service.create_product(
        name="Chaveiro Estrela",
        stock_unit_id=1,
        code="CH001",
        category_id=2,
    )

    products = product_service.list_products()

    assert len(products) == 2


def test_list_products_with_search(test_db):
    product_service.create_product(
        name="Brinco Lua",
        stock_unit_id=1,
        code="BR001",
        category_id=1,
    )
    product_service.create_product(
        name="Chaveiro Estrela",
        stock_unit_id=1,
        code="CH001",
        category_id=2,
    )

    products = product_service.list_products(search="Lua")

    assert len(products) == 1
    assert products[0]["name"] == "Brinco Lua"


def test_update_product(test_db):
    product_id = product_service.create_product(
        name="Brinco Lua",
        stock_unit_id=1,
        category_id=1,
        sale_price_cents=3000,
    )

    product_service.update_product(
        product_id=product_id,
        name="Brinco Lua Novo",
        stock_unit_id=1,
        category_id=2,
        sale_price_cents=4000,
    )

    product = product_service.get_product(product_id)

    assert product["name"] == "Brinco Lua Novo"
    assert product["category_id"] == 2
    assert product["sale_price_cents"] == 4000


def test_deactivate_product(test_db):
    product_id = product_service.create_product(
        name="Brinco Lua",
        stock_unit_id=1,
    )

    product_service.deactivate_product(product_id)

    assert product_service.get_product(product_id)["active"] == 0
    assert product_service.list_products() == []
    assert len(product_service.list_products(include_inactive=True)) == 1
