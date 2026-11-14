from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.services.production_service import (
    list_productions,
    reverse_production,
)
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
        self.reverse_button = QPushButton("Estornar produção selecionada")
        self.reverse_button.setEnabled(False)
        self.reverse_button.clicked.connect(self.reverse_selected_production)
        toolbar.addWidget(self.reverse_button)
        layout.addLayout(toolbar)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Data", "Produto", "Receita", "Versão", "Quantidade", "Custo total", "Situação"
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
        header.setSectionResizeMode(6, header.ResizeMode.ResizeToContents)
        self.table.itemSelectionChanged.connect(self._update_actions)
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

            quantity = production["quantity_milli"] // 1_000_000
            values = [
                date_text,
                production["product_name_snapshot"],
                production["recipe_name_snapshot"],
                str(production["recipe_version_number"]),
                str(quantity),
                self._format_currency(production["total_cost_cents"]),
                "Estornada" if production.get("is_reversed") else "Concluída",
            ]

            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if column == 0:
                    item.setData(Qt.ItemDataRole.UserRole, production["id"])
                if column in (3, 4, 5):
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight
                        | Qt.AlignmentFlag.AlignVCenter
                    )
                self.table.setItem(row, column, item)

        self._update_actions()

    def _update_actions(self):
        row = self.table.currentRow()
        selected = row >= 0 and self.table.item(row, 0) is not None
        is_reversed = (
            selected
            and self.table.item(row, 6).text() == "Estornada"
        )
        self.reverse_button.setEnabled(selected and not is_reversed)

    def reverse_selected_production(self):
        row = self.table.currentRow()
        if row < 0:
            return

        item = self.table.item(row, 0)
        if item is None:
            return

        production_id = item.data(Qt.ItemDataRole.UserRole)
        product_name = self.table.item(row, 1).text()
        quantity = self.table.item(row, 4).text()

        confirmation = QMessageBox.question(
            self,
            "Estornar produção",
            (
                f"Deseja estornar a produção #{production_id} de "
                f"{quantity} unidade(s) de '{product_name}'?\\n\\n"
                "Os materiais consumidos voltarão ao estoque e os "
                "produtos acabados desta produção serão retirados do estoque. "
                "O histórico será preservado como estornado."
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirmation != QMessageBox.StandardButton.Yes:
            return

        try:
            reverse_production(production_id)
        except ValueError as error:
            QMessageBox.warning(
                self,
                "Não foi possível estornar",
                str(error),
            )
            return

        QMessageBox.information(
            self,
            "Produção estornada",
            f"A produção #{production_id} foi estornada e o estoque foi atualizado.",
        )
        self.load_productions()

    def open_production_form(self):
        dialog = ProductionForm(self)
        if dialog.exec():
            self.load_productions()
