
from app.database.connection import get_connection

DEFAULT_UNITS = [
    # Contagem: unidade-base = unidade
    ("Unidade", "un", "count", 1000, 1, 1),
    ("Par", "par", "count", 2000, 1, 0),
    ("Dúzia", "dz", "count", 12000, 1, 0),

    # Massa: unidade-base = grama
    ("Miligrama", "mg", "mass", 1, 1, 0),
    ("Grama", "g", "mass", 1000, 1, 1),
    ("Quilograma", "kg", "mass", 1000000, 1, 0),

    # Volume: unidade-base = mililitro
    ("Mililitro", "ml", "volume", 1000, 1, 1),
    ("Litro", "l", "volume", 1000000, 1, 0),

    # Comprimento: unidade-base = milímetro
    ("Milímetro", "mm", "length", 1000, 1, 1),
    ("Centímetro", "cm", "length", 10000, 1, 0),
    ("Metro", "m", "length", 1000000, 1, 0),
]


def seed_units() -> None:
    """Insere as unidades padrão sem duplicar registros."""

    with get_connection() as connection:
        connection.executemany(
            """
            INSERT OR IGNORE INTO units (
                name,
                symbol,
                dimension,
                factor_num,
                factor_den,
                is_base
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            DEFAULT_UNITS,
        )


if __name__ == "__main__":
    seed_units()
    print("Unidades padrão cadastradas com sucesso!")
