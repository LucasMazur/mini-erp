
from app.database.connection import get_connection

with get_connection() as connection:
    tables = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = ? ORDER BY name",
        ("table",),
    ).fetchall()

    for table in tables:
        print(table["name"])
