from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from app.database.connection import get_connection
from app.services.purchase_service import (
    get_purchase,
    reverse_purchase,
)

from datetime import datetime, timezone

class PurchaseDetailsDialog(QDialog):
    def __init__(self, purchase_id, parent=None):
        super().__init__(parent)

        self.purchase_id = purchase_id
        self.purchase = get_purchase(purchase_id)

        self.setWindowTitle(f"Compra #{purchase_id}")
        self.resize(950, 650)
        self.setMinimumSize(750, 500)

        self._create_interface()

    def _format_currency(self, cents):
        value = cents / 100
        return (
            f"R$ {value:,.2f}"
            .replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )

    def _is_reversed(self):
        with get_connection() as connection:
            result = connection.execute(
                """
                SELECT COUNT(*) AS total
                FROM stock_movements original
                WHERE original.reference_type = 'purchase'
                  AND original.reference_id = ?
                  AND original.movement_type = 'purchase'
                  AND NOT EXISTS (
                      SELECT 1
                      FROM stock_movements reversal
                      WHERE reversal.reversal_of_id = original.id
                  )
                """,
                (self.purchase_id,),
            ).fetchone()

        return result["total"] == 0
    
    def _create_interface(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 25, 30, 25)
        layout.setSpacing(15)

        title = QLabel(f"Compra #{self.purchase['id']}")
        title.setObjectName("page_title")
        layout.addWidget(title)

        date = self.purchase["purchase_date"]
        formatted_date = (
            f"{date[8:10]}/{date[5:7]}/{date[:4]}"
        )

        supplier = self.purchase["supplier_name"] or "Sem fornecedor"
        invoice = self.purchase["invoice_number"] or "Não informada"

        info = QLabel(
            f"Data: {formatted_date}    |    "
            f"Fornecedor: {supplier}    |    "
            f"Nota fiscal: {invoice}"
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        if self.purchase["reversed_at"]:
            reversed_at = datetime.strptime(
                self.purchase["reversed_at"],
                "%Y-%m-%d %H:%M:%S",
            ).replace(tzinfo=timezone.utc)

            reversed_at = reversed_at.astimezone()

            formatted_reversal = reversed_at.strftime("%d/%m/%Y às %H:%M")

            reversal_info = QLabel(
                f"Estornada em: {formatted_reversal}"
            )
            reversal_info.setObjectName("status_inactive")
            layout.addWidget(reversal_info)

        self.is_reversed = self._is_reversed()

        status_label = QLabel(
            "Estornada" if self.is_reversed else "Concluída"
        )
        status_label.setStyleSheet(
            """
            QLabel {
                color: #DC2626;
                background-color: #FEE2E2;
                border: 1px solid #FECACA;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: 600;
            }
            """
            if self.is_reversed
            else
            """
            QLabel {
                color: #16A34A;
                background-color: #DCFCE7;
                border: 1px solid #BBF7D0;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: 600;
            }
            """
        )
        status_label.setMaximumWidth(130)
        layout.addWidget(status_label)

        items_title = QLabel("Itens da compra")
        items_title.setObjectName("page_subtitle")
        layout.addWidget(items_title)

        self.items_table = QTableWidget()
        self.items_table.setColumnCount(5)
        self.items_table.setHorizontalHeaderLabels([
            "Material",
            "Quantidade",
            "Unidade",
            "Valor do item",
            "Custo final",
        ])

        items = self.purchase["items"]
        self.items_table.setRowCount(len(items))

        for row, item in enumerate(items):
            quantity = item["quantity_milli"] / 1000

            values = [
                item["material_name_snapshot"],
                f"{quantity:,.3f}".replace(",", "X")
                .replace(".", ",").replace("X", "."),
                item["unit_symbol_snapshot"],
                self._format_currency(item["line_total_cents"]),
                self._format_currency(item["landed_cost_cents"]),
            ]

            for column, value in enumerate(values):
                self.items_table.setItem(
                    row,
                    column,
                    QTableWidgetItem(str(value)),
                )

        self.items_table.verticalHeader().setVisible(False)
        self.items_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self.items_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.items_table)

        summary_layout = QVBoxLayout()
        summary_layout.setSpacing(8)

        subtotal = sum(
            item["line_total_cents"] for item in items
        )
        freight = self.purchase["freight_cents"]
        discount = self.purchase["discount_cents"]
        total = sum(
            item["landed_cost_cents"] for item in items
        )

        summary_layout.addWidget(
            QLabel(f"Subtotal: {self._format_currency(subtotal)}")
        )
        summary_layout.addWidget(
            QLabel(f"Frete: {self._format_currency(freight)}")
        )
        summary_layout.addWidget(
            QLabel(f"Desconto: {self._format_currency(discount)}")
        )

        total_label = QLabel(
            f"Total da compra: {self._format_currency(total)}"
        )
        total_label.setObjectName("page_title")
        total_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        summary_layout.addWidget(total_label)

        layout.addLayout(summary_layout)

        if self.purchase["notes"]:
            notes = QLabel(
                f"Observações: {self.purchase['notes']}"
            )
            notes.setWordWrap(True)
            layout.addWidget(notes)

        buttons_layout = QHBoxLayout()

        if not self.is_reversed:
            reverse_button = QPushButton("Estornar compra")
            reverse_button.setObjectName("danger_button")
            reverse_button.clicked.connect(self._reverse_purchase)
            buttons_layout.addWidget(reverse_button)
        else:
            reversed_label = QLabel("Compra estornada")
            reversed_label.setObjectName("status_inactive")
            buttons_layout.addWidget(reversed_label)

        buttons_layout.addStretch()

        close_button = QPushButton("Fechar")
        close_button.clicked.connect(self.accept)
        buttons_layout.addWidget(close_button)

        layout.addLayout(buttons_layout)
    
    def _reverse_purchase(self):
        confirmation = QMessageBox.question(
            self,
            "Confirmar estorno",
            (
                f"Deseja realmente estornar a compra "
                f"#{self.purchase_id}?\n\n"
                "As entradas de estoque dessa compra serão "
                "revertidas. Essa operação não poderá ser desfeita."
            ),
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if confirmation != QMessageBox.StandardButton.Yes:
            return

        try:
            reverse_purchase(self.purchase_id)

        except (ValueError, RuntimeError) as error:
            QMessageBox.warning(
                self,
                "Não foi possível estornar",
                str(error),
            )
            return

        QMessageBox.information(
            self,
            "Estorno realizado",
            "A compra foi estornada com sucesso.",
        )

        self.accept()