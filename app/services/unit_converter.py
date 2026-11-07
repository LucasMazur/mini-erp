
from fractions import Fraction

from app.database.connection import get_connection


def get_unit_by_symbol(symbol: str) -> dict:
    """Busca uma unidade cadastrada pelo símbolo."""

    with get_connection() as connection:
        unit = connection.execute(
            """
            SELECT id, name, symbol, dimension,
                   factor_num, factor_den, is_base
            FROM units
            WHERE symbol = ? AND active = 1
            """,
            (symbol,),
        ).fetchone()

    if unit is None:
        raise ValueError(f"Unidade não encontrada: {symbol}")

    return dict(unit)


def convert_quantity(
    quantity: str,
    from_unit: dict,
    to_unit: dict,
) -> Fraction:
    """Converte quantidades entre unidades compatíveis."""

    if from_unit["dimension"] != to_unit["dimension"]:
        raise ValueError(
            "Não é possível converter unidades de categorias diferentes."
        )

    quantity_value = Fraction(quantity)

    source_factor = Fraction(
        from_unit["factor_num"],
        from_unit["factor_den"],
    )

    target_factor = Fraction(
        to_unit["factor_num"],
        to_unit["factor_den"],
    )

    return quantity_value * source_factor / target_factor


def convert_by_symbol(
    quantity: str,
    from_symbol: str,
    to_symbol: str,
) -> Fraction:
    """Busca as unidades no banco e realiza a conversão."""

    from_unit = get_unit_by_symbol(from_symbol)
    to_unit = get_unit_by_symbol(to_symbol)

    return convert_quantity(quantity, from_unit, to_unit)
