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

from app.services.sales_service import get_sale, reverse_sale


class SaleDetailsDialog(QDialog):
    def __init__(self, sale_id, parent=None):
        super().__init__(parent)
        self.sale_id = sale_id
        self.setWindowTitle(f"Detalhes da venda #{sale_id}")
        self.resize(800, 560)
        self._create_interface()
        self.load_sale()

    def _create_interface(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(12)

        self.title = QLabel("Detalhes da venda")
        self.title.setObjectName("page_title")
        layout.addWidget(self.title)

        self.info = QLabel()
        self.info.setObjectName("page_subtitle")
        layout.addWidget(self.info)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            "Produto", "Quantidade", "Preço unitário", "Subtotal"
        ])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        self.total = QLabel()
        self.total.setObjectName("page_title")
        layout.addWidget(self.total)

        buttons = QHBoxLayout()
        buttons.addStretch()
        close = QPushButton("Fechar")
        close.clicked.connect(self.accept)
        buttons.addWidget(close)

        self.reverse_button = QPushButton("Estornar venda")
        self.reverse_button.clicked.connect(self._reverse)
        buttons.addWidget(self.reverse_button)
        layout.addLayout(buttons)

    @staticmethod
    def _currency(cents):
        return f"R$ {cents / 100:,.2f}".replace(",", "X").replace(
            ".", ","
        ).replace("X", ".")

    def load_sale(self):
        sale = get_sale(self.sale_id)
        if sale is None:
            QMessageBox.warning(self, "Venda não encontrada", "A venda não foi localizada.")
            self.accept()
            return

        self.info.setText(
            f"Data: {sale['sale_date']}  •  Pagamento: {sale['payment_method']}  "
            f"•  Status: {'Estornada' if sale['reversed_at'] else 'Concluída'}"
        )
        self.table.setRowCount(len(sale["items"]))
        for row, item in enumerate(sale["items"]):
            values = [
                item["product_name_snapshot"],
                str(item["quantity_milli"] // 1000),
                self._currency(item["unit_price_cents"]),
                self._currency(item["line_total_cents"]),
            ]
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(value))

        self.total.setText(
            f"Subtotal: {self._currency(sale['subtotal_cents'])}   "
            f"Desconto: {self._currency(sale['discount_cents'])}   "
            f"Total: {self._currency(sale['total_cents'])}"
        )
        self.reverse_button.setEnabled(sale["reversed_at"] is None)

    def _reverse(self):
        answer = QMessageBox.question(
            self,
            "Estornar venda",
            "Deseja estornar esta venda? Os produtos retornarão ao estoque.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            reverse_sale(self.sale_id)
        except (ValueError, RuntimeError) as error:
            QMessageBox.warning(self, "Não foi possível estornar", str(error))
            return

        QMessageBox.information(
            self, "Venda estornada",
            "A venda foi estornada e o estoque foi recomposto.",
        )
        self.load_sale()
