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
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.database.connection import get_connection
from app.services.purchase_service import create_purchase


class PurchaseForm(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.items = []

        self.setWindowTitle("Nova compra")
        self.resize(950, 700)
        self.setMinimumSize(800, 600)

        self._create_interface()
        self._load_options()

    def _create_interface(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)

        scroll_area.setWidget(content)
        main_layout.addWidget(scroll_area)

        title = QLabel("Registrar compra")
        title.setObjectName("page_title")
        layout.addWidget(title)

        subtitle = QLabel(
            "Registre compras de materiais e atualize seu estoque."
        )
        subtitle.setObjectName("page_subtitle")
        layout.addWidget(subtitle)

        form = QFormLayout()

        self.supplier_combo = QComboBox()
        form.addRow("Fornecedor", self.supplier_combo)

        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDisplayFormat("dd/MM/yyyy")
        self.date_input.setDate(QDate.currentDate())
        form.addRow("Data da compra *", self.date_input)

        self.invoice_input = QLineEdit()
        self.invoice_input.setPlaceholderText(
            "Número da nota fiscal (opcional)"
        )
        form.addRow("Nota fiscal", self.invoice_input)

        layout.addLayout(form)

        items_title = QLabel("Itens da compra")
        items_title.setObjectName("page_subtitle")
        layout.addWidget(items_title)

        self.material_combo = QComboBox()
        self.unit_combo = QComboBox()

        item_form = QFormLayout()
        item_form.addRow("Material", self.material_combo)
        item_form.addRow("Unidade de compra", self.unit_combo)

        self.quantity_input = QDoubleSpinBox()
        self.quantity_input.setDecimals(6)
        self.quantity_input.setMinimum(0.000001)
        self.quantity_input.setMaximum(999999999)
        self.quantity_input.setSingleStep(1)
        item_form.addRow("Quantidade", self.quantity_input)

        self.item_value_input = QDoubleSpinBox()
        self.item_value_input.setDecimals(2)
        self.item_value_input.setMaximum(999999999)
        self.item_value_input.setPrefix("R$ ")
        item_form.addRow("Valor total do item", self.item_value_input)

        layout.addLayout(item_form)

        add_button = QPushButton("+ Adicionar item")
        add_button.clicked.connect(self._add_item)
        layout.addWidget(add_button)

        self.items_table = QTableWidget()
        self.items_table.setColumnCount(5)
        self.items_table.setHorizontalHeaderLabels([
            "Material",
            "Quantidade",
            "Unidade",
            "Valor",
            "Ação",
        ])
        self.items_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self.items_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.items_table.verticalHeader().setVisible(False)
        self.items_table.horizontalHeader().setStretchLastSection(True)

        self.items_table.setMinimumHeight(150)
        self.items_table.setMaximumHeight(220)
        self.items_table.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
)

        layout.addWidget(self.items_table)

        totals_form = QFormLayout()

        self.freight_input = QDoubleSpinBox()
        self.freight_input.setDecimals(2)
        self.freight_input.setMaximum(999999999)
        self.freight_input.setPrefix("R$ ")
        totals_form.addRow("Frete", self.freight_input)

        self.discount_input = QDoubleSpinBox()
        self.discount_input.setDecimals(2)
        self.discount_input.setMaximum(999999999)
        self.discount_input.setPrefix("R$ ")
        totals_form.addRow("Desconto", self.discount_input)

        layout.addLayout(totals_form)

        self.total_label = QLabel("Total: R$ 0,00")
        self.total_label.setObjectName("page_title")
        self.total_label.setAlignment(
            Qt.AlignmentFlag.AlignRight
        )
        layout.addWidget(self.total_label)

        self.notes_input = QTextEdit()
        self.notes_input.setMaximumHeight(65)
        self.notes_input.setPlaceholderText(
            "Observações da compra..."
        )
        layout.addWidget(self.notes_input)

        buttons = QHBoxLayout()
        buttons.addStretch()

        cancel_button = QPushButton("Cancelar")
        cancel_button.clicked.connect(self.reject)
        buttons.addWidget(cancel_button)

        self.save_button = QPushButton("Registrar compra")
        self.save_button.setObjectName("primary_button")
        self.save_button.setEnabled(False)
        buttons.addWidget(self.save_button)
        self.save_button.clicked.connect(self._save_purchase)

        layout.addLayout(buttons)

        self.freight_input.valueChanged.connect(
            self._update_totals
        )

        self.discount_input.valueChanged.connect(
            self._update_totals
        )

    def _load_options(self):
        with get_connection() as connection:
            suppliers = connection.execute(
                """
                SELECT id, name
                FROM suppliers
                WHERE active = 1
                ORDER BY name
                """
            ).fetchall()

            materials = connection.execute(
                """
                SELECT id, name, stock_unit_id
                FROM materials
                WHERE active = 1
                ORDER BY name
                """
            ).fetchall()

        self.supplier_combo.addItem("Sem fornecedor", None)

        for supplier in suppliers:
            self.supplier_combo.addItem(
                supplier["name"],
                supplier["id"],
            )

        for material in materials:
            self.material_combo.addItem(
                material["name"],
                material["id"],
            )

        self.material_combo.currentIndexChanged.connect(
            self._load_material_units
        )

        self._load_material_units()

    
    def _add_item(self):
        material_id = self.material_combo.currentData()
        unit_id = self.unit_combo.currentData()

        if material_id is None or unit_id is None:
            return

        quantity_milli = round(
            self.quantity_input.value() * 1_000_000
        )

        line_total_cents = round(
            self.item_value_input.value() * 100
        )

        if quantity_milli <= 0:
            return

        item = {
            "material_id": material_id,
            "material_name": self.material_combo.currentText(),
            "unit_id": unit_id,
            "unit_name": self.unit_combo.currentText(),
            "quantity_milli": quantity_milli,
            "line_total_cents": line_total_cents,
        }

        self.items.append(item)

        self._refresh_items_table()
        self._update_totals()

        self.quantity_input.setValue(1)
        self.item_value_input.setValue(0)


    def _refresh_items_table(self):
        self.items_table.setRowCount(len(self.items))

        for row, item in enumerate(self.items):
            quantity = item["quantity_milli"] / 1_000_000
            value = item["line_total_cents"] / 100

            values = [
                item["material_name"],
                f"{quantity:.3f}".replace(".", ","),
                item["unit_name"],
                f"R$ {value:.2f}".replace(".", ","),
            ]

            for column, value in enumerate(values):
                self.items_table.setItem(
                    row,
                    column,
                    QTableWidgetItem(str(value)),
                )

            remove_button = QPushButton("Remover")
            remove_button.clicked.connect(
                lambda checked=False, index=row:
                self._remove_item(index)
            )

            self.items_table.setCellWidget(
                row,
                4,
                remove_button,
            )


    def _remove_item(self, index):
        if index < 0 or index >= len(self.items):
            return

        self.items.pop(index)

        self._refresh_items_table()
        self._update_totals()


    def _update_totals(self):
        subtotal = sum(
            item["line_total_cents"]
            for item in self.items
        )

        freight = round(
            self.freight_input.value() * 100
        )

        discount = round(
            self.discount_input.value() * 100
        )

        total = subtotal + freight - discount

        formatted = f"{total / 100:,.2f}".replace(
            ",", "X"
        ).replace(".", ",").replace("X", ".")

        self.total_label.setText(
            f"Total: R$ {formatted}"
        )

        self.save_button.setEnabled(
            len(self.items) > 0 and total >= 0
        )
    def _load_material_units(self):
        material_id = self.material_combo.currentData()

        self.unit_combo.clear()

        if material_id is None:
            return

        with get_connection() as connection:
            material = connection.execute(
                """
                SELECT stock_unit_id
                FROM materials
                WHERE id = ?
                """,
                (material_id,),
            ).fetchone()

            if material is None:
                return

            stock_unit = connection.execute(
                """
                SELECT dimension
                FROM units
                WHERE id = ?
                """,
                (material["stock_unit_id"],),
            ).fetchone()

            if stock_unit is None:
                return

            units = connection.execute(
                """
                SELECT id, name, symbol
                FROM units
                WHERE dimension = ?
                AND active = 1
                ORDER BY name
                """,
                (stock_unit["dimension"],),
            ).fetchall()

        for unit in units:
            self.unit_combo.addItem(
                f"{unit['name']} ({unit['symbol']})",
                unit["id"],
            )

            if unit["id"] == material["stock_unit_id"]:
                self.unit_combo.setCurrentIndex(
                    self.unit_combo.count() - 1
                )
    def _save_purchase(self):
        if not self.items:
            QMessageBox.warning(
                self,
                "Compra sem itens",
                "Adicione pelo menos um material à compra.",
            )
            return

        subtotal = sum(
            item["line_total_cents"] for item in self.items
        )
        freight_cents = round(self.freight_input.value() * 100)
        discount_cents = round(self.discount_input.value() * 100)

        if discount_cents > subtotal:
            QMessageBox.warning(
                self,
                "Desconto inválido",
                "O desconto não pode ser maior que o subtotal dos itens.",
            )
            return

        purchase_items = [
            {
                "material_id": item["material_id"],
                "unit_id": item["unit_id"],
                "quantity_milli": item["quantity_milli"],
                "line_total_cents": item["line_total_cents"],
            }
            for item in self.items
        ]

        try:
            purchase_id = create_purchase(
                purchase_date=self.date_input.date().toString("yyyy-MM-dd"),
                items=purchase_items,
                supplier_id=self.supplier_combo.currentData(),
                invoice_number=self.invoice_input.text().strip() or None,
                freight_cents=freight_cents,
                discount_cents=discount_cents,
                notes=self.notes_input.toPlainText().strip() or None,
            )
        except ValueError as error:
            QMessageBox.warning(
                self,
                "Não foi possível registrar a compra",
                str(error),
            )
            return

        QMessageBox.information(
            self,
            "Compra registrada",
            f"Compra nº {purchase_id} registrada com sucesso!",
        )
        self.accept()