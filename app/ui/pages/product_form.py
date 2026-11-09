
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from app.database.connection import get_connection
from app.services.product_service import (
    create_product,
    generate_next_product_code,
    update_product,
)


class ProductForm(QDialog):
    def __init__(self, parent=None, product=None):
        super().__init__(parent)

        self.product = product

        if self.product:
            self.setWindowTitle("Editar produto")
        else:
            self.setWindowTitle("Novo produto")

        self.setMinimumWidth(450)

        self._create_interface()
        self._load_options()

        if not self.product:
            try:
                self.code_input.setText(
                    generate_next_product_code()
                )
            except ValueError as error:
                QMessageBox.critical(
                    self,
                    "Não foi possível gerar o código",
                    str(error),
                )
                self.reject()
                return

        if self.product:
            self._fill_product_data()

    def _create_interface(self):
        layout = QVBoxLayout(self)

        if self.product:
            title_text = "Editar produto"
        else:
            title_text = "Cadastrar produto"

        title = QLabel(title_text)
        title.setObjectName("page_title")
        layout.addWidget(title)

        form = QFormLayout()

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Ex.: Brinco Lua")
        form.addRow("Nome *", self.name_input)

        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("Ex.: BR001")
        form.addRow("Código", self.code_input)
        self.code_input.setReadOnly(True)
        self.code_input.setPlaceholderText(
            "Gerado automaticamente"
        )

        self.category_combo = QComboBox()
        form.addRow("Categoria", self.category_combo)

        self.unit_combo = QComboBox()
        form.addRow("Unidade de estoque *", self.unit_combo)

        self.price_checkbox = QCheckBox(
            "Informar preço de venda"
        )
        form.addRow("", self.price_checkbox)

        self.price_input = QDoubleSpinBox()
        self.price_input.setDecimals(2)
        self.price_input.setMinimum(0)
        self.price_input.setMaximum(999999999)
        self.price_input.setPrefix("R$ ")
        self.price_input.setEnabled(False)

        form.addRow("Preço de venda", self.price_input)

        self.price_checkbox.toggled.connect(
            self.price_input.setEnabled
        )

        self.notes_input = QTextEdit()
        self.notes_input.setMaximumHeight(90)
        form.addRow("Observações", self.notes_input)

        layout.addLayout(form)

        buttons = QHBoxLayout()

        cancel_button = QPushButton("Cancelar")
        cancel_button.clicked.connect(self.reject)

        if self.product:
            save_text = "Salvar alterações"
        else:
            save_text = "Salvar produto"

        save_button = QPushButton(save_text)
        save_button.setObjectName("primary_button")
        save_button.clicked.connect(self._save_product)

        buttons.addStretch()
        buttons.addWidget(cancel_button)
        buttons.addWidget(save_button)

        layout.addLayout(buttons)

    def _load_options(self):
        with get_connection() as connection:
            units = connection.execute(
                """
                SELECT id, name, symbol
                FROM units
                WHERE active = 1
                ORDER BY name
                """
            ).fetchall()

            categories = connection.execute(
                """
                SELECT id, name
                FROM categories
                WHERE kind = 'product' AND active = 1
                ORDER BY name
                """
            ).fetchall()

        for unit in units:
            self.unit_combo.addItem(
                f"{unit['name']} ({unit['symbol']})",
                unit["id"],
            )

        self.category_combo.addItem("Sem categoria", None)

        for category in categories:
            self.category_combo.addItem(
                category["name"],
                category["id"],
            )

    def _fill_product_data(self):
        self.name_input.setText(self.product["name"])
        self.code_input.setText(self.product["code"] or "")

        category_index = self.category_combo.findData(
            self.product["category_id"]
        )
        if category_index >= 0:
            self.category_combo.setCurrentIndex(category_index)

        unit_index = self.unit_combo.findData(
            self.product["stock_unit_id"]
        )
        if unit_index >= 0:
            self.unit_combo.setCurrentIndex(unit_index)

        price = self.product["sale_price_cents"]

        if price is not None:
            self.price_checkbox.setChecked(True)
            self.price_input.setValue(price / 100)

        self.notes_input.setPlainText(
            self.product["notes"] or ""
        )

    def _save_product(self):
        name = self.name_input.text().strip()

        if not name:
            QMessageBox.warning(
                self,
                "Campo obrigatório",
                "Informe o nome do produto.",
            )
            self.name_input.setFocus()
            return

        if self.unit_combo.currentData() is None:
            QMessageBox.warning(
                self,
                "Unidade obrigatória",
                "Não existem unidades ativas cadastradas.",
            )
            return

        price_cents = None

        if self.price_checkbox.isChecked():
            price_cents = round(
                self.price_input.value() * 100
            )

        try:
            if self.product:
                update_product(
                    product_id=self.product["id"],
                    name=name,
                    code=self.code_input.text(),
                    category_id=self.category_combo.currentData(),
                    stock_unit_id=self.unit_combo.currentData(),
                    sale_price_cents=price_cents,
                    notes=self.notes_input.toPlainText(),
                )

                message = "Produto atualizado com sucesso!"

            else:
                create_product(
                    name=name,
                    code=self.code_input.text(),
                    category_id=self.category_combo.currentData(),
                    stock_unit_id=self.unit_combo.currentData(),
                    sale_price_cents=price_cents,
                    notes=self.notes_input.toPlainText(),
                )

                message = "Produto cadastrado com sucesso!"

            QMessageBox.information(
                self,
                "Sucesso",
                message,
            )

            self.accept()

        except ValueError as error:
            QMessageBox.critical(
                self,
                "Erro ao salvar",
                str(error),
            )
