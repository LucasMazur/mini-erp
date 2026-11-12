from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.services.purchase_service import list_purchases
from app.ui.pages.purchase_details_dialog import PurchaseDetailsDialog
from app.ui.pages.purchase_form import PurchaseForm

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

class PurchasesPage(QWidget):
    def __init__(self):
        super().__init__()

        self._create_interface()
        self._load_purchases()

    def _create_interface(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)

        title = QLabel("Compras")
        title.setObjectName("page_title")
        layout.addWidget(title)

        subtitle = QLabel(
            "Registre compras de materiais e acompanhe suas entradas."
        )
        subtitle.setObjectName("page_subtitle")
        layout.addWidget(subtitle)

        actions_layout = QHBoxLayout()
        actions_layout.addStretch()

        new_purchase_button = QPushButton("＋ Nova compra")
        new_purchase_button.setObjectName("primary_button")
        new_purchase_button.clicked.connect(self._open_purchase_form)

        actions_layout.addWidget(new_purchase_button)
        layout.addLayout(actions_layout)

        self.purchases_table = QTableWidget()
        self.purchases_table.setColumnCount(6)
        self.purchases_table.setHorizontalHeaderLabels([
            "Data",
            "Fornecedor",
            "Quantidade de itens",
            "Subtotal",
            "Total",
            "Status",
        ])

        self.purchases_table.cellDoubleClicked.connect(
            self._open_purchase_details
        )

        self.purchases_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self.purchases_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.purchases_table.setSelectionMode(
            QTableWidget.SelectionMode.SingleSelection
        )
        self.purchases_table.verticalHeader().setVisible(False)
        header = self.purchases_table.horizontalHeader()

        header.setSectionResizeMode(0, header.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, header.ResizeMode.Stretch)
        header.setSectionResizeMode(2, header.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, header.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, header.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, header.ResizeMode.ResizeToContents)

        layout.addWidget(self.purchases_table)

    def _load_purchases(self):
        purchases = list_purchases()

        self.purchases_table.setRowCount(len(purchases))

        for row, purchase in enumerate(purchases):
            purchase_date = purchase["purchase_date"]
            formatted_date = (
                f"{purchase_date[8:10]}/"
                f"{purchase_date[5:7]}/"
                f"{purchase_date[:4]}"
            )

            subtotal = purchase["subtotal_cents"] / 100
            total = purchase["total_cost_cents"] / 100

            status = (
                "Estornada"
                if purchase["is_reversed"]
                else "Concluída"
            )

            values = [
                formatted_date,
                purchase["supplier_name"] or "Sem fornecedor",
                str(purchase["item_count"]),
                f"R$ {subtotal:,.2f}".replace(",", "X")
                .replace(".", ",").replace("X", "."),
                f"R$ {total:,.2f}".replace(",", "X")
                .replace(".", ",").replace("X", "."),
                status,
            ]

            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))

                if column == 5:
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignCenter
                    )

                    if purchase["is_reversed"]:
                        item.setForeground(QColor("#DC2626"))
                    else:
                        item.setForeground(QColor("#16A34A"))

                self.purchases_table.setItem(
                    row,
                    column,
                    item,
                )
    def _open_purchase_form(self):
        dialog = PurchaseForm(self)

        if dialog.exec():
            self._load_purchases()

    def _open_purchase_details(self, row, column):
        purchase = list_purchases()

        if row >= len(purchase):
            return

        purchase_id = purchase[row]["id"]

        dialog = PurchaseDetailsDialog(purchase_id, self)
        dialog.exec()

        self._load_purchases()