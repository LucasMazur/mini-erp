
from app.database.connection import get_connection


def initialize_database() -> None:
    """Aplica as migrações pendentes do banco de dados."""

    migrations = {
        1: [
            """
            CREATE TABLE categories (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                kind TEXT NOT NULL
                    CHECK (kind IN ('material', 'product')),
                active INTEGER NOT NULL DEFAULT 1
                    CHECK (active IN (0, 1)),
                UNIQUE (name, kind)
            )
            """,
            """
            CREATE TABLE units (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                symbol TEXT NOT NULL UNIQUE,
                dimension TEXT NOT NULL,
                factor_num INTEGER NOT NULL CHECK (factor_num > 0),
                factor_den INTEGER NOT NULL CHECK (factor_den > 0),
                is_base INTEGER NOT NULL DEFAULT 0
                    CHECK (is_base IN (0, 1)),
                active INTEGER NOT NULL DEFAULT 1
                    CHECK (active IN (0, 1))
            )
            """,
            """
            CREATE TABLE materials (
                id INTEGER PRIMARY KEY,
                code TEXT UNIQUE,
                name TEXT NOT NULL,
                category_id INTEGER,
                stock_unit_id INTEGER NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
                    CHECK (active IN (0, 1)),
                notes TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id)
                    REFERENCES categories(id) ON DELETE RESTRICT,
                FOREIGN KEY (stock_unit_id)
                    REFERENCES units(id) ON DELETE RESTRICT
            )
            """,
            """
            CREATE TABLE products (
                id INTEGER PRIMARY KEY,
                code TEXT UNIQUE,
                name TEXT NOT NULL,
                category_id INTEGER,
                stock_unit_id INTEGER NOT NULL,
                sale_price_cents INTEGER
                    CHECK (sale_price_cents IS NULL
                           OR sale_price_cents >= 0),
                active INTEGER NOT NULL DEFAULT 1
                    CHECK (active IN (0, 1)),
                notes TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id)
                    REFERENCES categories(id) ON DELETE RESTRICT,
                FOREIGN KEY (stock_unit_id)
                    REFERENCES units(id) ON DELETE RESTRICT
            )
            """,
        ],
        2: [
            """
            CREATE TABLE suppliers (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                document TEXT,
                phone TEXT,
                email TEXT,
                address TEXT,
                notes TEXT,
                active INTEGER NOT NULL DEFAULT 1
                    CHECK (active IN (0, 1)),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE purchases (
                id INTEGER PRIMARY KEY,
                supplier_id INTEGER,
                purchase_date TEXT NOT NULL,
                invoice_number TEXT,
                freight_cents INTEGER NOT NULL DEFAULT 0
                    CHECK (freight_cents >= 0),
                discount_cents INTEGER NOT NULL DEFAULT 0
                    CHECK (discount_cents >= 0),
                notes TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (supplier_id)
                    REFERENCES suppliers(id) ON DELETE RESTRICT
            )
            """,
            """
            CREATE TABLE purchase_items (
                id INTEGER PRIMARY KEY,
                purchase_id INTEGER NOT NULL,
                material_id INTEGER NOT NULL,
                unit_id INTEGER NOT NULL,
                quantity_milli INTEGER NOT NULL
                    CHECK (quantity_milli > 0),
                unit_cost_cents INTEGER NOT NULL
                    CHECK (unit_cost_cents >= 0),
                line_total_cents INTEGER NOT NULL
                    CHECK (line_total_cents >= 0),
                material_name_snapshot TEXT NOT NULL,
                unit_symbol_snapshot TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (purchase_id)
                    REFERENCES purchases(id) ON DELETE RESTRICT,
                FOREIGN KEY (material_id)
                    REFERENCES materials(id) ON DELETE RESTRICT,
                FOREIGN KEY (unit_id)
                    REFERENCES units(id) ON DELETE RESTRICT
            )
            """,
        ],
    }

    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        applied = {
            row["version"]
            for row in connection.execute(
                "SELECT version FROM schema_migrations"
            ).fetchall()
        }

        for version, statements in migrations.items():
            if version in applied:
                continue

            for statement in statements:
                connection.execute(statement)

            connection.execute(
                """
                INSERT INTO schema_migrations (version)
                VALUES (?)
                """,
                (version,),
            )


def get_database_version() -> int:
    """Retorna a última versão aplicada."""

    with get_connection() as connection:
        result = connection.execute(
            """
            SELECT MAX(version) AS version
            FROM schema_migrations
            """
        ).fetchone()

        return result["version"] or 0
