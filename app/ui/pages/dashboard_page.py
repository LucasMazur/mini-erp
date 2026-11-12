from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from app.database.connection import get_connection


class DashboardPage(QWidget):
    def __init__(self):
        super().__init__()
        self.value_labels = {}
        self._create_interface()
        self.refresh_data()

    def _create_interface(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(35, 30, 35, 30)
        layout.setSpacing(20)

        title = QLabel("Visão geral")
        title.setObjectName("page_title")
        layout.addWidget(title)

        subtitle = QLabel(
            "Acompanhe os principais indicadores do seu negócio."
        )
        subtitle.setObjectName("page_subtitle")
        layout.addWidget(subtitle)

        cards_layout = QGridLayout()
        cards_layout.setSpacing(18)

        indicators = [
            ("Vendas do mês", "sales_month", "R$ 0,00"),
            ("Produtos em estoque", "products_stock", "0"),
            ("Produções realizadas", "productions", "0"),
            ("Resultado financeiro", "financial", "Em desenvolvimento"),
        ]

        for index, (name, key, value) in enumerate(indicators):
            card, value_label = self._create_card(name, value)
            self.value_labels[key] = value_label
            cards_layout.addWidget(card, index // 2, index % 2)

        layout.addLayout(cards_layout)
        layout.addStretch()

    def _create_card(self, name, value):
        card = QFrame()
        card.setObjectName("dashboard_card")

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(22, 20, 22, 20)
        card_layout.setSpacing(12)

        name_label = QLabel(name)
        name_label.setObjectName("card_name")

        value_label = QLabel(value)
        value_label.setObjectName("card_value")
        value_label.setWordWrap(True)

        card_layout.addWidget(name_label)
        card_layout.addWidget(value_label)

        return card, value_label

    @staticmethod
    def _format_currency(cents):
        return f"R$ {cents / 100:,.2f}".replace(",", "X").replace(
            ".", ","
        ).replace("X", ".")

    @staticmethod
    def _format_quantity(quantity_milli):
        quantity = quantity_milli / 1000
        if quantity.is_integer():
            return f"{int(quantity):,}".replace(",", ".")
        return f"{quantity:,.3f}".replace(",", "X").replace(
            ".", ","
        ).replace("X", ".")

    def refresh_data(self):
        with get_connection() as connection:
            sales = connection.execute(
                """
                SELECT COALESCE(SUM(total_cents), 0) AS total
                FROM sales
                WHERE reversed_at IS NULL
                  AND sale_date >= date('now', 'localtime', 'start of month')
                  AND sale_date < date('now', 'localtime', 'start of month', '+1 month')
                """
            ).fetchone()

            stock = connection.execute(
                """
                SELECT COALESCE(SUM(quantity_milli), 0) AS quantity
                FROM stock_movements
                WHERE product_id IS NOT NULL
                """
            ).fetchone()

            productions = connection.execute(
                "SELECT COUNT(*) AS total FROM productions"
            ).fetchone()

        self.value_labels["sales_month"].setText(
            self._format_currency(sales["total"])
        )
        self.value_labels["products_stock"].setText(
            self._format_quantity(stock["quantity"])
        )
        self.value_labels["productions"].setText(
            f"{productions['total']:,}".replace(",", ".")
        )
        self.value_labels["financial"].setText("Em desenvolvimento")
