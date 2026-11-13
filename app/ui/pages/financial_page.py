from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
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


class FinancialPage(QWidget):
    def __init__(self):
        super().__init__()
        self._create_interface()
        self.refresh_data()

    def _create_card(self, title, object_name):
        card = QFrame()
        card.setObjectName("dashboard_card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 17, 20, 17)
        card_layout.setSpacing(8)

        caption = QLabel(title)
        caption.setObjectName("card_name")
        card_layout.addWidget(caption)

        value = QLabel("R$ 0,00")
        value.setObjectName(object_name)
        card_layout.addWidget(value)
        return card, value

    def _create_interface(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(35, 30, 35, 30)
        layout.setSpacing(16)

        title = QLabel("Financeiro")
        title.setObjectName("page_title")
        layout.addWidget(title)

        subtitle = QLabel(
            "Acompanhe receitas, despesas e o resultado financeiro do negócio."
        )
        subtitle.setObjectName("page_subtitle")
        layout.addWidget(subtitle)

        cards = QHBoxLayout()
        cards.setSpacing(14)
        income_card, self.income_value = self._create_card(
            "Receitas", "card_value"
        )
        expense_card, self.expense_value = self._create_card(
            "Despesas", "card_value"
        )
        balance_card, self.balance_value = self._create_card(
            "Saldo do período", "card_value"
        )
        cards.addWidget(income_card)
        cards.addWidget(expense_card)
        cards.addWidget(balance_card)
        layout.addLayout(cards)

        filters = QHBoxLayout()
        filters.setSpacing(10)

        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDisplayFormat("dd/MM/yyyy")
        self.start_date.setDate(QDate.currentDate().addDays(1 - QDate.currentDate().day()))
        filters.addWidget(QLabel("De"))
        filters.addWidget(self.start_date)

        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDisplayFormat("dd/MM/yyyy")
        self.end_date.setDate(QDate.currentDate())
        filters.addWidget(QLabel("Até"))
        filters.addWidget(self.end_date)

        self.direction_filter = QComboBox()
        self.direction_filter.addItem("Todas as movimentações", None)
        self.direction_filter.addItem("Receitas", "income")
        self.direction_filter.addItem("Despesas", "expense")
        filters.addWidget(self.direction_filter)

        apply_button = QPushButton("Aplicar filtros")
        apply_button.clicked.connect(self.refresh_data)
        filters.addWidget(apply_button)

        clear_button = QPushButton("Este mês")
        clear_button.clicked.connect(self._current_month)
        filters.addWidget(clear_button)
        filters.addStretch()
        layout.addLayout(filters)

        self.transactions_table = QTableWidget()
        self.transactions_table.setColumnCount(6)
        self.transactions_table.setHorizontalHeaderLabels([
            "Data", "Descrição", "Categoria", "Tipo", "Forma de pagamento", "Valor"
        ])
        self.transactions_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self.transactions_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.transactions_table.setSelectionMode(
            QTableWidget.SelectionMode.SingleSelection
        )
        self.transactions_table.verticalHeader().setVisible(False)
        header = self.transactions_table.horizontalHeader()
        header.setSectionResizeMode(0, header.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, header.ResizeMode.Stretch)
        header.setSectionResizeMode(2, header.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, header.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, header.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, header.ResizeMode.ResizeToContents)
        layout.addWidget(self.transactions_table, 1)

    @staticmethod
    def _currency(cents):
        return f"R$ {cents / 100:,.2f}".replace(",", "X").replace(
            ".", ","
        ).replace("X", ".")

    @staticmethod
    def _date_iso(date):
        return date.toString("yyyy-MM-dd")

    def _current_month(self):
        today = QDate.currentDate()
        self.start_date.setDate(today.addDays(1 - today.day()))
        self.end_date.setDate(today)
        self.direction_filter.setCurrentIndex(0)
        self.refresh_data()

    def refresh_data(self):
        start_date = self._date_iso(self.start_date.date())
        end_date = self._date_iso(self.end_date.date())
        if start_date > end_date:
            self.transactions_table.setRowCount(0)
            self.income_value.setText("R$ 0,00")
            self.expense_value.setText("R$ 0,00")
            self.balance_value.setText("Período inválido")
            return

        summary = get_financial_summary(start_date, end_date)
        transactions = list_transactions(
            start_date,
            end_date,
            self.direction_filter.currentData(),
        )

        self.income_value.setText(self._currency(summary["income_cents"]))
        self.expense_value.setText(self._currency(summary["expense_cents"]))
        self.balance_value.setText(self._currency(summary["balance_cents"]))
        self.balance_value.setStyleSheet(
            "color: #187443;" if summary["balance_cents"] >= 0
            else "color: #B42318;"
        )

        self.transactions_table.setRowCount(len(transactions))
        for row, transaction in enumerate(transactions):
            date = transaction["transaction_date"]
            formatted_date = f"{date[8:10]}/{date[5:7]}/{date[:4]}"
            is_income = transaction["direction"] == "income"
            values = [
                formatted_date,
                transaction["description"],
                transaction["category"] or "—",
                "Receita" if is_income else "Despesa",
                transaction["payment_method"] or "—",
                self._currency(transaction["amount_cents"]),
            ]
            for column, value in enumerate(values):
                cell = QTableWidgetItem(str(value))
                if column in (3, 5):
                    cell.setForeground(
                        QColor("#187443") if is_income else QColor("#B42318")
                    )
                if column == 5:
                    cell.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    )
                self.transactions_table.setItem(row, column, cell)
