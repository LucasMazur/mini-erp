import sqlite3

import pytest

from app.services import production_service, stock_service


@pytest.fixture
def recipe_data():
    return {
        "id": 1,
        "name": "Brinco Lua",
        "versions": [
            {
                "version_number": 1,
                "finalized_at": "2026-11-09 10:00:00",
                "items": [
                    {
                        "material_id": 10,
                        "material_name_snapshot": "PLA",
                        "unit_symbol_snapshot": "g",
                        "quantity_milli": 4000000,
                    },
                    {
                        "material_id": 20,
                        "material_name_snapshot": "Argola",
                        "unit_symbol_snapshot": "un",
                        "quantity_milli": 2000000,
                    },
                ],
            }
        ],
    }


def test_calculate_required_materials(monkeypatch, recipe_data):
    monkeypatch.setattr(
        production_service,
        "get_recipe",
        lambda recipe_id: recipe_data,
    )

    result = production_service.calculate_required_materials(1, 10)

    assert result["recipe_name"] == "Brinco Lua"
    assert result["production_quantity"] == 10
    assert result["version_number"] == 1
    assert result["materials"][0]["quantity_milli"] == 40000000
    assert result["materials"][1]["quantity_milli"] == 20000000


@pytest.mark.parametrize("quantity", [0, -1, 1.5, 2.0, "3", True])
def test_rejects_invalid_production_quantity(quantity):
    with pytest.raises(ValueError, match="inteiro"):
        production_service.calculate_required_materials(1, quantity)


def test_recipe_not_found(monkeypatch):
    monkeypatch.setattr(
        production_service,
        "get_recipe",
        lambda recipe_id: None,
    )

    with pytest.raises(ValueError, match="Receita não encontrada"):
        production_service.calculate_required_materials(999, 1)


def test_rejects_unfinalized_recipe(monkeypatch, recipe_data):
    recipe_data["versions"][0]["finalized_at"] = None

    monkeypatch.setattr(
        production_service,
        "get_recipe",
        lambda recipe_id: recipe_data,
    )

    with pytest.raises(ValueError, match="não foi finalizada"):
        production_service.calculate_required_materials(1, 5)


def test_rejects_recipe_without_materials(monkeypatch, recipe_data):
    recipe_data["versions"][0]["items"] = []

    monkeypatch.setattr(
        production_service,
        "get_recipe",
        lambda recipe_id: recipe_data,
    )

    with pytest.raises(ValueError, match="não possui materiais"):
        production_service.calculate_required_materials(1, 5)


def test_selects_specific_recipe_version(monkeypatch, recipe_data):
    recipe_data["versions"].append({
        "version_number": 2,
        "finalized_at": "2026-11-09 11:00:00",
        "items": [
            {
                "material_id": 30,
                "material_name_snapshot": "PLA especial",
                "unit_symbol_snapshot": "g",
                "quantity_milli": 5000000,
            }
        ],
    })

    monkeypatch.setattr(
        production_service,
        "get_recipe",
        lambda recipe_id: recipe_data,
    )

    result = production_service.calculate_required_materials(
        1,
        3,
        version_number=2,
    )

    assert result["version_number"] == 2
    assert len(result["materials"]) == 1
    assert result["materials"][0]["quantity_milli"] == 15000000

def test_check_production_stock_sufficient(monkeypatch):
    monkeypatch.setattr(
        production_service,
        "get_stock_balance",
        lambda item_type, item_id: {
            10: 100000000,
            20: 50000000,
        }[item_id],
    )

    materials = [
        {
            "material_id": 10,
            "material_name": "PLA",
            "quantity_milli": 40000000,
            "unit_symbol": "g",
        },
        {
            "material_id": 20,
            "material_name": "Argola",
            "quantity_milli": 20000000,
            "unit_symbol": "un",
        },
    ]

    result = production_service.check_production_stock(materials)

    assert result["sufficient"] is True
    assert len(result["shortages"]) == 0


def test_check_production_stock_insufficient(monkeypatch):
    monkeypatch.setattr(
        production_service,
        "get_stock_balance",
        lambda item_type, item_id: {
            10: 100000000,
            20: 12000000,
        }[item_id],
    )

    materials = [
        {
            "material_id": 10,
            "material_name": "PLA",
            "quantity_milli": 40000000,
            "unit_symbol": "g",
        },
        {
            "material_id": 20,
            "material_name": "Argola",
            "quantity_milli": 20000000,
            "unit_symbol": "un",
        },
    ]

    result = production_service.check_production_stock(materials)

    assert result["sufficient"] is False
    assert len(result["shortages"]) == 1
    assert result["shortages"][0]["material_name"] == "Argola"
    assert result["shortages"][0]["available_quantity_milli"] == 12000000


def test_check_production_stock_does_not_change_stock(monkeypatch):
    stock = {10: 100000000, 20: 50000000}

    monkeypatch.setattr(
        production_service,
        "get_stock_balance",
        lambda item_type, item_id: stock[item_id],
    )

    original_stock = stock.copy()

    materials = [
        {
            "material_id": 10,
            "material_name": "PLA",
            "quantity_milli": 40000000,
            "unit_symbol": "g",
        },
        {
            "material_id": 20,
            "material_name": "Argola",
            "quantity_milli": 20000000,
            "unit_symbol": "un",
        },
    ]

    production_service.check_production_stock(materials)

    assert stock == original_stock

@pytest.fixture
def production_db(tmp_path, monkeypatch):
    database_path = tmp_path / "test_production.db"

    def get_test_connection():
        connection = sqlite3.connect(database_path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    monkeypatch.setattr(
        production_service,
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

            CREATE TABLE product_recipes (
                id INTEGER PRIMARY KEY,
                product_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE recipe_versions (
                id INTEGER PRIMARY KEY,
                recipe_id INTEGER NOT NULL,
                version_number INTEGER NOT NULL,
                finalized_at TEXT
            );

            CREATE TABLE recipe_items (
                id INTEGER PRIMARY KEY,
                recipe_version_id INTEGER NOT NULL,
                material_id INTEGER NOT NULL,
                quantity_milli INTEGER NOT NULL,
                material_name_snapshot TEXT NOT NULL,
                unit_symbol_snapshot TEXT NOT NULL
            );

            CREATE TABLE productions (
                id INTEGER PRIMARY KEY,
                product_id INTEGER NOT NULL,
                recipe_id INTEGER NOT NULL,
                recipe_version_id INTEGER NOT NULL,
                product_name_snapshot TEXT NOT NULL,
                recipe_name_snapshot TEXT NOT NULL,
                recipe_version_number INTEGER NOT NULL,
                quantity_milli INTEGER NOT NULL,
                total_cost_cents INTEGER NOT NULL,
                occurred_at TEXT DEFAULT CURRENT_TIMESTAMP,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE production_items (
                id INTEGER PRIMARY KEY,
                production_id INTEGER NOT NULL,
                material_id INTEGER NOT NULL,
                quantity_milli INTEGER NOT NULL,
                total_cost_cents INTEGER NOT NULL,
                material_name_snapshot TEXT NOT NULL,
                unit_symbol_snapshot TEXT NOT NULL
            );

            CREATE TABLE stock_movements (
                id INTEGER PRIMARY KEY,
                material_id INTEGER,
                product_id INTEGER,
                movement_type TEXT NOT NULL,
                quantity_milli INTEGER NOT NULL,
                value_cents INTEGER NOT NULL DEFAULT 0,
                occurred_at TEXT DEFAULT CURRENT_TIMESTAMP,
                reference_type TEXT,
                reference_id INTEGER,
                notes TEXT,
                reversal_of_id INTEGER UNIQUE,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            INSERT INTO materials (id, name)
            VALUES (10, 'PLA'), (20, 'Argola');

            INSERT INTO products (id, name)
            VALUES (1, 'Brinco Lua');

            INSERT INTO product_recipes (
                id, product_id, name, active
            )
            VALUES (1, 1, 'Receita padrão', 1);

            INSERT INTO recipe_versions (
                id, recipe_id, version_number, finalized_at
            )
            VALUES (1, 1, 1, '2026-11-09 10:00:00');

            INSERT INTO recipe_items (
                id, recipe_version_id, material_id,
                quantity_milli, material_name_snapshot,
                unit_symbol_snapshot
            )
            VALUES
                (1, 1, 10, 4000000, 'PLA', 'g'),
                (2, 1, 20, 2000000, 'Argola', 'un');

            INSERT INTO stock_movements (
                material_id, movement_type,
                quantity_milli, value_cents
            )
            VALUES
                (10, 'purchase', 1000000000, 8500),
                (20, 'purchase', 100000000, 50000);
        """)

    return get_test_connection

def test_register_production_successfully(production_db):
    production_id = production_service.register_production(
        product_id=1,
        recipe_id=1,
        quantity=10,
    )

    with production_db() as connection:
        production = connection.execute(
            "SELECT * FROM productions WHERE id = ?",
            (production_id,),
        ).fetchone()

        items = connection.execute(
            """
            SELECT * FROM production_items
            WHERE production_id = ?
            ORDER BY material_id
            """,
            (production_id,),
        ).fetchall()

    assert production["quantity_milli"] == 10000000
    assert production["total_cost_cents"] == 10340
    assert production["product_name_snapshot"] == "Brinco Lua"
    assert production["recipe_version_number"] == 1

    assert len(items) == 2
    assert items[0]["quantity_milli"] == 40000000
    assert items[0]["total_cost_cents"] == 340
    assert items[1]["quantity_milli"] == 20000000
    assert items[1]["total_cost_cents"] == 10000

    assert stock_service.get_stock_balance("material", 10) == 960000000
    assert stock_service.get_stock_balance("material", 20) == 80000000
    assert stock_service.get_stock_balance("product", 1) == 10000000

    valuation = stock_service.get_stock_valuation("product", 1)
    assert valuation["value_cents"] == 10340

def test_insufficient_stock_does_not_register_production(production_db):
    with pytest.raises(ValueError, match="Estoque insuficiente"):
        production_service.register_production(
            product_id=1,
            recipe_id=1,
            quantity=300,
        )

    with production_db() as connection:
        production_count = connection.execute(
            "SELECT COUNT(*) FROM productions"
        ).fetchone()[0]

        movement_count = connection.execute(
            "SELECT COUNT(*) FROM stock_movements"
        ).fetchone()[0]

    assert production_count == 0
    assert movement_count == 2

    assert stock_service.get_stock_balance("material", 10) == 1000000000
    assert stock_service.get_stock_balance("material", 20) == 100000000
    assert stock_service.get_stock_balance("product", 1) == 0

def test_production_failure_rolls_back_all_movements(production_db):
    with production_db() as connection:
        connection.execute("""
            CREATE TRIGGER simulate_production_output_failure
            BEFORE INSERT ON stock_movements
            WHEN NEW.movement_type = 'production_output'
            BEGIN
                SELECT RAISE(ABORT, 'Falha simulada na produção');
            END;
        """)

    with pytest.raises(Exception, match="Falha simulada"):
        production_service.register_production(
            product_id=1,
            recipe_id=1,
            quantity=10,
        )

    with production_db() as connection:
        production_count = connection.execute(
            "SELECT COUNT(*) FROM productions"
        ).fetchone()[0]

        production_items_count = connection.execute(
            "SELECT COUNT(*) FROM production_items"
        ).fetchone()[0]

        movement_count = connection.execute(
            "SELECT COUNT(*) FROM stock_movements"
        ).fetchone()[0]

    assert production_count == 0
    assert production_items_count == 0
    assert movement_count == 2

    assert stock_service.get_stock_balance("material", 10) == 1000000000
    assert stock_service.get_stock_balance("material", 20) == 100000000
    assert stock_service.get_stock_balance("product", 1) == 0
