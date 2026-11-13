from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
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
from app.services.image_storage import (
    delete_product_image,
    resolve_product_image,
    save_product_image,
)
from app.services.product_service import (
    create_product,
    generate_next_product_code,
    update_product,
)


class ProductForm(QDialog):
    def __init__(self, parent=None, product=None):
        super().__init__(parent)
        self.product = product
        self._selected_image_source = None
        self._remove_image = False
        self.setWindowTitle("Editar produto" if product else "Novo produto")
        self.resize(620, 560)
        self.setMinimumSize(480, 420)
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
        from PySide6.QtWidgets import QScrollArea, QWidget

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 18)
        root.setSpacing(12)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(4, 4, 10, 12)
        layout.setSpacing(12)

        title = QLabel("Editar produto" if self.product else "Novo produto")
        title.setObjectName("page_title")
        layout.addWidget(title)

        subtitle = QLabel(
            "Mantenha os dados comerciais e de identificação do produto."
        )
        subtitle.setObjectName("page_subtitle")
        layout.addWidget(subtitle)

        identity_card, identity_layout = self._create_card(
            "Identificação",
            "Informações básicas para localizar o produto no estoque.",
        )
        identity_form = QFormLayout()
        identity_form.setHorizontalSpacing(14)
        identity_form.setVerticalSpacing(8)

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

        image_card, image_layout = self._create_card(
            "Imagem do produto",
            "Escolha uma foto para identificar o produto no cadastro.",
        )
        image_row = QHBoxLayout()
        self.image_preview = QLabel("Sem imagem")
        self.image_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_preview.setFixedSize(150, 150)
        self.image_preview.setStyleSheet(
            "QLabel { background: #F4F6FA; border: 1px dashed #C0C6CC; "
            "border-radius: 10px; color: #6B7280; }"
        )
        image_row.addWidget(self.image_preview)

        image_actions = QVBoxLayout()
        select_image_button = QPushButton("Selecionar imagem")
        select_image_button.clicked.connect(self._select_product_image)
        image_actions.addWidget(select_image_button)

        remove_image_button = QPushButton("Remover imagem")
        remove_image_button.clicked.connect(self._remove_product_image)
        image_actions.addWidget(remove_image_button)
        image_actions.addStretch()
        image_row.addLayout(image_actions)
        image_row.addStretch()
        image_layout.addLayout(image_row)
        layout.addWidget(image_card)

        price_card, price_layout = self._create_card(
            "Preço de venda",
            "Este valor será sugerido automaticamente ao registrar uma venda.",
        )
        self.price_checkbox = QCheckBox(
            "Definir preço padrão para este produto"
        )
        price_layout.addWidget(self.price_checkbox)

        self.price_input = QDoubleSpinBox()
        self.price_input.setDecimals(2)
        self.price_input.setMinimum(0)
        self.price_input.setMaximum(999999999)
        self.price_input.setPrefix("R$ ")
        self.price_input.setMinimumHeight(38)
        self.price_input.setEnabled(False)
        price_layout.addWidget(self.price_input)

        self.price_hint = QLabel(
            "O preço poderá ser ajustado individualmente durante uma venda, "
            "sem alterar este cadastro."
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
        self.notes_input.setPlaceholderText(
            "Adicione informações relevantes..."
        )
        self.notes_input.setMinimumHeight(55)
        self.notes_input.setMaximumHeight(75)
        notes_layout.addWidget(self.notes_input)
        layout.addWidget(notes_card)
        layout.addStretch()

        scroll.setWidget(content)
        root.addWidget(scroll, 1)

        footer = QHBoxLayout()
        footer.addStretch()
        cancel_button = QPushButton("Cancelar")
        cancel_button.clicked.connect(self.reject)
        footer.addWidget(cancel_button)

        save_button = QPushButton(
            "Salvar alterações" if self.product else "Cadastrar produto"
        )
        save_button.setObjectName("primary_button")
        save_button.clicked.connect(self._save_product)
        footer.addWidget(save_button)
        root.addLayout(footer)

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
        self._show_product_image(self.product.get("image_path"))

    def _show_product_image(self, image_path=None):
        if not image_path:
            self.image_preview.setPixmap(QPixmap())
            self.image_preview.setText("Sem imagem")
            return

        path = resolve_product_image(image_path)
        pixmap = QPixmap(str(path)) if path else QPixmap()
        if pixmap.isNull():
            self.image_preview.setPixmap(QPixmap())
            self.image_preview.setText("Imagem indisponível")
            return

        self.image_preview.setText("")
        self.image_preview.setPixmap(
            pixmap.scaled(
                self.image_preview.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def _select_product_image(self):
        source_path, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar imagem do produto",
            "",
            "Imagens (*.jpg *.jpeg *.png *.webp)",
        )
        if not source_path:
            return

        pixmap = QPixmap(source_path)
        if pixmap.isNull():
            QMessageBox.warning(
                self,
                "Imagem inválida",
                "Não foi possível abrir o arquivo selecionado.",
            )
            return

        self._selected_image_source = source_path
        self._remove_image = False
        self.image_preview.setText("")
        self.image_preview.setPixmap(
            pixmap.scaled(
                self.image_preview.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def _remove_product_image(self):
        self._selected_image_source = None
        self._remove_image = True
        self._show_product_image()

    def _save_product(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(
                self, "Campo obrigatório", "Informe o nome do produto."
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

        price_cents = (
            round(self.price_input.value() * 100)
            if self.price_checkbox.isChecked()
            else None
        )

        old_image_path = (
            self.product.get("image_path") if self.product else None
        )
        new_image_path = None
        image_changed = self._selected_image_source is not None or self._remove_image

        try:
            if self._selected_image_source:
                new_image_path = save_product_image(
                    self._selected_image_source
                )

            common_values = {
                "name": name,
                "code": self.code_input.text(),
                "category_id": self.category_combo.currentData(),
                "stock_unit_id": self.unit_combo.currentData(),
                "sale_price_cents": price_cents,
                "notes": self.notes_input.toPlainText(),
            }

            if self.product:
                if image_changed:
                    update_product(
                        product_id=self.product["id"],
                        image_path=new_image_path,
                        **common_values,
                    )
                else:
                    update_product(
                        product_id=self.product["id"],
                        **common_values,
                    )
                message = "Produto atualizado com sucesso!"
            else:
                create_product(
                    image_path=new_image_path,
                    **common_values,
                )
                message = "Produto cadastrado com sucesso!"

            if image_changed and old_image_path:
                delete_product_image(old_image_path)

            QMessageBox.information(self, "Sucesso", message)
            self.accept()
        except (ValueError, OSError) as error:
            if new_image_path:
                delete_product_image(new_image_path)
            QMessageBox.critical(self, "Erro ao salvar", str(error))
