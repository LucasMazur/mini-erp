
from fractions import Fraction

from app.database.connection import get_connection
from app.services.unit_converter import convert_quantity, get_unit_by_symbol


def _validate_recipe(product_id, name):
    if not name or not name.strip():
        raise ValueError("O nome da receita é obrigatório.")

    with get_connection() as connection:
        product = connection.execute(
            """
            SELECT id
            FROM products
            WHERE id = ? AND active = 1
            """,
            (product_id,),
        ).fetchone()

        if product is None:
            raise ValueError("Produto não encontrado ou inativo.")


def create_recipe(product_id, name, notes=None, is_default=False):
    """Cria uma receita e sua primeira versão vazia."""

    _validate_recipe(product_id, name)

    with get_connection() as connection:
        if is_default:
            connection.execute(
                """
                UPDATE product_recipes
                SET is_default = 0
                WHERE product_id = ?
                """,
                (product_id,),
            )

        cursor = connection.execute(
            """
            INSERT INTO product_recipes (
                product_id, name, is_default, notes
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                product_id,
                name.strip(),
                int(is_default),
                notes,
            ),
        )

        recipe_id = cursor.lastrowid

        connection.execute(
            """
            INSERT INTO recipe_versions (
                recipe_id, version_number
            )
            VALUES (?, 1)
            """,
            (recipe_id,),
        )

        return recipe_id


def _get_current_version(connection, recipe_id):
    """Retorna a versão mais recente de uma receita."""

    version = connection.execute(
        """
        SELECT id, version_number, finalized_at
        FROM recipe_versions
        WHERE recipe_id = ?
        ORDER BY version_number DESC
        LIMIT 1
        """,
        (recipe_id,),
    ).fetchone()

    if version is None:
        raise ValueError("A receita não possui uma versão.")

    if version["finalized_at"] is not None:
        raise ValueError("A versão atual já foi finalizada.")

    return dict(version)


def add_recipe_item(recipe_id, material_id, quantity, unit_symbol):
    """Adiciona um material à versão atual ainda não finalizada."""


    try:
        quantity_value = Fraction(str(quantity))
    except (ValueError, ZeroDivisionError):
        raise ValueError("A quantidade informada é inválida.")

    if quantity_value <= 0:
        raise ValueError("A quantidade deve ser maior que zero.")

    input_unit = get_unit_by_symbol(unit_symbol)

    with get_connection() as connection:
        version = _get_current_version(connection, recipe_id)

        material = connection.execute(
            """
            SELECT
                m.id,
                m.name,
                m.stock_unit_id,
                u.name AS stock_unit_name,
                u.symbol AS stock_unit_symbol,
                u.dimension,
                u.factor_num,
                u.factor_den,
                u.active AS unit_active
            FROM materials m
            JOIN units u ON u.id = m.stock_unit_id
            WHERE m.id = ? AND m.active = 1
            """,
            (material_id,),
        ).fetchone()

        if material is None:
            raise ValueError("Material não encontrado ou inativo.")

        if not material["unit_active"]:
            raise ValueError("A unidade de estoque do material está inativa.")

        stock_unit = dict(material)

        converted_quantity = convert_quantity(
            str(quantity_value),
            input_unit,
            stock_unit,
        )

        quantity_milli = converted_quantity * 1000

        if quantity_milli.denominator != 1:
            raise ValueError(
                "A quantidade convertida possui precisão maior "
                "que a permitida pela unidade de estoque."
            )

        quantity_milli = quantity_milli.numerator

        try:
            connection.execute(
                """
                INSERT INTO recipe_items (
                    recipe_version_id,
                    material_id,
                    quantity_milli,
                    material_name_snapshot,
                    unit_symbol_snapshot
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    version["id"],
                    material_id,
                    quantity_milli,
                    material["name"],
                    material["stock_unit_symbol"],
                ),
            )
        except Exception as error:
            if "UNIQUE constraint failed" in str(error):
                raise ValueError(
                    "Esse material já foi adicionado à versão da receita."
                ) from error
            raise

        return quantity_milli


def finalize_recipe_version(recipe_id):
    """Finaliza a versão atual da receita, impedindo alterações."""

    with get_connection() as connection:
        version = _get_current_version(connection, recipe_id)

        items = connection.execute(
            """
            SELECT COUNT(*) AS total
            FROM recipe_items
            WHERE recipe_version_id = ?
            """,
            (version["id"],),
        ).fetchone()

        if items["total"] == 0:
            raise ValueError(
                "Não é possível finalizar uma receita sem materiais."
            )

        connection.execute(
            """
            UPDATE recipe_versions
            SET finalized_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (version["id"],),
        )

        return version["id"]

def create_recipe_version(recipe_id, notes=None):
    """Cria uma nova versão vazia após finalizar a versão anterior."""

    with get_connection() as connection:
        previous_version = connection.execute(
            """
            SELECT id, version_number, finalized_at
            FROM recipe_versions
            WHERE recipe_id = ?
            ORDER BY version_number DESC
            LIMIT 1
            """,
            (recipe_id,),
        ).fetchone()

        if previous_version is None:
            raise ValueError("A receita não possui uma versão anterior.")

        if previous_version["finalized_at"] is None:
            raise ValueError(
                "Finalize a versão atual antes de criar outra."
            )

        new_version_number = previous_version["version_number"] + 1

        cursor = connection.execute(
            """
            INSERT INTO recipe_versions (
                recipe_id, version_number, notes
            )
            VALUES (?, ?, ?)
            """,
            (recipe_id, new_version_number, notes),
        )

        return cursor.lastrowid

def get_recipe(recipe_id):
    """Retorna uma receita com todas as suas versões e materiais."""

    with get_connection() as connection:
        recipe = connection.execute(
            """
            SELECT
                r.*,
                p.name AS product_name
            FROM product_recipes r
            JOIN products p ON p.id = r.product_id
            WHERE r.id = ?
            """,
            (recipe_id,),
        ).fetchone()

        if recipe is None:
            return None

        recipe = dict(recipe)

        versions = connection.execute(
            """
            SELECT *
            FROM recipe_versions
            WHERE recipe_id = ?
            ORDER BY version_number
            """,
            (recipe_id,),
        ).fetchall()

        recipe["versions"] = []

        for version_row in versions:
            version = dict(version_row)

            items = connection.execute(
                """
                SELECT
                    id,
                    material_id,
                    quantity_milli,
                    material_name_snapshot,
                    unit_symbol_snapshot
                FROM recipe_items
                WHERE recipe_version_id = ?
                ORDER BY material_name_snapshot
                """,
                (version["id"],),
            ).fetchall()

            version["items"] = [dict(item) for item in items]

            recipe["versions"].append(version)

        return recipe


def list_product_recipes(product_id):
    """Lista todas as receitas cadastradas para um produto."""

    with get_connection() as connection:
        recipes = connection.execute(
            """
            SELECT *
            FROM product_recipes
            WHERE product_id = ?
            ORDER BY is_default DESC, name
            """,
            (product_id,),
        ).fetchall()

        return [dict(recipe) for recipe in recipes]

def list_all_recipes(search=""):
    """Lista todas as receitas cadastradas, com seus produtos e versões."""

    with get_connection() as connection:
        recipes = connection.execute(
            """
            SELECT
                r.id,
                r.product_id,
                r.name,
                r.is_default,
                r.active,
                p.name AS product_name,
                v.version_number,
                v.finalized_at
            FROM product_recipes r
            JOIN products p ON p.id = r.product_id
            LEFT JOIN recipe_versions v
                ON v.id = (
                    SELECT rv.id
                    FROM recipe_versions rv
                    WHERE rv.recipe_id = r.id
                    ORDER BY rv.version_number DESC
                    LIMIT 1
                )
            WHERE
                r.name LIKE ?
                OR p.name LIKE ?
            ORDER BY p.name, r.is_default DESC, r.name
            """,
            (f"%{search}%", f"%{search}%"),
        ).fetchall()

        return [dict(recipe) for recipe in recipes]

def list_material_compatible_units(material_id):
    """Lista unidades ativas compatíveis com o material."""

    with get_connection() as connection:
        material = connection.execute(
            """
            SELECT u.dimension
            FROM materials m
            JOIN units u ON u.id = m.stock_unit_id
            WHERE m.id = ? AND m.active = 1
            """,
            (material_id,),
        ).fetchone()

        if material is None:
            raise ValueError("Material não encontrado ou inativo.")

        units = connection.execute(
            """
            SELECT id, name, symbol, dimension
            FROM units
            WHERE dimension = ? AND active = 1
            ORDER BY name
            """,
            (material["dimension"],),
        ).fetchall()

        return [dict(unit) for unit in units]