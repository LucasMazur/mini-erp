from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from app.services.recipe_service import (
    get_recipe,
    finalize_recipe_version,
    create_recipe_version,
    remove_recipe_item,
)
from app.services.recipe_cost_calculator import calculate_recipe_cost
from app.ui.pages.recipe_item_form import RecipeItemForm


class RecipeDetailsDialog(QDialog):
    def __init__(self, recipe_id, parent=None):
        super().__init__(parent)

        self.recipe_id = recipe_id
        self.recipe = get_recipe(recipe_id)

        self.setWindowTitle("Detalhes da receita")
        self.resize(1100, 720)
        self.setMinimumSize(900, 600)

        self._create_interface()
        self.load_recipe_details()

    def _create_interface(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)

        self.product_label = QLabel()
        self.product_label.setObjectName("page_title")
        layout.addWidget(self.product_label)

        self.recipe_label = QLabel()
        self.recipe_label.setObjectName("page_subtitle")
        layout.addWidget(self.recipe_label)

        version_layout = QHBoxLayout()
        self.version_label = QLabel("Versão")
        version_layout.addWidget(self.version_label)
        self.version_combo = QComboBox()
        self.version_combo.setMinimumWidth(190)
        self.version_combo.currentIndexChanged.connect(
            self.load_selected_version
        )
        version_layout.addWidget(self.version_combo)
        version_layout.addStretch()
        layout.addLayout(version_layout)

        actions = QHBoxLayout()
        actions.setSpacing(10)
        self.finalize_button = QPushButton("Finalizar versão")
        self.finalize_button.setObjectName("primary_button")
        self.finalize_button.clicked.connect(self.finalize_version)
        actions.addWidget(self.finalize_button)
        self.add_material_button = QPushButton("+ Adicionar material")
        self.add_material_button.setObjectName("primary_button")
        self.add_material_button.clicked.connect(self.open_add_material)
        actions.addWidget(self.add_material_button)
        self.remove_material_button = QPushButton("Remover material")
        self.remove_material_button.setEnabled(False)
        self.remove_material_button.clicked.connect(self.remove_selected_material)
        actions.addWidget(self.remove_material_button)
        self.new_version_button = QPushButton("Criar nova versão")
        self.new_version_button.setObjectName("primary_button")
        self.new_version_button.clicked.connect(self.create_new_version)
        actions.addWidget(self.new_version_button)
        actions.addStretch()
        layout.addLayout(actions)

        for button in (
            self.finalize_button,
            self.add_material_button,
            self.remove_material_button,
            self.new_version_button,
        ):
            button.setMinimumHeight(38)
            button.setMaximumHeight(42)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            "Material",
            "Quantidade",
            "Unidade",
            "Custo estimado",
        ])

        self.table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self.table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.table.setWordWrap(False)
        self.table.itemSelectionChanged.connect(self._update_remove_button)

        layout.addWidget(self.table, 1)
        self.table.verticalHeader().setDefaultSectionSize(34)

        total_layout = QHBoxLayout()

        total_layout.addStretch()

        self.total_label = QLabel()
        self.total_label.setObjectName("page_title")
        total_layout.addWidget(self.total_label)

        layout.addLayout(total_layout)

    def load_recipe_details(self):
        if self.recipe is None:
            self.close()
            return

        self.product_label.setText(self.recipe["product_name"])
        self.recipe_label.setText(self.recipe["name"])

        versions = self.recipe["versions"]

        self.version_combo.blockSignals(True)
        self.version_combo.clear()

        for version in versions:
            version_number = version["version_number"]
            status = (
                "Finalizada"
                if version["finalized_at"] is not None
                else "Em edição"
            )

            self.version_combo.addItem(
                f"Versão {version_number} • {status}",
                version_number,
            )

        self.version_combo.blockSignals(False)

        if versions:
            self.version_combo.setCurrentIndex(
                self.version_combo.count() - 1
            )
            self.load_selected_version()

        if not versions:
            self.version_label.setText("Nenhuma versão cadastrada.")
            self.table.setRowCount(0)
            self.total_label.setText("Custo estimado: -")
            return

        version_number = version["version_number"]
        finalized = version["finalized_at"] is not None

        status = "Finalizada" if finalized else "Em edição"

        self.version_label.setText(
            f"Versão {version_number} • {status}"
        )
        self.add_material_button.setEnabled(not finalized)
        self.finalize_button.setEnabled(not finalized)
        self.new_version_button.setEnabled(finalized)
        items = version["items"]
        self.table.setRowCount(len(items))

        for row, item in enumerate(items):
            values = [
                item["material_name_snapshot"],
                self._format_quantity(item["quantity_milli"]),
                item["unit_symbol_snapshot"],
                "-",
            ]

            for column, value in enumerate(values):
                cell = QTableWidgetItem(str(value))
                cell.setToolTip(str(value))
                if column == 0:
                    cell.setData(Qt.ItemDataRole.UserRole, item["id"])
                self.table.setItem(row, column, cell)

        self._update_remove_button()
        try:
            cost = calculate_recipe_cost(
                self.recipe_id,
                version_number,
            )

            for row, item in enumerate(cost["items"]):
                self.table.setItem(
                    row,
                    3,
                    QTableWidgetItem(
                        self._format_price(item["cost_cents"])
                    ),
                )

            self.total_label.setText(
                f"Custo estimado: "
                f"{self._format_price(cost['total_cost_cents'])}"
            )

        except ValueError as error:
            self.total_label.setText(
                f"Custo indisponível: {error}"
            )

    @staticmethod
    def _format_quantity(quantity_milli):
        quantity = quantity_milli / 1_000_000

        return (
            f"{quantity:,.6f}"
            .replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )

    @staticmethod
    def _format_price(price_cents):
        return (
            f"R$ {price_cents / 100:,.2f}"
            .replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )

    def _update_remove_button(self):
        version_number = self.version_combo.currentData()
        version = next(
            (
                item for item in self.recipe["versions"]
                if item["version_number"] == version_number
            ),
            None,
        )
        can_edit = (
            version is not None
            and version["finalized_at"] is None
            and version_number == self.recipe["versions"][-1]["version_number"]
        )
        self.remove_material_button.setEnabled(
            can_edit and self.table.currentRow() >= 0
        )

    def remove_selected_material(self):
        row = self.table.currentRow()
        if row < 0:
            return
        item = self.table.item(row, 0)
        if item is None:
            return
        recipe_item_id = item.data(Qt.ItemDataRole.UserRole)
        material_name = item.text()
        confirmation = QMessageBox.question(
            self,
            "Remover material",
            f"Deseja remover '{material_name}' da versão atual da receita?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirmation != QMessageBox.StandardButton.Yes:
            return
        try:
            remove_recipe_item(self.recipe_id, recipe_item_id)
            self.recipe = get_recipe(self.recipe_id)
            self.load_recipe_details()
        except ValueError as error:
            QMessageBox.warning(
                self,
                "Não foi possível remover",
                str(error),
            )

    def open_add_material(self):
        if not self.recipe["versions"]:
            return

        version = self.recipe["versions"][-1]

        if version["finalized_at"] is not None:
            QMessageBox.information(
                self,
                "Versão finalizada",
                "Crie uma nova versão antes de alterar a composição.",
            )
            return

        dialog = RecipeItemForm(self.recipe_id, self)

        if dialog.exec():
            self.recipe = get_recipe(self.recipe_id)
            self.load_recipe_details()

    def finalize_version(self):
        if not self.recipe["versions"]:
            return

        version = self.recipe["versions"][-1]

        if version["finalized_at"] is not None:
            return

        confirmation = QMessageBox.question(
            self,
            "Finalizar receita",
            "Deseja finalizar esta versão da receita? "
            "Depois disso, ela não poderá mais ser alterada.",
        )

        if confirmation != QMessageBox.StandardButton.Yes:
            return

        try:
            finalize_recipe_version(self.recipe_id)

            QMessageBox.information(
                self,
                "Receita finalizada",
                "A versão da receita foi finalizada com sucesso.",
            )

            self.recipe = get_recipe(self.recipe_id)
            self.load_recipe_details()

        except ValueError as error:
            QMessageBox.warning(
                self,
                "Não foi possível finalizar",
                str(error),
            )

    def create_new_version(self):
        if not self.recipe["versions"]:
            return

        version = self.recipe["versions"][-1]

        if version["finalized_at"] is None:
            return

        confirmation = QMessageBox.question(
            self,
            "Criar nova versão",
            "Deseja criar uma nova versão desta receita? "
            "A composição atual será copiada.",
        )

        if confirmation != QMessageBox.StandardButton.Yes:
            return

        try:
            create_recipe_version(self.recipe_id)

            QMessageBox.information(
                self,
                "Nova versão criada",
                "A nova versão foi criada com sucesso.",
            )

            self.recipe = get_recipe(self.recipe_id)
            self.load_recipe_details()

        except ValueError as error:
            QMessageBox.warning(
                self,
                "Não foi possível criar a versão",
                str(error),
            )
    def load_selected_version(self):
        version_number = self.version_combo.currentData()

        if version_number is None:
            return

        version = next(
            (
                item
                for item in self.recipe["versions"]
                if item["version_number"] == version_number
            ),
            None,
        )

        if version is None:
            return

        finalized = version["finalized_at"] is not None

        status = "Finalizada" if finalized else "Em edição"

        self.version_label.setText(
            f"Versão {version_number} • {status}"
        )

        self.add_material_button.setEnabled(
            not finalized and version_number == self.recipe["versions"][-1]["version_number"]
        )

        self.finalize_button.setEnabled(
            not finalized and version_number == self.recipe["versions"][-1]["version_number"]
        )

        self.new_version_button.setEnabled(
            finalized and version_number == self.recipe["versions"][-1]["version_number"]
        )
        self.remove_material_button.setEnabled(
            not finalized and version_number == self.recipe["versions"][-1]["version_number"]
            and self.table.currentRow() >= 0
        )

        items = version["items"]
        self.table.setRowCount(len(items))

        for row, item in enumerate(items):
            values = [
                item["material_name_snapshot"],
                self._format_quantity(item["quantity_milli"]),
                item["unit_symbol_snapshot"],
                "-",
            ]

            for column, value in enumerate(values):
                cell = QTableWidgetItem(str(value))
                if column == 0:
                    cell.setData(Qt.ItemDataRole.UserRole, item["id"])
                self.table.setItem(row, column, cell)

        self._update_remove_button()
        try:
            cost = calculate_recipe_cost(
                self.recipe_id,
                version_number,
            )

            for row, item in enumerate(cost["items"]):
                self.table.setItem(
                    row,
                    3,
                    QTableWidgetItem(
                        self._format_price(item["cost_cents"])
                    ),
                )

            self.total_label.setText(
                f"Custo estimado: "
                f"{self._format_price(cost['total_cost_cents'])}"
            )

        except ValueError as error:
            self.total_label.setText(
                f"Custo indisponível: {error}"
            )