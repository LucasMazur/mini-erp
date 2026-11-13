
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
        3: [
            """
            ALTER TABLE materials
            ADD COLUMN minimum_stock_quantity_milli INTEGER
            NOT NULL DEFAULT 0
            CHECK (minimum_stock_quantity_milli >= 0)
            """,
        ],
        4: [
            """
            CREATE TABLE stock_movements (
                id INTEGER PRIMARY KEY,

                material_id INTEGER,
                product_id INTEGER,

                movement_type TEXT NOT NULL CHECK (
                    movement_type IN (
                        'purchase',
                        'production_consumption',
                        'production_output',
                        'sale',
                        'adjustment_in',
                        'adjustment_out',
                        'reversal'
                    )
                ),

                quantity_milli INTEGER NOT NULL
                    CHECK (quantity_milli != 0),

                occurred_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                reference_type TEXT,
                reference_id INTEGER,
                notes TEXT,

                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

                CHECK (
                    (material_id IS NOT NULL AND product_id IS NULL)
                    OR
                    (material_id IS NULL AND product_id IS NOT NULL)
                ),

                CHECK (
                    movement_type = 'reversal'
                    OR
                    movement_type = 'adjustment_in'
                    OR
                    movement_type = 'adjustment_out'
                    OR
                    (movement_type IN ('purchase', 'production_output')
                     AND quantity_milli > 0)
                    OR
                    (movement_type IN ('production_consumption', 'sale')
                     AND quantity_milli < 0)
                ),

                CHECK (
                    movement_type NOT IN (
                        'purchase',
                        'production_consumption'
                    )
                    OR material_id IS NOT NULL
                ),

                CHECK (
                    movement_type NOT IN (
                        'production_output',
                        'sale'
                    )
                    OR product_id IS NOT NULL
                ),

                FOREIGN KEY (material_id)
                    REFERENCES materials(id) ON DELETE RESTRICT,

                FOREIGN KEY (product_id)
                    REFERENCES products(id) ON DELETE RESTRICT
            )
            """,
            """
            CREATE INDEX idx_stock_movements_material
            ON stock_movements(material_id, occurred_at)
            """,
            """
            CREATE INDEX idx_stock_movements_product
            ON stock_movements(product_id, occurred_at)
            """,
            """
            CREATE INDEX idx_stock_movements_reference
            ON stock_movements(reference_type, reference_id)
            """,
        ],
        5: [
            """
            ALTER TABLE stock_movements
            ADD COLUMN reversal_of_id INTEGER
            REFERENCES stock_movements(id) ON DELETE RESTRICT
            """,
            """
            CREATE UNIQUE INDEX idx_stock_movements_reversal
            ON stock_movements(reversal_of_id)
            WHERE reversal_of_id IS NOT NULL
            """,
        ],
        6: [
            """
            ALTER TABLE purchase_items
            ADD COLUMN landed_cost_cents INTEGER NOT NULL DEFAULT 0
            CHECK (landed_cost_cents >= 0)
            """,
            """
            ALTER TABLE stock_movements
            ADD COLUMN value_cents INTEGER NOT NULL DEFAULT 0
            """,
        ],
        7: [
            """
            CREATE TABLE product_recipes (
                id INTEGER PRIMARY KEY,
                product_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                is_default INTEGER NOT NULL DEFAULT 0
                    CHECK (is_default IN (0, 1)),
                active INTEGER NOT NULL DEFAULT 1
                    CHECK (active IN (0, 1)),
                notes TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id)
                    REFERENCES products(id) ON DELETE RESTRICT
            )
            """,
            """
            CREATE UNIQUE INDEX idx_product_recipes_default
            ON product_recipes(product_id)
            WHERE is_default = 1 AND active = 1
            """,
            """
            CREATE TABLE recipe_versions (
                id INTEGER PRIMARY KEY,
                recipe_id INTEGER NOT NULL,
                version_number INTEGER NOT NULL
                    CHECK (version_number > 0),
                notes TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (recipe_id, version_number),
                FOREIGN KEY (recipe_id)
                    REFERENCES product_recipes(id) ON DELETE RESTRICT
            )
            """,
            """
            CREATE TABLE recipe_items (
                id INTEGER PRIMARY KEY,
                recipe_version_id INTEGER NOT NULL,
                material_id INTEGER NOT NULL,
                quantity_milli INTEGER NOT NULL
                    CHECK (quantity_milli > 0),
                material_name_snapshot TEXT NOT NULL,
                unit_symbol_snapshot TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (recipe_version_id, material_id),
                FOREIGN KEY (recipe_version_id)
                    REFERENCES recipe_versions(id) ON DELETE RESTRICT,
                FOREIGN KEY (material_id)
                    REFERENCES materials(id) ON DELETE RESTRICT
            )
            """,
            """
            CREATE INDEX idx_product_recipes_product
            ON product_recipes(product_id)
            """,
            """
            CREATE INDEX idx_recipe_versions_recipe
            ON recipe_versions(recipe_id, version_number)
            """,
            """
            CREATE INDEX idx_recipe_items_version
            ON recipe_items(recipe_version_id)
            """,
        ],
        8: [
            """
            ALTER TABLE recipe_versions
            ADD COLUMN finalized_at TEXT
            """,
            """
            CREATE TRIGGER prevent_insert_into_finalized_recipe
            BEFORE INSERT ON recipe_items
            WHEN EXISTS (
                SELECT 1
                FROM recipe_versions
                WHERE id = NEW.recipe_version_id
                  AND finalized_at IS NOT NULL
            )
            BEGIN
                SELECT RAISE(ABORT, 'Versão da receita já finalizada.');
            END
            """,
            """
            CREATE TRIGGER prevent_update_finalized_recipe_item
            BEFORE UPDATE ON recipe_items
            WHEN EXISTS (
                SELECT 1
                FROM recipe_versions
                WHERE id = OLD.recipe_version_id
                  AND finalized_at IS NOT NULL
            )
            OR EXISTS (
                SELECT 1
                FROM recipe_versions
                WHERE id = NEW.recipe_version_id
                  AND finalized_at IS NOT NULL
            )
            BEGIN
                SELECT RAISE(ABORT, 'Versão da receita já finalizada.');
            END
            """,
            """
            CREATE TRIGGER prevent_delete_from_finalized_recipe
            BEFORE DELETE ON recipe_items
            WHEN EXISTS (
                SELECT 1
                FROM recipe_versions
                WHERE id = OLD.recipe_version_id
                  AND finalized_at IS NOT NULL
            )
            BEGIN
                SELECT RAISE(ABORT, 'Versão da receita já finalizada.');
            END
            """,
            """
            CREATE TRIGGER prevent_update_finalized_recipe_version
            BEFORE UPDATE ON recipe_versions
            WHEN OLD.finalized_at IS NOT NULL
            BEGIN
                SELECT RAISE(ABORT, 'Versão da receita já finalizada.');
            END
            """,
            """
            CREATE TRIGGER prevent_delete_finalized_recipe_version
            BEFORE DELETE ON recipe_versions
            WHEN OLD.finalized_at IS NOT NULL
            BEGIN
                SELECT RAISE(ABORT, 'Versão da receita já finalizada.');
            END
            """,
        ],
        
        9: [
            """
            CREATE TABLE productions (
                id INTEGER PRIMARY KEY,
                product_id INTEGER NOT NULL,
                recipe_id INTEGER NOT NULL,
                recipe_version_id INTEGER NOT NULL,

                product_name_snapshot TEXT NOT NULL,
                recipe_name_snapshot TEXT NOT NULL,
                recipe_version_number INTEGER NOT NULL
                    CHECK (recipe_version_number > 0),

                quantity_milli INTEGER NOT NULL
                    CHECK (quantity_milli > 0),

                total_cost_cents INTEGER NOT NULL
                    CHECK (total_cost_cents >= 0),

                occurred_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                notes TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (product_id)
                    REFERENCES products(id) ON DELETE RESTRICT,

                FOREIGN KEY (recipe_id)
                    REFERENCES product_recipes(id) ON DELETE RESTRICT,

                FOREIGN KEY (recipe_version_id)
                    REFERENCES recipe_versions(id) ON DELETE RESTRICT
            )
            """,
            """
            CREATE TABLE production_items (
                id INTEGER PRIMARY KEY,
                production_id INTEGER NOT NULL,
                material_id INTEGER NOT NULL,

                quantity_milli INTEGER NOT NULL
                    CHECK (quantity_milli > 0),

                total_cost_cents INTEGER NOT NULL
                    CHECK (total_cost_cents >= 0),

                material_name_snapshot TEXT NOT NULL,
                unit_symbol_snapshot TEXT NOT NULL,

                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (production_id)
                    REFERENCES productions(id) ON DELETE RESTRICT,

                FOREIGN KEY (material_id)
                    REFERENCES materials(id) ON DELETE RESTRICT
            )
            """,
            """
            CREATE INDEX idx_productions_product
            ON productions(product_id, occurred_at)
            """,
            """
            CREATE INDEX idx_productions_recipe
            ON productions(recipe_id, recipe_version_id)
            """,
            """
            CREATE INDEX idx_production_items_production
            ON production_items(production_id)
            """,
            """
            CREATE INDEX idx_production_items_material
            ON production_items(material_id)
            """,
        ],
        10: [
            """
            CREATE TABLE sales (
                id INTEGER PRIMARY KEY,
                sale_date TEXT NOT NULL,
                subtotal_cents INTEGER NOT NULL CHECK (subtotal_cents >= 0),
                discount_cents INTEGER NOT NULL DEFAULT 0 CHECK (discount_cents >= 0),
                total_cents INTEGER NOT NULL CHECK (total_cents >= 0),
                payment_method TEXT NOT NULL,
                notes TEXT,
                reversed_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE sale_items (
                id INTEGER PRIMARY KEY,
                sale_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity_milli INTEGER NOT NULL CHECK (quantity_milli > 0),
                unit_price_cents INTEGER NOT NULL CHECK (unit_price_cents >= 0),
                line_total_cents INTEGER NOT NULL CHECK (line_total_cents >= 0),
                product_name_snapshot TEXT NOT NULL,
                unit_symbol_snapshot TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sale_id) REFERENCES sales(id) ON DELETE RESTRICT,
                FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT
            )
            """,
            """
            CREATE INDEX idx_sales_date ON sales(sale_date, id)
            """,
            """
            CREATE INDEX idx_sale_items_sale ON sale_items(sale_id)
            """,
            """
            CREATE INDEX idx_sale_items_product ON sale_items(product_id)
            """,
        ],
        11: [
            """
            ALTER TABLE products
            ADD COLUMN image_path TEXT
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
