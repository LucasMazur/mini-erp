from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.services.sales_service import list_sales
from app.ui.pages.sale_details_dialog import SaleDetailsDialog
from app.ui.pages.sale_form import SaleForm


class SalesPage(QWidget):
    def __init__(self):
        super().__init__()
        self._create_interface()
        self.load_sales()

    def _create_interface(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(35, 30, 35, 30)
        layout.setSpacing(18)

        title = QLabel("Vendas")
        title.setObjectName("page_title")
        layout.addWidget(title)

        subtitle = QLabel(
            "Registre vendas, acompanhe os recebimentos e controle as saídas do estoque."
        )
        subtitle.setObjectName("page_subtitle")
        layout.addWidget(subtitle)

        toolbar = QHBoxLayout()
        toolbar.addStretch()
        new_button = QPushButton("+ Nova venda")
        new_button.setObjectName("primary_button")
        new_button.clicked.connect(self.open_sale_form)
        toolbar.addWidget(new_button)
        layout.addLayout(toolbar)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Data", "Venda", "Itens", "Subtotal", "Total", "Status"
        ])
        self.table.cellDoubleClicked.connect(self.open_sale_details)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, header.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, header.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, header.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, header.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, header.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, header.ResizeMode.Stretch)
        layout.addWidget(self.table)

    @staticmethod
    def _currency(cents):
        return f"R$ {cents / 100:,.2f}".replace(",", "X").replace(
            ".", ","
        ).replace("X", ".")

    def load_sales(self):
        sales = list_sales()
        self.table.setRowCount(len(sales))
        for row, sale in enumerate(sales):
            date = sale["sale_date"]
            formatted_date = f"{date[8:10]}/{date[5:7]}/{date[:4]}"
            values = [
                formatted_date,
                f"#{sale['id']}",
                str(sale["item_count"]),
                self._currency(sale["subtotal_cents"]),
                self._currency(sale["total_cents"]),
                "Estornada" if sale["reversed_at"] else "Concluída",
            ]
            for column, value in enumerate(values):
                cell = QTableWidgetItem(value)
                if column == 5:
                    cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    cell.setForeground(
                        QColor("#DC2626")
                        if sale["reversed_at"]
                        else QColor("#187443")
                    )
                self.table.setItem(row, column, cell)

    def open_sale_form(self):
        dialog = SaleForm(self)
        if dialog.exec():
            self.load_sales()

    def open_sale_details(self, row, column):
        sales = list_sales()
        if row >= len(sales):
            return
        dialog = SaleDetailsDialog(sales[row]["id"], self)
        dialog.exec()
        self.load_sales()
