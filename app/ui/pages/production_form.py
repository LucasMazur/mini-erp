from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
)

from app.services.product_service import list_products
from app.services.recipe_service import get_recipe, list_product_recipes
from app.services.production_service import (
    calculate_required_materials,
    check_production_stock,
    register_production,
)
from app.services.recipe_cost_calculator import calculate_recipe_cost


class ProductionForm(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Registrar produção")
        self.resize(850, 650)
        self.setMinimumSize(700, 520)
        self._create_interface()
        self._load_products()

    def _create_interface(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(14)

        title = QLabel("Nova produção")
        title.setObjectName("page_title")
        layout.addWidget(title)

        subtitle = QLabel(
            "Selecione uma receita finalizada e confira o consumo antes de registrar."
        )
        subtitle.setObjectName("page_subtitle")
        layout.addWidget(subtitle)

        form = QFormLayout()
        self.product_combo = QComboBox()
        self.product_combo.currentIndexChanged.connect(self._load_recipes)
        form.addRow("Produto:", self.product_combo)

        self.recipe_combo = QComboBox()
        self.recipe_combo.currentIndexChanged.connect(self._load_versions)
        form.addRow("Receita:", self.recipe_combo)

        self.version_combo = QComboBox()
        self.version_combo.currentIndexChanged.connect(self._refresh_preview)
        form.addRow("Versão:", self.version_combo)

        self.quantity_spin = QSpinBox()
        self.quantity_spin.setRange(1, 100000)
        self.quantity_spin.setValue(1)
        self.quantity_spin.valueChanged.connect(self._refresh_preview)
        form.addRow("Quantidade a produzir:", self.quantity_spin)
        layout.addLayout(form)

        materials_title = QLabel("Consumo previsto e disponibilidade")
        materials_title.setObjectName("page_subtitle")
        layout.addWidget(materials_title)

        self.materials_table = QTableWidget()
        self.materials_table.setColumnCount(5)
        self.materials_table.setHorizontalHeaderLabels([
            "Material", "Necessário", "Disponível", "Unidade", "Situação"
        ])
        self.materials_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self.materials_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.materials_table.verticalHeader().setVisible(False)
        self.materials_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.materials_table)

        self.stock_status = QLabel("Selecione uma receita finalizada.")
        self.stock_status.setWordWrap(True)
        layout.addWidget(self.stock_status)

        self.cost_label = QLabel("Custo estimado do lote: R$ 0,00")
        self.cost_label.setObjectName("page_title")
        self.cost_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.cost_label)

        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Observações (opcional)")
        self.notes_input.setMaximumHeight(75)
        layout.addWidget(self.notes_input)

        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel = QPushButton("Cancelar")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(cancel)

        self.register_button = QPushButton("Confirmar produção")
        self.register_button.setObjectName("primary_button")
        self.register_button.clicked.connect(self._register)
        self.register_button.setEnabled(False)
        buttons.addWidget(self.register_button)
        layout.addLayout(buttons)

    def _load_products(self):
        self.product_combo.blockSignals(True)
        self.product_combo.clear()
        for product in list_products():
            self.product_combo.addItem(
                product["name"], product["id"]
            )
        self.product_combo.blockSignals(False)
        self._load_recipes()

    def _load_recipes(self):
        product_id = self.product_combo.currentData()
        self.recipe_combo.blockSignals(True)
        self.recipe_combo.clear()
        if product_id is not None:
            for recipe in list_product_recipes(product_id):
                if recipe["active"]:
                    self.recipe_combo.addItem(
                        recipe["name"], recipe["id"]
                    )
        self.recipe_combo.blockSignals(False)
        self._load_versions()

    def _load_versions(self):
        recipe_id = self.recipe_combo.currentData()
        self.version_combo.blockSignals(True)
        self.version_combo.clear()

        if recipe_id is not None:
            recipe = get_recipe(recipe_id)
            for version in reversed(recipe["versions"]):
                if version["finalized_at"] is not None and version["items"]:
                    self.version_combo.addItem(
                        f'Versão {version["version_number"]}',
                        version["version_number"],
                    )

        self.version_combo.blockSignals(False)
        self._refresh_preview()

    @staticmethod
    def _format_quantity(quantity_milli):
        value = quantity_milli / 1000
        return f"{value:,.3f}".replace(",", "X").replace(
            ".", ","
        ).replace("X", ".")

    @staticmethod
    def _format_currency(cents):
        value = cents / 100
        return f"R$ {value:,.2f}".replace(",", "X").replace(
            ".", ","
        ).replace("X", ".")

    def _refresh_preview(self):
        recipe_id = self.recipe_combo.currentData()
        version_number = self.version_combo.currentData()
        quantity = self.quantity_spin.value()
        self.materials_table.setRowCount(0)
        self.register_button.setEnabled(False)

        if recipe_id is None or version_number is None:
            self.stock_status.setText(
                "Não há versões finalizadas com materiais para este produto."
            )
            self.cost_label.setText("Custo estimado do lote: R$ 0,00")
            return

        try:
            required = calculate_required_materials(
                recipe_id, quantity, version_number
            )
            stock = check_production_stock(required["materials"])
        except ValueError as error:
            self.stock_status.setText(str(error))
            return

        try:
            cost = calculate_recipe_cost(recipe_id, version_number)
            total_cost = cost["total_cost_cents"] * quantity
        except ValueError:
            total_cost = 0
            cost_by_material = {}

        self.materials_table.setRowCount(len(stock["items"]))
        for row, item in enumerate(stock["items"]):
            values = [
                item["material_name"],
                self._format_quantity(item["quantity_milli"]),
                self._format_quantity(item["available_quantity_milli"]),
                item["unit_symbol"],
                "Disponível" if item["sufficient"] else "Estoque insuficiente",
            ]
            for column, value in enumerate(values):
                cell = QTableWidgetItem(str(value))
                if column == 4:
                    cell.setForeground(
                        QColor("#187443")
                        if item["sufficient"]
                        else QColor("#B42318")
                    )
                self.materials_table.setItem(row, column, cell)

        self.stock_status.setText(
            "Estoque suficiente para produzir."
            if stock["sufficient"]
            else "Estoque insuficiente. Reponha os materiais antes de registrar."
        )
        self.cost_label.setText(
            f"Custo estimado do lote: {self._format_currency(total_cost)}"
        )
        self.register_button.setEnabled(stock["sufficient"])

    def _register(self):
        product_id = self.product_combo.currentData()
        recipe_id = self.recipe_combo.currentData()
        version_number = self.version_combo.currentData()
        quantity = self.quantity_spin.value()

        if None in (product_id, recipe_id, version_number):
            return

        confirmation = QMessageBox.question(
            self,
            "Confirmar produção",
            (
                f"Registrar a produção de {quantity} unidade(s)?\n\n"
                "O estoque de materiais será baixado e os produtos acabados "
                "serão adicionados ao estoque."
            ),
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirmation != QMessageBox.StandardButton.Yes:
            return

        try:
            production_id = register_production(
                product_id=product_id,
                recipe_id=recipe_id,
                quantity=quantity,
                version_number=version_number,
                notes=self.notes_input.toPlainText(),
            )
        except (ValueError, RuntimeError) as error:
            QMessageBox.warning(
                self, "Não foi possível registrar", str(error)
            )
            self._refresh_preview()
            return

        QMessageBox.information(
            self,
            "Produção registrada",
            f"Produção #{production_id} registrada com sucesso.",
        )
        self.accept()
