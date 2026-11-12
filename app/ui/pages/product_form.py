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
    QFrame,
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
        self.setWindowTitle("Editar produto" if product else "Novo produto")
        self.resize(620, 650)
        self.setMinimumSize(540, 580)
        self._create_interface()
        self._load_options()

        if not self.product:
            try:
                self.code_input.setText(generate_next_product_code())
            except ValueError as error:
                QMessageBox.critical(
                    self, "Não foi possível gerar o código", str(error)
                )
                self.reject()
                return

        if self.product:
            self._fill_product_data()

    def _create_card(self, title_text, description):
        card = QFrame()
        card.setObjectName("form_card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 18, 20, 20)
        card_layout.setSpacing(6)

        title = QLabel(title_text)
        title.setObjectName("form_section_title")
        card_layout.addWidget(title)

        description_label = QLabel(description)
        description_label.setObjectName("form_section_hint")
        card_layout.addWidget(description_label)
        return card, card_layout

    def _create_interface(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 24)
        layout.setSpacing(16)

        title = QLabel("Editar produto" if self.product else "Novo produto")
        title.setObjectName("page_title")
        layout.addWidget(title)

        subtitle = QLabel(
            "Mantenha os dados comerciais e de identificação do produto."
        )
        subtitle.setObjectName("page_subtitle")
        layout.addWidget(subtitle)

        identity_card, identity_layout = self._create_card(
            "Identificação", "Informações básicas para localizar o produto no estoque."
        )
        identity_form = QFormLayout()
        identity_form.setLabelAlignment(identity_form.labelAlignment())
        identity_form.setHorizontalSpacing(18)
        identity_form.setVerticalSpacing(12)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Ex.: Brinco Gato Lua")
        identity_form.addRow("Nome do produto *", self.name_input)

        self.code_input = QLineEdit()
        self.code_input.setReadOnly(True)
        self.code_input.setPlaceholderText("Gerado automaticamente")
        identity_form.addRow("Código", self.code_input)

        self.category_combo = QComboBox()
        identity_form.addRow("Categoria", self.category_combo)

        self.unit_combo = QComboBox()
        identity_form.addRow("Unidade de estoque *", self.unit_combo)
        identity_layout.addLayout(identity_form)
        layout.addWidget(identity_card)

        price_card, price_layout = self._create_card(
            "Preço de venda", "Este valor será sugerido automaticamente ao registrar uma venda."
        )
        self.price_checkbox = QCheckBox("Definir preço padrão para este produto")
        price_layout.addWidget(self.price_checkbox)

        self.price_input = QDoubleSpinBox()
        self.price_input.setDecimals(2)
        self.price_input.setMinimum(0)
        self.price_input.setMaximum(999999999)
        self.price_input.setPrefix("R$ ")
        self.price_input.setMinimumHeight(44)
        self.price_input.setEnabled(False)
        price_layout.addWidget(self.price_input)

        self.price_hint = QLabel(
            "O preço poderá ser ajustado individualmente durante uma venda, sem alterar este cadastro."
        )
        self.price_hint.setObjectName("form_section_hint")
        self.price_hint.setWordWrap(True)
        price_layout.addWidget(self.price_hint)
        self.price_checkbox.toggled.connect(self.price_input.setEnabled)
        layout.addWidget(price_card)

        notes_card, notes_layout = self._create_card(
            "Observações", "Detalhes internos opcionais sobre o produto."
        )
        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Adicione informações relevantes...")
        self.notes_input.setMinimumHeight(70)
        self.notes_input.setMaximumHeight(95)
        notes_layout.addWidget(self.notes_input)
        layout.addWidget(notes_card)

        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel_button = QPushButton("Cancelar")
        cancel_button.clicked.connect(self.reject)
        buttons.addWidget(cancel_button)

        save_button = QPushButton(
            "Salvar alterações" if self.product else "Cadastrar produto"
        )
        save_button.setObjectName("primary_button")
        save_button.clicked.connect(self._save_product)
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
                f"{unit['name']} ({unit['symbol']})", unit["id"]
            )

        self.category_combo.addItem("Sem categoria", None)
        for category in categories:
            self.category_combo.addItem(category["name"], category["id"])

    def _fill_product_data(self):
        self.name_input.setText(self.product["name"])
        self.code_input.setText(self.product["code"] or "")

        category_index = self.category_combo.findData(
            self.product["category_id"]
        )
        if category_index >= 0:
            self.category_combo.setCurrentIndex(category_index)

        unit_index = self.unit_combo.findData(self.product["stock_unit_id"])
        if unit_index >= 0:
            self.unit_combo.setCurrentIndex(unit_index)

        price = self.product["sale_price_cents"]
        if price is not None:
            self.price_checkbox.setChecked(True)
            self.price_input.setValue(price / 100)

        self.notes_input.setPlainText(self.product["notes"] or "")

    def _save_product(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Campo obrigatório", "Informe o nome do produto.")
            self.name_input.setFocus()
            return

        if self.unit_combo.currentData() is None:
            QMessageBox.warning(
                self, "Unidade obrigatória",
                "Não existem unidades ativas cadastradas.",
            )
            return

        price_cents = (
            round(self.price_input.value() * 100)
            if self.price_checkbox.isChecked()
            else None
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

            QMessageBox.information(self, "Sucesso", message)
            self.accept()
        except ValueError as error:
            QMessageBox.critical(self, "Erro ao salvar", str(error))
