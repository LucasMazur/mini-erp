
import sqlite3
from pathlib import Path


def get_database_path() -> Path:
    """Retorna o caminho do banco de dados durante o desenvolvimento."""
    project_root = Path(__file__).resolve().parents[2]
    data_directory = project_root / "data"

    data_directory.mkdir(parents=True, exist_ok=True)

    return data_directory / "mini_erp.db"


def get_connection() -> sqlite3.Connection:
    """Abre uma conexão configurada com o banco de dados."""
    database_path = get_database_path()

    connection = sqlite3.connect(
        database_path,
        timeout=30,
    )

    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA busy_timeout = 30000")

    return connection