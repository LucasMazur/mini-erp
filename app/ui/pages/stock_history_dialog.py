
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from app.services.stock_service import (
    get_stock_valuation,
    list_stock_movements,
)

MOVEMENT_LABELS = {
    "purchase": "Compra",
    "production_consumption": "Consumo na produção",
    "production_output": "Produção",
    "sale": "Venda",
    "adjustment_in": "Ajuste de entrada",
    "adjustment_out": "Ajuste de saída",
    "reversal": "Estorno",
}


class StockHistoryDialog(QDialog):
    def __init__(self, item, item_type=self.item_type, parent=None):
        super().__init__(parent)

        self.item = item
        self.item_type = item_type

        self.setWindowTitle(
            f"Histórico de estoque - {item['name']}"
        )
        self.resize(1050, 650)
        self.setMinimumSize(800, 450)

        self._create_interface()
        self.load_movements()

    def _create_interface(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)

        title = QLabel("Histórico de movimentações")
        title.setObjectName("page_title")
        layout.addWidget(title)

        subtitle = QLabel(
            f"Material: {self.item['name']}"
        )
        subtitle.setObjectName("page_subtitle")
        layout.addWidget(subtitle)

        self._create_summary(layout)

        section_title = QLabel("Movimentações")
        section_title.setObjectName("page_subtitle")
        layout.addWidget(section_title)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Data",
            "Movimentação",
            "Quantidade",
            "Valor",
            "Referência",
            "Observações",
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

        for column in range(5):
            header.setSectionResizeMode(
                column,
                header.ResizeMode.ResizeToContents,
            )

        header.setSectionResizeMode(
            5,
            header.ResizeMode.Stretch,
        )

        layout.addWidget(self.table)

        footer = QHBoxLayout()
        footer.addStretch()

        close_button = QPushButton("Fechar")
        close_button.clicked.connect(self.accept)
        footer.addWidget(close_button)

        layout.addLayout(footer)

    def _create_summary(self, layout):
        valuation = get_stock_valuation(
            self.item_type,
            self.item["id"],
        )

        quantity = valuation["quantity_milli"]
        value = valuation["value_cents"]
        average_cost = valuation[
            "average_cost_cents_per_milli"
        ] * 1000

        summary_layout = QHBoxLayout()
        summary_layout.setSpacing(12)

        self._add_summary_card(
            summary_layout,
            "Saldo atual",
            (
                f"{self._format_quantity(quantity)} "
                f"{self.item['unit_symbol']}"
            ),
        )

        self._add_summary_card(
            summary_layout,
            "Valor em estoque",
            self._format_currency(value),
        )

        self._add_summary_card(
            summary_layout,
            "Custo médio por "
            f"{self.item['unit_symbol']}",
            self._format_currency(
                round(average_cost)
            ),
        )

        layout.addLayout(summary_layout)

    @staticmethod
    def _add_summary_card(layout, title, value):
        card = QFrame()
        card.setObjectName("card")

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 12, 16, 12)
        card_layout.setSpacing(6)

        title_label = QLabel(title)
        title_label.setObjectName("page_subtitle")

        value_label = QLabel(value)
        value_label.setObjectName("page_title")

        card_layout.addWidget(title_label)
        card_layout.addWidget(value_label)

        layout.addWidget(card)

    def load_movements(self):
        movements = list_stock_movements(
            self.item_type,
            self.item["id"],
        )

        self.table.setRowCount(len(movements))

        for row, movement in enumerate(movements):
            movement_type = movement["movement_type"]

            reference = ""
            if movement["reference_type"]:
                reference = (
                    f"{movement['reference_type']} "
                    f"#{movement['reference_id'] or '-'}"
                )

            values = [
                self._format_date(movement["occurred_at"]),
                MOVEMENT_LABELS.get(
                    movement_type,
                    movement_type,
                ),
                self._format_quantity(
                    movement["quantity_milli"]
                ),
                self._format_currency(
                    movement["value_cents"]
                ),
                reference,
                movement["notes"] or "-",
            ]

            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))

                if column in (2, 3):
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight
                        | Qt.AlignmentFlag.AlignVCenter
                    )

                self.table.setItem(row, column, item)

    @staticmethod
    def _format_quantity(quantity_milli):
        quantity = abs(quantity_milli) / 1000
        if quantity_milli > 0:
            signal = "+"
        elif quantity_milli < 0:
            signal = "-"
        else:
            signal = ""

        return f"{signal}{quantity:,.3f}".replace(
            ",", "X"
        ).replace(".", ",").replace("X", ".")

    @staticmethod
    def _format_currency(value_cents):
        value = abs(value_cents) / 100
        signal = "-" if value_cents < 0 else ""

        formatted = f"{value:,.2f}".replace(
            ",", "X"
        ).replace(".", ",").replace("X", ".")

        return f"{signal}R$ {formatted}"

    @staticmethod
    def _format_date(value):
        if not value:
            return "-"

        return value.replace("T", " ")
