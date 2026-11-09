
import sqlite3

import pytest

from app.services import recipe_service


@pytest.fixture
def test_db(tmp_path, monkeypatch):
    database_path = tmp_path / "test_recipes.db"

    def get_test_connection():
        connection = sqlite3.connect(database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    monkeypatch.setattr(
        recipe_service,
        "get_connection",
        get_test_connection,
    )

    with get_test_connection() as connection:
        connection.executescript("""
            CREATE TABLE products (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE product_recipes (
                id INTEGER PRIMARY KEY,
                product_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                is_default INTEGER NOT NULL DEFAULT 0,
                active INTEGER NOT NULL DEFAULT 1,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products(id)
            );

            CREATE TABLE recipe_versions (
                id INTEGER PRIMARY KEY,
                recipe_id INTEGER NOT NULL,
                version_number INTEGER NOT NULL,
                notes TEXT,
                finalized_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (recipe_id, version_number),
                FOREIGN KEY (recipe_id) REFERENCES product_recipes(id)
            );

            INSERT INTO products (id, name)
            VALUES
                (1, 'Brinco Lua'),
                (2, 'Chaveiro Estrela');

            INSERT INTO products (id, name, active)
            VALUES (3, 'Produto Inativo', 0);
        """)

    return get_test_connection


def test_create_recipe(test_db):
    recipe_id = recipe_service.create_recipe(
        product_id=1,
        name="Receita PLA",
        notes="Receita tradicional",
    )

    with test_db() as connection:
        recipe = connection.execute(
            "SELECT * FROM product_recipes WHERE id = ?",
            (recipe_id,),
        ).fetchone()

        version = connection.execute(
            "SELECT * FROM recipe_versions WHERE recipe_id = ?",
            (recipe_id,),
        ).fetchone()

    assert recipe["name"] == "Receita PLA"
    assert recipe["product_id"] == 1
    assert recipe["is_default"] == 0
    assert version["version_number"] == 1


def test_create_default_recipe(test_db):
    recipe_id = recipe_service.create_recipe(
        product_id=1,
        name="Receita padrão",
        is_default=True,
    )

    with test_db() as connection:
        recipe = connection.execute(
            "SELECT * FROM product_recipes WHERE id = ?",
            (recipe_id,),
        ).fetchone()

    assert recipe["is_default"] == 1


def test_create_recipe_with_blank_name_fails(test_db):
    with pytest.raises(ValueError, match="nome"):
        recipe_service.create_recipe(
            product_id=1,
            name="   ",
        )


def test_create_recipe_for_nonexistent_product_fails(test_db):
    with pytest.raises(ValueError, match="Produto"):
        recipe_service.create_recipe(
            product_id=999,
            name="Receita inválida",
        )


def test_create_recipe_for_inactive_product_fails(test_db):
    with pytest.raises(ValueError, match="Produto"):
        recipe_service.create_recipe(
            product_id=3,
            name="Receita inválida",
        )


def test_product_can_have_multiple_recipes(test_db):
    first_id = recipe_service.create_recipe(
        product_id=1,
        name="Receita PLA",
    )

    second_id = recipe_service.create_recipe(
        product_id=1,
        name="Receita Resina",
    )

    assert first_id != second_id

    with test_db() as connection:
        recipes = connection.execute(
            "SELECT * FROM product_recipes WHERE product_id = ?",
            (1,),
        ).fetchall()

    assert len(recipes) == 2


def test_add_recipe_item(test_db, monkeypatch):

    with test_db() as connection:
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

            CREATE TABLE materials (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                stock_unit_id INTEGER NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (stock_unit_id) REFERENCES units(id)
            );

            CREATE TABLE recipe_items (
                id INTEGER PRIMARY KEY,
                recipe_version_id INTEGER NOT NULL,
                material_id INTEGER NOT NULL,
                quantity_milli INTEGER NOT NULL,
                material_name_snapshot TEXT NOT NULL,
                unit_symbol_snapshot TEXT NOT NULL,
                UNIQUE (recipe_version_id, material_id),
                FOREIGN KEY (recipe_version_id)
                    REFERENCES recipe_versions(id),
                FOREIGN KEY (material_id) REFERENCES materials(id)
            );

            INSERT INTO units (
                id, name, symbol, dimension, factor_num, factor_den, is_base
            )
            VALUES (1, 'Grama', 'g', 'mass', 1000, 1, 1);

            INSERT INTO materials (id, name, stock_unit_id)
            VALUES (1, 'PLA', 1);
        """)

    recipe_id = recipe_service.create_recipe(
        product_id=1,
        name="Receita PLA",
    )

    quantity = recipe_service.add_recipe_item(
        recipe_id=recipe_id,
        material_id=1,
        quantity="4",
        unit_symbol="g",
    )

    assert quantity == 4000

    with test_db() as connection:
        item = connection.execute(
            "SELECT * FROM recipe_items"
        ).fetchone()

    assert item["material_name_snapshot"] == "PLA"
    assert item["unit_symbol_snapshot"] == "g"


def test_add_recipe_item_rejects_invalid_quantity(test_db):
    with test_db() as connection:
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

            CREATE TABLE materials (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                stock_unit_id INTEGER NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE recipe_items (
                id INTEGER PRIMARY KEY,
                recipe_version_id INTEGER NOT NULL,
                material_id INTEGER NOT NULL,
                quantity_milli INTEGER NOT NULL,
                material_name_snapshot TEXT NOT NULL,
                unit_symbol_snapshot TEXT NOT NULL,
                UNIQUE (recipe_version_id, material_id)
            );

            INSERT INTO units
            VALUES (1, 'Grama', 'g', 'mass', 1000, 1, 1, 1);

            INSERT INTO materials
            VALUES (1, 'PLA', 1, 1);
        """)

    recipe_id = recipe_service.create_recipe(1, "Receita PLA")

    with pytest.raises(ValueError, match="maior que zero"):
        recipe_service.add_recipe_item(
            recipe_id, 1, "0", "g"
        )

def test_finalize_recipe_version(test_db):
    with test_db() as connection:
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

            CREATE TABLE materials (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                stock_unit_id INTEGER NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE recipe_items (
                id INTEGER PRIMARY KEY,
                recipe_version_id INTEGER NOT NULL,
                material_id INTEGER NOT NULL,
                quantity_milli INTEGER NOT NULL,
                material_name_snapshot TEXT NOT NULL,
                unit_symbol_snapshot TEXT NOT NULL,
                UNIQUE (recipe_version_id, material_id)
            );

            INSERT INTO units
            VALUES (1, 'Grama', 'g', 'mass', 1000, 1, 1, 1);

            INSERT INTO materials
            VALUES (1, 'PLA', 1, 1);
        """)

    recipe_id = recipe_service.create_recipe(1, "Receita PLA")

    recipe_service.add_recipe_item(
        recipe_id, 1, "4", "g"
    )

    version_id = recipe_service.finalize_recipe_version(recipe_id)

    with test_db() as connection:
        version = connection.execute(
            "SELECT * FROM recipe_versions WHERE id = ?",
            (version_id,),
        ).fetchone()

    assert version["finalized_at"] is not None



def test_cannot_finalize_empty_recipe(test_db):
    with test_db() as connection:
        connection.execute("""
            CREATE TABLE recipe_items (
                id INTEGER PRIMARY KEY,
                recipe_version_id INTEGER NOT NULL,
                material_id INTEGER NOT NULL,
                quantity_milli INTEGER NOT NULL,
                material_name_snapshot TEXT NOT NULL,
                unit_symbol_snapshot TEXT NOT NULL
            )
        """)

    recipe_id = recipe_service.create_recipe(1, "Receita vazia")

    with pytest.raises(ValueError, match="sem materiais"):
        recipe_service.finalize_recipe_version(recipe_id)



def test_cannot_finalize_recipe_twice(test_db):
    with test_db() as connection:
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

            CREATE TABLE materials (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                stock_unit_id INTEGER NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE recipe_items (
                id INTEGER PRIMARY KEY,
                recipe_version_id INTEGER NOT NULL,
                material_id INTEGER NOT NULL,
                quantity_milli INTEGER NOT NULL,
                material_name_snapshot TEXT NOT NULL,
                unit_symbol_snapshot TEXT NOT NULL,
                UNIQUE (recipe_version_id, material_id)
            );

            INSERT INTO units
            VALUES (1, 'Grama', 'g', 'mass', 1000, 1, 1, 1);

            INSERT INTO materials
            VALUES (1, 'PLA', 1, 1);
        """)

    recipe_id = recipe_service.create_recipe(1, "Receita PLA")

    recipe_service.add_recipe_item(
        recipe_id, 1, "4", "g"
    )

    recipe_service.finalize_recipe_version(recipe_id)

    with pytest.raises(ValueError, match="finalizada"):
        recipe_service.finalize_recipe_version(recipe_id)

def test_create_new_recipe_version_copies_items(test_db):
    with test_db() as connection:
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

            CREATE TABLE materials (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                stock_unit_id INTEGER NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE recipe_items (
                id INTEGER PRIMARY KEY,
                recipe_version_id INTEGER NOT NULL,
                material_id INTEGER NOT NULL,
                quantity_milli INTEGER NOT NULL,
                material_name_snapshot TEXT NOT NULL,
                unit_symbol_snapshot TEXT NOT NULL,
                UNIQUE (recipe_version_id, material_id)
            );

            INSERT INTO units
            VALUES (1, 'Grama', 'g', 'mass', 1000, 1, 1, 1);

            INSERT INTO materials
            VALUES (1, 'PLA', 1, 1);
        """)

    recipe_id = recipe_service.create_recipe(1, "Receita PLA")

    recipe_service.add_recipe_item(recipe_id, 1, "4", "g")
    recipe_service.finalize_recipe_version(recipe_id)

    new_version_id = recipe_service.create_recipe_version(
        recipe_id,
        notes="Ajuste da receita",
    )

    with test_db() as connection:
        new_version = connection.execute(
            "SELECT * FROM recipe_versions WHERE id = ?",
            (new_version_id,),
        ).fetchone()

        items = connection.execute(
            "SELECT * FROM recipe_items WHERE recipe_version_id = ?",
            (new_version_id,),
        ).fetchall()

    assert new_version["version_number"] == 2
    assert new_version["notes"] == "Ajuste da receita"
    assert len(items) == 1
    assert items[0]["material_id"] == 1
    assert items[0]["quantity_milli"] == 4000


def test_cannot_create_new_version_before_finalizing(test_db):
    recipe_id = recipe_service.create_recipe(1, "Receita PLA")

    with pytest.raises(ValueError, match="Finalize"):
        recipe_service.create_recipe_version(recipe_id)


def test_previous_recipe_version_remains_unchanged(test_db):
    with test_db() as connection:
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

            CREATE TABLE materials (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                stock_unit_id INTEGER NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE recipe_items (
                id INTEGER PRIMARY KEY,
                recipe_version_id INTEGER NOT NULL,
                material_id INTEGER NOT NULL,
                quantity_milli INTEGER NOT NULL,
                material_name_snapshot TEXT NOT NULL,
                unit_symbol_snapshot TEXT NOT NULL,
                UNIQUE (recipe_version_id, material_id)
            );

            INSERT INTO units
            VALUES (1, 'Grama', 'g', 'mass', 1000, 1, 1, 1);

            INSERT INTO materials
            VALUES (1, 'PLA', 1, 1);
        """)

    recipe_id = recipe_service.create_recipe(1, "Receita PLA")
    recipe_service.add_recipe_item(recipe_id, 1, "4", "g")
    recipe_service.finalize_recipe_version(recipe_id)

    recipe_service.create_recipe_version(recipe_id)

    with test_db() as connection:
        old_item = connection.execute(
            """
            SELECT ri.quantity_milli
            FROM recipe_items ri
            JOIN recipe_versions rv
                ON rv.id = ri.recipe_version_id
            WHERE rv.recipe_id = ? AND rv.version_number = 1
            """,
            (recipe_id,),
        ).fetchone()

    assert old_item["quantity_milli"] == 4000

def test_get_recipe_with_versions_and_items(test_db):
    with test_db() as connection:
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

            CREATE TABLE materials (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                stock_unit_id INTEGER NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE recipe_items (
                id INTEGER PRIMARY KEY,
                recipe_version_id INTEGER NOT NULL,
                material_id INTEGER NOT NULL,
                quantity_milli INTEGER NOT NULL,
                material_name_snapshot TEXT NOT NULL,
                unit_symbol_snapshot TEXT NOT NULL,
                UNIQUE (recipe_version_id, material_id)
            );

            INSERT INTO units
            VALUES (1, 'Grama', 'g', 'mass', 1000, 1, 1, 1);

            INSERT INTO materials
            VALUES (1, 'PLA', 1, 1);
        """)

    recipe_id = recipe_service.create_recipe(
        1, "Receita PLA", is_default=True
    )

    recipe_service.add_recipe_item(recipe_id, 1, "4", "g")
    recipe_service.finalize_recipe_version(recipe_id)
    recipe_service.create_recipe_version(recipe_id)

    recipe = recipe_service.get_recipe(recipe_id)

    assert recipe["name"] == "Receita PLA"
    assert recipe["product_name"] == "Brinco Lua"
    assert recipe["is_default"] == 1
    assert len(recipe["versions"]) == 2
    assert recipe["versions"][0]["items"][0]["quantity_milli"] == 4000
    assert recipe["versions"][1]["items"][0]["quantity_milli"] == 4000


def test_get_nonexistent_recipe_returns_none(test_db):
    assert recipe_service.get_recipe(999) is None


def test_list_product_recipes(test_db):
    recipe_service.create_recipe(1, "Receita PLA")
    recipe_service.create_recipe(
        1, "Receita Resina", is_default=True
    )

    recipes = recipe_service.list_product_recipes(1)

    assert len(recipes) == 2
    assert recipes[0]["name"] == "Receita Resina"
    assert recipes[0]["is_default"] == 1


def test_list_product_recipes_for_product_without_recipes(test_db):
    recipes = recipe_service.list_product_recipes(2)

    assert recipes == []
