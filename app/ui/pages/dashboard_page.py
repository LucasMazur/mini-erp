from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from app.database.connection import get_connection


class BarChart(QWidget):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.title = title
        self.values = []
        self.setMinimumHeight(250)

    def set_values(self, values):
        self.values = values
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QColor("#263445"))
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(0, 20, self.title)

        if not self.values:
            painter.setPen(QColor("#8290A0"))
            painter.drawText(0, 60, "Sem dados para o período.")
            return

        max_value = max(value for _, value in self.values) or 1
        top = 42
        row_height = min(34, (self.height() - top - 8) / len(self.values))
        label_width = 125
        value_width = 85
        bar_width = max(30, self.width() - label_width - value_width - 18)

        for index, (label, value) in enumerate(self.values):
            y = top + index * row_height
            painter.setPen(QColor("#526174"))
            painter.drawText(
                QRectF(0, y, label_width - 8, row_height),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                str(label)[:18],
            )
            background = QRectF(label_width, y + 7, bar_width, 13)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#E8EDF2"))
            painter.drawRoundedRect(background, 6, 6)
            filled = QRectF(
                label_width, y + 7, bar_width * value / max_value, 13
            )
            painter.setBrush(QColor("#526B86"))
            painter.drawRoundedRect(filled, 6, 6)
            painter.setPen(QColor("#263445"))
            painter.drawText(
                QRectF(label_width + bar_width + 8, y, value_width, row_height),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                self._format_value(value),
            )

    @staticmethod
    def _format_value(value):
        return f"{value:,.0f}".replace(",", ".")


class MonthlyChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.values = []
        self.setMinimumHeight(250)

    def set_values(self, values):
        self.values = values
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QColor("#263445"))
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(0, 20, "Faturamento mensal — últimos 6 meses")

        if not self.values:
            painter.setPen(QColor("#8290A0"))
            painter.drawText(0, 60, "Sem dados para o período.")
            return

        left, right, top, bottom = 42, 12, 45, 35
        chart_width = max(1, self.width() - left - right)
        chart_height = max(1, self.height() - top - bottom)
        maximum = max(value for _, value in self.values) or 1

        painter.setPen(QPen(QColor("#DCE2E8"), 1))
        for step in range(4):
            y = top + chart_height * step / 3
            painter.drawLine(int(left), int(y), int(left + chart_width), int(y))

        count = len(self.values)
        points = []
        for index, (month, value) in enumerate(self.values):
            x = left + chart_width * (index + 0.5) / count
            y = top + chart_height * (1 - value / maximum)
            points.append((x, y))
            painter.setPen(QColor("#526B86"))
            painter.drawText(
                QRectF(x - 30, top + chart_height + 8, 60, 22),
                Qt.AlignmentFlag.AlignHCenter,
                month,
            )

        painter.setPen(QPen(QColor("#526B86"), 3))
        for first, second in zip(points, points[1:]):
            painter.drawLine(int(first[0]), int(first[1]), int(second[0]), int(second[1]))

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#526B86"))
        for x, y in points:
            painter.drawEllipse(int(x - 4), int(y - 4), 8, 8)


class DashboardPage(QWidget):
    def __init__(self):
        super().__init__()
        self.value_labels = {}
        self._create_interface()
        self.refresh_data()

    def _create_interface(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(35, 30, 35, 30)
        layout.setSpacing(16)

        title = QLabel("Visão geral")
        title.setObjectName("page_title")
        layout.addWidget(title)

        subtitle = QLabel(
            "Indicadores de vendas, financeiro, estoque e desempenho do negócio."
        )
        subtitle.setObjectName("page_subtitle")
        layout.addWidget(subtitle)

        cards_layout = QGridLayout()
        cards_layout.setSpacing(14)
        indicators = [
            ("Vendas do mês", "sales_month", "R$ 0,00"),
            ("Produtos com estoque", "products_stock", "0"),
            ("Produções no mês", "productions", "0"),
            ("Resultado financeiro", "financial", "R$ 0,00"),
        ]
        for index, (name, key, value) in enumerate(indicators):
            card, value_label = self._create_card(name, value)
            self.value_labels[key] = value_label
            cards_layout.addWidget(card, index // 2, index % 2)
        layout.addLayout(cards_layout)

        charts_layout = QGridLayout()
        charts_layout.setSpacing(14)
        self.monthly_chart = MonthlyChart()
        self.top_products_chart = BarChart("Produtos mais vendidos — mês atual")
        self.low_stock_chart = BarChart("Materiais que precisam de atenção")
        charts_layout.addWidget(self.monthly_chart, 0, 0)
        charts_layout.addWidget(self.top_products_chart, 0, 1)
        charts_layout.addWidget(self.low_stock_chart, 1, 0, 1, 2)
        layout.addLayout(charts_layout, 1)

    def _create_card(self, name, value):
        card = QFrame()
        card.setObjectName("dashboard_card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 16, 20, 16)
        card_layout.setSpacing(8)
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

            product_stock = connection.execute(
                """
                SELECT COUNT(*) AS total
                FROM products p
                WHERE p.active = 1 AND COALESCE((
                    SELECT SUM(sm.quantity_milli)
                    FROM stock_movements sm
                    WHERE sm.product_id = p.id
                ), 0) > 0
                """
            ).fetchone()

            productions = connection.execute(
                """
                SELECT COUNT(*) AS total
                FROM productions
                WHERE occurred_at >= date('now', 'localtime', 'start of month')
                  AND occurred_at < date('now', 'localtime', 'start of month', '+1 month')
                """
            ).fetchone()

            financial = connection.execute(
                """
                SELECT
                    COALESCE(SUM(CASE WHEN direction = 'income'
                        THEN amount_cents ELSE 0 END), 0) -
                    COALESCE(SUM(CASE WHEN direction = 'expense'
                        THEN amount_cents ELSE 0 END), 0) AS balance
                FROM financial_transactions
                WHERE transaction_date >= date('now', 'localtime', 'start of month')
                  AND transaction_date < date('now', 'localtime', 'start of month', '+1 month')
                """
            ).fetchone()

            monthly_rows = connection.execute(
                """
                SELECT strftime('%Y-%m', transaction_date) AS month,
                       COALESCE(SUM(CASE WHEN direction = 'income'
                           THEN amount_cents ELSE 0 END), 0) AS income,
                       COALESCE(SUM(CASE WHEN direction = 'expense'
                           THEN amount_cents ELSE 0 END), 0) AS expense
                FROM financial_transactions
                WHERE transaction_date >= date('now', 'localtime', 'start of month', '-5 months')
                  AND transaction_date < date('now', 'localtime', 'start of month', '+1 month')
                GROUP BY strftime('%Y-%m', transaction_date)
                ORDER BY month
                """
            ).fetchall()

            top_products = connection.execute(
                """
                SELECT si.product_name_snapshot AS name,
                       SUM(si.quantity_milli) AS quantity
                FROM sale_items si
                JOIN sales s ON s.id = si.sale_id
                WHERE s.reversed_at IS NULL
                  AND s.sale_date >= date('now', 'localtime', 'start of month')
                  AND s.sale_date < date('now', 'localtime', 'start of month', '+1 month')
                GROUP BY si.product_name_snapshot
                ORDER BY quantity DESC
                LIMIT 5
                """
            ).fetchall()

            low_stock = connection.execute(
                """
                SELECT m.name,
                       COALESCE(SUM(sm.quantity_milli), 0) AS current_stock,
                       m.minimum_stock_quantity_milli AS minimum_stock
                FROM materials m
                LEFT JOIN stock_movements sm ON sm.material_id = m.id
                WHERE m.active = 1 AND m.minimum_stock_quantity_milli > 0
                GROUP BY m.id
                HAVING current_stock <= minimum_stock
                ORDER BY current_stock - minimum_stock
                LIMIT 8
                """
            ).fetchall()

        self.value_labels["sales_month"].setText(
            self._format_currency(sales["total"])
        )
        self.value_labels["products_stock"].setText(str(product_stock["total"]))
        self.value_labels["productions"].setText(str(productions["total"]))
        self.value_labels["financial"].setText(
            self._format_currency(financial["balance"])
        )
        self.value_labels["financial"].setStyleSheet(
            "color: #187443;" if financial["balance"] >= 0
            else "color: #B42318;"
        )

        month_names = {
            "01": "Jan", "02": "Fev", "03": "Mar", "04": "Abr",
            "05": "Mai", "06": "Jun", "07": "Jul", "08": "Ago",
            "09": "Set", "10": "Out", "11": "Nov", "12": "Dez",
        }
        monthly_data = {row["month"]: row for row in monthly_rows}
        month_keys = connection_month_keys()
        chart_values = []
        for key in month_keys:
            row = monthly_data.get(key, {"income": 0, "expense": 0})
            month_label = f"{month_names[key[5:7]]}/{key[2:4]}"
            chart_values.append((
                month_label,
                max(0, row["income"] - row["expense"]) / 100,
            ))
        self.monthly_chart.set_values(chart_values)
        self.top_products_chart.set_values([
            (row["name"], row["quantity"] / 1000) for row in top_products
        ])
        self.low_stock_chart.set_values([
            (row["name"], max(0, row["minimum_stock"] - row["current_stock"]) / 1000)
            for row in low_stock
        ])


def connection_month_keys():
    from datetime import date

    today = date.today().replace(day=1)
    months = []
    for offset in range(5, -1, -1):
        year = today.year
        month = today.month - offset
        while month <= 0:
            month += 12
            year -= 1
        months.append(f"{year:04d}-{month:02d}")
    return months
