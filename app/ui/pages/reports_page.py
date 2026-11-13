from collections import defaultdict

from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDateEdit,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.services.financial_service import (
    get_financial_summary,
    list_transactions,
)
from app.services.sales_service import get_sales_report


class ReportsPage(QWidget):
    def __init__(self):
        super().__init__()
        self._create_interface()
        self.refresh_data()

    @staticmethod
    def _currency(cents):
        return f"R$ {cents / 100:,.2f}".replace(",", "X").replace(
            ".", ","
        ).replace("X", ".")

    @staticmethod
    def _iso_date(date):
        return date.toString("yyyy-MM-dd")

    def _create_card(self, title):
        card = QFrame()
        card.setObjectName("dashboard_card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 15, 18, 15)
        card_layout.setSpacing(7)
        caption = QLabel(title)
        caption.setObjectName("card_name")
        card_layout.addWidget(caption)
        value = QLabel("0")
        value.setObjectName("card_value")
        card_layout.addWidget(value)
        return card, value

    def _create_table(self, headers, stretch_column=0):
        table = QTableWidget()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.verticalHeader().setVisible(False)
        header = table.horizontalHeader()
        for column in range(len(headers)):
            mode = (
                header.ResizeMode.Stretch
                if column == stretch_column
                else header.ResizeMode.ResizeToContents
            )
            header.setSectionResizeMode(column, mode)
        return table

    def _create_interface(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(35, 30, 35, 30)
        layout.setSpacing(15)

        title = QLabel("Relatórios")
        title.setObjectName("page_title")
        layout.addWidget(title)
        subtitle = QLabel(
            "Analise o desempenho financeiro e comercial do seu negócio."
        )
        subtitle.setObjectName("page_subtitle")
        layout.addWidget(subtitle)

        filters = QHBoxLayout()
        filters.setSpacing(10)
        today = QDate.currentDate()
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDisplayFormat("dd/MM/yyyy")
        self.start_date.setDate(today.addDays(1 - today.day()))
        filters.addWidget(QLabel("De"))
        filters.addWidget(self.start_date)

        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDisplayFormat("dd/MM/yyyy")
        self.end_date.setDate(today)
        filters.addWidget(QLabel("Até"))
        filters.addWidget(self.end_date)

        apply_button = QPushButton("Gerar relatório")
        apply_button.setObjectName("primary_button")
        apply_button.clicked.connect(self.refresh_data)
        filters.addWidget(apply_button)
        month_button = QPushButton("Este mês")
        month_button.clicked.connect(self._current_month)
        filters.addWidget(month_button)
        filters.addStretch()
        layout.addLayout(filters)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)
        self._create_financial_tab()
        self._create_sales_tab()

    def _create_financial_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 12, 8, 8)
        layout.setSpacing(14)

        cards = QHBoxLayout()
        income_card, self.income_value = self._create_card("Total de receitas")
        expense_card, self.expense_value = self._create_card("Total de despesas")
        balance_card, self.balance_value = self._create_card("Resultado do período")
        cards.addWidget(income_card)
        cards.addWidget(expense_card)
        cards.addWidget(balance_card)
        layout.addLayout(cards)

        section = QLabel("Movimentações por categoria")
        section.setObjectName("section_title")
        layout.addWidget(section)
        self.category_table = self._create_table(
            ["Categoria", "Tipo", "Quantidade de lançamentos", "Valor total"]
        )
        layout.addWidget(self.category_table, 1)
        self.financial_status = QLabel("")
        self.financial_status.setObjectName("page_subtitle")
        layout.addWidget(self.financial_status)
        self.tabs.addTab(tab, "Financeiro")

    def _create_sales_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 12, 8, 8)
        layout.setSpacing(14)

        cards = QHBoxLayout()
        revenue_card, self.sales_revenue_value = self._create_card(
            "Faturamento líquido"
        )
        count_card, self.sales_count_value = self._create_card("Vendas realizadas")
        quantity_card, self.units_sold_value = self._create_card("Unidades vendidas")
        cards.addWidget(revenue_card)
        cards.addWidget(count_card)
        cards.addWidget(quantity_card)
        layout.addLayout(cards)

        product_title = QLabel("Produtos vendidos")
        product_title.setObjectName("section_title")
        layout.addWidget(product_title)
        self.products_table = self._create_table(
            ["Produto", "Quantidade vendida", "Valor bruto", "Vendas"],
            stretch_column=0,
        )
        layout.addWidget(self.products_table, 1)

        payment_title = QLabel("Vendas por forma de pagamento")
        payment_title.setObjectName("section_title")
        layout.addWidget(payment_title)
        self.payment_table = self._create_table(
            ["Forma de pagamento", "Quantidade de vendas", "Faturamento"],
            stretch_column=0,
        )
        layout.addWidget(self.payment_table, 1)
        self.sales_status = QLabel("")
        self.sales_status.setObjectName("page_subtitle")
        layout.addWidget(self.sales_status)
        self.tabs.addTab(tab, "Vendas")

    def _current_month(self):
        today = QDate.currentDate()
        self.start_date.setDate(today.addDays(1 - today.day()))
        self.end_date.setDate(today)
        self.refresh_data()

    def refresh_data(self):
        start_date = self._iso_date(self.start_date.date())
        end_date = self._iso_date(self.end_date.date())
        if start_date > end_date:
            self._show_invalid_period()
            return

        self._refresh_financial(start_date, end_date)
        self._refresh_sales(start_date, end_date)

    def _show_invalid_period(self):
        for label in (
            self.income_value,
            self.expense_value,
            self.sales_revenue_value,
        ):
            label.setText("—")
        self.balance_value.setText("Período inválido")
        self.sales_count_value.setText("—")
        self.units_sold_value.setText("—")
        self.category_table.setRowCount(0)
        self.products_table.setRowCount(0)
        self.payment_table.setRowCount(0)
        self.financial_status.setText(
            "A data inicial deve ser anterior à data final."
        )
        self.sales_status.setText(
            "A data inicial deve ser anterior à data final."
        )

    def _refresh_financial(self, start_date, end_date):
        summary = get_financial_summary(start_date, end_date)
        transactions = list_transactions(start_date, end_date)
        self.income_value.setText(self._currency(summary["income_cents"]))
        self.expense_value.setText(self._currency(summary["expense_cents"]))
        self.balance_value.setText(self._currency(summary["balance_cents"]))
        self.balance_value.setStyleSheet(
            "color: #187443;" if summary["balance_cents"] >= 0
            else "color: #B42318;"
        )

        grouped = defaultdict(lambda: {"amount": 0, "count": 0})
        for transaction in transactions:
            category = transaction["category"] or "Sem categoria"
            direction = transaction["direction"]
            group = grouped[(category, direction)]
            group["amount"] += transaction["amount_cents"]
            group["count"] += 1

        rows = sorted(
            grouped.items(),
            key=lambda item: (item[0][0].casefold(), item[0][1]),
        )
        self.category_table.setRowCount(len(rows))
        for row, ((category, direction), values) in enumerate(rows):
            is_income = direction == "income"
            cells = [
                category,
                "Receita" if is_income else "Despesa",
                str(values["count"]),
                self._currency(values["amount"]),
            ]
            for column, value in enumerate(cells):
                item = QTableWidgetItem(value)
                if column in (1, 3):
                    item.setForeground(
                        QColor("#187443") if is_income else QColor("#B42318")
                    )
                if column in (2, 3):
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    )
                self.category_table.setItem(row, column, item)

        self.financial_status.setText(
            f"{len(transactions)} lançamento(s) no período selecionado."
        )

    def _refresh_sales(self, start_date, end_date):
        report = get_sales_report(start_date, end_date)
        self.sales_revenue_value.setText(
            self._currency(report["revenue_cents"])
        )
        self.sales_count_value.setText(str(report["sales_count"]))
        self.units_sold_value.setText(
            f"{report['quantity_milli'] / 1000:,.3f}".replace(",", "X")
            .replace(".", ",").replace("X", ".")
        )

        products = report["by_product"]
        self.products_table.setRowCount(len(products))
        for row, product in enumerate(products):
            quantity = product["quantity_milli"] / 1000
            cells = [
                product["product_name"],
                f"{quantity:,.3f}".replace(",", "X").replace(
                    ".", ","
                ).replace("X", "."),
                self._currency(product["gross_cents"]),
                str(product["sales_count"]),
            ]
            for column, value in enumerate(cells):
                item = QTableWidgetItem(value)
                if column in (1, 2, 3):
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    )
                self.products_table.setItem(row, column, item)

        payments = report["by_payment"]
        self.payment_table.setRowCount(len(payments))
        for row, payment in enumerate(payments):
            cells = [
                payment["payment_method"],
                str(payment["sales_count"]),
                self._currency(payment["revenue_cents"]),
            ]
            for column, value in enumerate(cells):
                item = QTableWidgetItem(value)
                if column == 2:
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    )
                self.payment_table.setItem(row, column, item)

        self.sales_status.setText(
            f"{len(products)} produto(s) com vendas no período selecionado. "
            "Vendas estornadas não entram neste relatório."
        )
