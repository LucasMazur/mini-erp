from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)

from app.services.product_service import list_products
from app.services.recipe_service import create_recipe


class RecipeForm(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Nova receita")
        self.setMinimumWidth(420)

        self._create_interface()
        self._load_products()

    def _create_interface(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.product_combo = QComboBox()
        form.addRow("Produto:", self.product_combo)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Ex.: Receita padrão")
        form.addRow("Nome da receita:", self.name_input)

        self.default_checkbox = QCheckBox(
            "Definir como receita padrão do produto"
        )
        form.addRow("", self.default_checkbox)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )

        buttons.accepted.connect(self.save_recipe)
        buttons.rejected.connect(self.reject)

        layout.addWidget(buttons)

    def _load_products(self):
        products = list_products()

        for product in products:
            self.product_combo.addItem(
                product["name"],
                product["id"],
            )

        if not products:
            self.product_combo.addItem("Nenhum produto cadastrado")
            self.product_combo.setEnabled(False)

    def save_recipe(self):
        product_id = self.product_combo.currentData()
        name = self.name_input.text()
        is_default = self.default_checkbox.isChecked()

        if product_id is None:
            QMessageBox.warning(
                self,
                "Atenção",
                "Cadastre um produto antes de criar uma receita.",
            )
            return

        try:
            create_recipe(
                product_id=product_id,
                name=name,
                is_default=is_default,
            )

            QMessageBox.information(
                self,
                "Sucesso",
                "Receita cadastrada com sucesso!",
            )

            self.accept()

        except ValueError as error:
            QMessageBox.warning(
                self,
                "Não foi possível cadastrar",
                str(error),
            )