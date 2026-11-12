from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.services.production_service import list_productions
from app.ui.pages.production_form import ProductionForm


class ProductionsPage(QWidget):
    def __init__(self):
        super().__init__()
        self._create_interface()
        self.load_productions()

    def _create_interface(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(35, 30, 35, 30)
        layout.setSpacing(18)

        title = QLabel("Produção")
        title.setObjectName("page_title")
        layout.addWidget(title)

        subtitle = QLabel(
            "Registre lotes de fabricação e acompanhe o histórico de produção."
        )
        subtitle.setObjectName("page_subtitle")
        layout.addWidget(subtitle)

        toolbar = QHBoxLayout()
        toolbar.addStretch()
        self.new_button = QPushButton("+ Registrar produção")
        self.new_button.setObjectName("primary_button")
        self.new_button.clicked.connect(self.open_production_form)
        toolbar.addWidget(self.new_button)
        layout.addLayout(toolbar)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Data", "Produto", "Receita", "Versão", "Quantidade", "Custo total"
        ])
        self.table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self.table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.table.setSelectionMode(
            QTableWidget.SelectionMode.SingleSelection
        )
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, header.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, header.ResizeMode.Stretch)
        header.setSectionResizeMode(2, header.ResizeMode.Stretch)
        header.setSectionResizeMode(3, header.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, header.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, header.ResizeMode.ResizeToContents)
        layout.addWidget(self.table)

    @staticmethod
    def _format_currency(cents):
        value = cents / 100
        return f"R$ {value:,.2f}".replace(",", "X").replace(
            ".", ","
        ).replace("X", ".")

    def load_productions(self):
        productions = list_productions()
        self.table.setRowCount(len(productions))

        for row, production in enumerate(productions):
            occurred_at = production["occurred_at"] or ""
            if len(occurred_at) >= 10:
                date_text = (
                    f"{occurred_at[8:10]}/"
                    f"{occurred_at[5:7]}/"
                    f"{occurred_at[:4]}"
                )
            else:
                date_text = "-"

            quantity = production["quantity_milli"] // 1000
            values = [
                date_text,
                production["product_name_snapshot"],
                production["recipe_name_snapshot"],
                str(production["recipe_version_number"]),
                str(quantity),
                self._format_currency(production["total_cost_cents"]),
            ]

            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if column in (3, 4, 5):
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight
                        | Qt.AlignmentFlag.AlignVCenter
                    )
                self.table.setItem(row, column, item)

    def open_production_form(self):
        dialog = ProductionForm(self)
        if dialog.exec():
            self.load_productions()
