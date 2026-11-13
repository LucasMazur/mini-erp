from app.database.connection import get_connection


def create_transaction(
    transaction_date,
    direction,
    description,
    amount_cents,
    category=None,
    payment_method=None,
):
    if not transaction_date:
        raise ValueError("Informe a data do lançamento.")
    if direction not in {"income", "expense"}:
        raise ValueError("Tipo de lançamento inválido.")
    if not description or not description.strip():
        raise ValueError("Informe a descrição.")
    if not isinstance(amount_cents, int) or isinstance(amount_cents, bool) or amount_cents <= 0:
        raise ValueError("O valor deve ser um inteiro positivo em centavos.")

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO financial_transactions (
                transaction_date, direction, description, amount_cents,
                category, payment_method, origin
            )
            VALUES (?, ?, ?, ?, ?, ?, 'manual')
            """,
            (
                transaction_date,
                direction,
                description.strip(),
                amount_cents,
                category.strip() if category and category.strip() else None,
                payment_method,
            ),
        )
        return cursor.lastrowid


def list_transactions(start_date=None, end_date=None, direction=None):
    query = "SELECT * FROM financial_transactions WHERE 1 = 1"
    parameters = []
    if start_date:
        query += " AND transaction_date >= ?"
        parameters.append(start_date)
    if end_date:
        query += " AND transaction_date <= ?"
        parameters.append(end_date)
    if direction in {"income", "expense"}:
        query += " AND direction = ?"
        parameters.append(direction)
    query += " ORDER BY transaction_date DESC, id DESC"

    with get_connection() as connection:
        return [dict(row) for row in connection.execute(query, parameters)]


def get_financial_summary(start_date=None, end_date=None):
    query = """
        SELECT
            COALESCE(SUM(CASE WHEN direction = 'income'
                THEN amount_cents ELSE 0 END), 0) AS income_cents,
            COALESCE(SUM(CASE WHEN direction = 'expense'
                THEN amount_cents ELSE 0 END), 0) AS expense_cents
        FROM financial_transactions
        WHERE 1 = 1
    """
    parameters = []
    if start_date:
        query += " AND transaction_date >= ?"
        parameters.append(start_date)
    if end_date:
        query += " AND transaction_date <= ?"
        parameters.append(end_date)

    with get_connection() as connection:
        row = connection.execute(query, parameters).fetchone()

    income = row["income_cents"]
    expense = row["expense_cents"]
    return {
        "income_cents": income,
        "expense_cents": expense,
        "balance_cents": income - expense,
    }
