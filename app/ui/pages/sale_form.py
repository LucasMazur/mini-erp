from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
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
from app.services.sales_service import PAYMENT_METHODS, create_sale


class SaleForm(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.items = []
        self.products = {}
        self.setWindowTitle("Nova venda")
        self.resize(940, 760)
        self.setMinimumSize(780, 650)
        self._create_interface()
        self._load_products()

    def _create_card(self, title_text, hint=None):
        card = QFrame()
        card.setObjectName("form_card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 17, 20, 19)
        card_layout.setSpacing(10)

        title = QLabel(title_text)
        title.setObjectName("form_section_title")
        card_layout.addWidget(title)

        if hint:
            description = QLabel(hint)
            description.setObjectName("form_section_hint")
            description.setWordWrap(True)
            card_layout.addWidget(description)
        return card, card_layout

    def _create_interface(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 25, 28, 24)
        layout.setSpacing(15)

        title = QLabel("Nova venda")
        title.setObjectName("page_title")
        layout.addWidget(title)

        subtitle = QLabel(
            "Selecione os produtos, confira os valores e confirme a venda."
        )
        subtitle.setObjectName("page_subtitle")
        layout.addWidget(subtitle)

        info_card, info_layout = self._create_card(
            "Dados da venda", "Informe a data e a forma de pagamento."
        )
        info_form = QFormLayout()
        info_form.setVerticalSpacing(12)
        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDisplayFormat("dd/MM/yyyy")
        self.date_input.setDate(QDate.currentDate())
        info_form.addRow("Data *", self.date_input)

        self.payment_combo = QComboBox()
        self.payment_combo.addItems(sorted(PAYMENT_METHODS))
        info_form.addRow("Forma de pagamento *", self.payment_combo)
        info_layout.addLayout(info_form)
        layout.addWidget(info_card)

        products_card, products_layout = self._create_card(
            "Produtos", "O preço padrão do cadastro será carregado automaticamente. Você pode ajustá-lo somente nesta venda."
        )
        product_form = QFormLayout()
        product_form.setVerticalSpacing(12)

        self.product_combo = QComboBox()
        product_form.addRow("Produto", self.product_combo)

        self.quantity_input = QSpinBox()
        self.quantity_input.setRange(1, 100000)
        self.quantity_input.setMinimumHeight(42)
        product_form.addRow("Quantidade", self.quantity_input)

        self.price_input = QDoubleSpinBox()
        self.price_input.setDecimals(2)
        self.price_input.setMaximum(999999.99)
        self.price_input.setPrefix("R$ ")
        self.price_input.setMinimumHeight(42)
        product_form.addRow("Preço unitário", self.price_input)
        products_layout.addLayout(product_form)

        self.price_hint = QLabel("Selecione um produto para carregar o preço padrão.")
        self.price_hint.setObjectName("form_section_hint")
        products_layout.addWidget(self.price_hint)

        add_button = QPushButton("+ Adicionar produto à venda")
        add_button.setObjectName("primary_button")
        add_button.clicked.connect(self._add_item)
        products_layout.addWidget(add_button)
        layout.addWidget(products_card)

        items_card, items_layout = self._create_card(
            "Itens da venda", "Confira os produtos adicionados antes de confirmar."
        )
        self.items_table = QTableWidget()
        self.items_table.setColumnCount(5)
        self.items_table.setHorizontalHeaderLabels([
            "Produto", "Quantidade", "Preço unitário", "Subtotal", "Ação"
        ])
        self.items_table.setMinimumHeight(150)
        self.items_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.items_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.items_table.verticalHeader().setVisible(False)
        self.items_table.horizontalHeader().setStretchLastSection(True)
        items_layout.addWidget(self.items_table)

        discount_form = QFormLayout()
        self.discount_input = QDoubleSpinBox()
        self.discount_input.setDecimals(2)
        self.discount_input.setMaximum(999999.99)
        self.discount_input.setPrefix("R$ ")
        self.discount_input.setMinimumHeight(42)
        self.discount_input.valueChanged.connect(self._update_total)
        discount_form.addRow("Desconto geral", self.discount_input)
        items_layout.addLayout(discount_form)

        self.total_label = QLabel("Total da venda: R$ 0,00")
        self.total_label.setObjectName("sale_total")
        self.total_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        items_layout.addWidget(self.total_label)
        layout.addWidget(items_card)

        notes_card, notes_layout = self._create_card(
            "Observações", "Campo opcional para informações sobre esta venda."
        )
        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Ex.: pedido pelo Instagram...")
        self.notes_input.setMaximumHeight(65)
        notes_layout.addWidget(self.notes_input)
        layout.addWidget(notes_card)

        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel = QPushButton("Cancelar")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(cancel)

        self.save_button = QPushButton("Confirmar venda")
        self.save_button.setObjectName("primary_button")
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self._save_sale)
        buttons.addWidget(self.save_button)
        layout.addLayout(buttons)

    def _load_products(self):
        self.product_combo.clear()
        self.products = {}
        for product in list_products():
            self.products[product["id"]] = product
            self.product_combo.addItem(
                f'{product["code"] or ""} • {product["name"]} ({product["unit_symbol"]})',
                product["id"],
            )
        self.product_combo.currentIndexChanged.connect(self._update_suggested_price)
        self._update_suggested_price()

    def _update_suggested_price(self):
        product = self.products.get(self.product_combo.currentData())
        if product:
            price_cents = product["sale_price_cents"]
            self.price_input.setValue((price_cents or 0) / 100)
            self.price_hint.setText(
                f"Preço padrão do cadastro: {self._currency(price_cents or 0)}"
                if price_cents is not None
                else "Este produto ainda não possui preço padrão cadastrado."
            )
        else:
            self.price_input.setValue(0)
            self.price_hint.setText("Nenhum produto disponível.")

    @staticmethod
    def _currency(cents):
        return f"R$ {cents / 100:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    def _add_item(self):
        product_id = self.product_combo.currentData()
        if product_id is None:
            return
        if any(item["product_id"] == product_id for item in self.items):
            QMessageBox.warning(
                self, "Produto já adicionado",
                "Esse produto já está na venda. Remova-o para alterar a quantidade.",
            )
            return

        product = self.products[product_id]
        quantity = self.quantity_input.value()
        unit_price_cents = round(self.price_input.value() * 100)
        self.items.append({
            "product_id": product_id,
            "product_name": product["name"],
            "quantity": quantity,
            "unit_price_cents": unit_price_cents,
            "line_total_cents": quantity * unit_price_cents,
        })
        self._refresh_items()

    def _refresh_items(self):
        self.items_table.setRowCount(len(self.items))
        for row, item in enumerate(self.items):
            values = [
                item["product_name"],
                str(item["quantity"]),
                self._currency(item["unit_price_cents"]),
                self._currency(item["line_total_cents"]),
            ]
            for column, value in enumerate(values):
                self.items_table.setItem(row, column, QTableWidgetItem(value))
            remove = QPushButton("Remover")
            remove.clicked.connect(
                lambda checked=False, index=row: self._remove_item(index)
            )
            self.items_table.setCellWidget(row, 4, remove)
        self._update_total()

    def _remove_item(self, index):
        if 0 <= index < len(self.items):
            self.items.pop(index)
            self._refresh_items()

    def _update_total(self):
        subtotal = sum(item["line_total_cents"] for item in self.items)
        discount = round(self.discount_input.value() * 100)
        total = subtotal - discount
        self.total_label.setText(f"Total da venda: {self._currency(max(total, 0))}")
        self.save_button.setEnabled(bool(self.items) and 0 <= discount <= subtotal)

    def _save_sale(self):
        try:
            sale_id = create_sale(
                sale_date=self.date_input.date().toString("yyyy-MM-dd"),
                items=[
                    {
                        "product_id": item["product_id"],
                        "quantity": item["quantity"],
                        "unit_price_cents": item["unit_price_cents"],
                    }
                    for item in self.items
                ],
                payment_method=self.payment_combo.currentText(),
                discount_cents=round(self.discount_input.value() * 100),
                notes=self.notes_input.toPlainText(),
            )
        except (ValueError, RuntimeError) as error:
            QMessageBox.warning(self, "Não foi possível registrar", str(error))
            return

        QMessageBox.information(
            self, "Venda registrada",
            f"Venda #{sale_id} registrada com sucesso.",
        )
        self.accept()
