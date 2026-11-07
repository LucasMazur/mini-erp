import sqlite3

import pytest

from app.services import material_service


@pytest.fixture
def test_db(tmp_path, monkeypatch):
    database_path = tmp_path / "test_materials.db"

    def get_test_connection():
        connection = sqlite3.connect(database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    monkeypatch.setattr(
        material_service,
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

            CREATE TABLE materials (
                id INTEGER PRIMARY KEY,
                code TEXT,
                name TEXT NOT NULL,
                category_id INTEGER,
                stock_unit_id INTEGER NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                minimum_stock_quantity_milli INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (category_id) REFERENCES categories(id),
                FOREIGN KEY (stock_unit_id) REFERENCES units(id)
            );

            INSERT INTO units (id, name, symbol)
            VALUES (1, 'Grama', 'g');

            INSERT INTO categories (id, name, kind)
            VALUES (1, 'Filamentos', 'material');
        """)

    return get_test_connection


def test_create_material(test_db):
    material_id = material_service.create_material(
        name="PLA",
        stock_unit_id=1,
        code="PLA001",
        category_id=1,
        minimum_stock_quantity_milli=200000,
    )

    material = material_service.get_material(material_id)

    assert material["name"] == "PLA"
    assert material["code"] == "PLA001"
    assert material["unit_symbol"] == "g"
    assert material["minimum_stock_quantity_milli"] == 200000


def test_create_material_without_category(test_db):
    material_id = material_service.create_material(
        name="Resina",
        stock_unit_id=1,
    )

    material = material_service.get_material(material_id)

    assert material["name"] == "Resina"
    assert material["category_id"] is None


def test_create_material_with_blank_name_fails(test_db):
    with pytest.raises(ValueError):
        material_service.create_material(
            name=" ",
            stock_unit_id=1,
        )


def test_create_material_with_invalid_unit_fails(test_db):
    with pytest.raises(ValueError):
        material_service.create_material(
            name="PLA",
            stock_unit_id=999,
        )


def test_list_materials(test_db):
    material_service.create_material("PLA", 1)
    material_service.create_material("PETG", 1)

    materials = material_service.list_materials()

    assert len(materials) == 2


def test_update_material(test_db):
    material_id = material_service.create_material("PLA", 1)

    material_service.update_material(
        material_id=material_id,
        name="PLA Premium",
        stock_unit_id=1,
        code="PLA002",
    )

    material = material_service.get_material(material_id)

    assert material["name"] == "PLA Premium"
    assert material["code"] == "PLA002"


def test_deactivate_material(test_db):
    material_id = material_service.create_material("PLA", 1)

    material_service.deactivate_material(material_id)

    material = material_service.get_material(material_id)

    assert material["active"] == 0