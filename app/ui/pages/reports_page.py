from collections import defaultdict

from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDateEdit,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.services.financial_service import (
    get_financial_summary,
    list_transactions,
)


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

        value = QLabel("R$ 0,00")
        value.setObjectName("card_value")
        card_layout.addWidget(value)
        return card, value

    def _create_interface(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(35, 30, 35, 30)
        layout.setSpacing(15)

        title = QLabel("Relatórios")
        title.setObjectName("page_title")
        layout.addWidget(title)

        subtitle = QLabel(
            "Analise o resultado financeiro e a composição das movimentações."
        )
        subtitle.setObjectName("page_subtitle")
        layout.addWidget(subtitle)

        filters = QHBoxLayout()
        filters.setSpacing(10)
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDisplayFormat("dd/MM/yyyy")
        today = QDate.currentDate()
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

        cards = QHBoxLayout()
        cards.setSpacing(14)
        income_card, self.income_value = self._create_card("Total de receitas")
        expense_card, self.expense_value = self._create_card("Total de despesas")
        balance_card, self.balance_value = self._create_card("Resultado do período")
        cards.addWidget(income_card)
        cards.addWidget(expense_card)
        cards.addWidget(balance_card)
        layout.addLayout(cards)

        section_title = QLabel("Movimentações por categoria")
        section_title.setObjectName("section_title")
        layout.addWidget(section_title)

        self.category_table = QTableWidget()
        self.category_table.setColumnCount(4)
        self.category_table.setHorizontalHeaderLabels([
            "Categoria", "Tipo", "Quantidade de lançamentos", "Valor total"
        ])
        self.category_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self.category_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.category_table.verticalHeader().setVisible(False)
        header = self.category_table.horizontalHeader()
        header.setSectionResizeMode(0, header.ResizeMode.Stretch)
        header.setSectionResizeMode(1, header.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, header.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, header.ResizeMode.ResizeToContents)
        layout.addWidget(self.category_table, 1)

        self.status_label = QLabel("")
        self.status_label.setObjectName("page_subtitle")
        layout.addWidget(self.status_label)

    def _current_month(self):
        today = QDate.currentDate()
        self.start_date.setDate(today.addDays(1 - today.day()))
        self.end_date.setDate(today)
        self.refresh_data()

    def refresh_data(self):
        start_date = self._iso_date(self.start_date.date())
        end_date = self._iso_date(self.end_date.date())
        if start_date > end_date:
            self.income_value.setText("—")
            self.expense_value.setText("—")
            self.balance_value.setText("Período inválido")
            self.category_table.setRowCount(0)
            self.status_label.setText("A data inicial deve ser anterior à data final.")
            return

        summary = get_financial_summary(start_date, end_date)
        transactions = list_transactions(start_date, end_date)

        self.income_value.setText(self._currency(summary["income_cents"]))
        self.expense_value.setText(self._currency(summary["expense_cents"]))
        self.balance_value.setText(self._currency(summary["balance_cents"]))
        self.balance_value.setStyleSheet(
            "color: #187443;" if summary["balance_cents"] >= 0
            else "color: #B42318;"
        )

        grouped = defaultdict(lambda: {"income": 0, "expense": 0, "count": 0})
        for transaction in transactions:
            category = transaction["category"] or "Sem categoria"
            direction = transaction["direction"]
            grouped[(category, direction)]["income" if direction == "income" else "expense"] += transaction["amount_cents"]
            grouped[(category, direction)]["count"] += 1

        rows = sorted(
            grouped.items(),
            key=lambda item: (item[0][0].casefold(), item[0][1]),
        )
        self.category_table.setRowCount(len(rows))
        for row, ((category, direction), values) in enumerate(rows):
            is_income = direction == "income"
            total = values["income"] + values["expense"]
            cells = [
                category,
                "Receita" if is_income else "Despesa",
                str(values["count"]),
                self._currency(total),
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

        self.status_label.setText(
            f"{len(transactions)} lançamento(s) no período selecionado."
        )
