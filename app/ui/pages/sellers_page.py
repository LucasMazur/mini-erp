from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QDialog, QDoubleSpinBox, QFormLayout, QHBoxLayout,
    QInputDialog, QLabel, QLineEdit, QMessageBox, QPushButton,
    QSpinBox, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from app.database.connection import get_connection
from app.services.consignment_service import (
    close_consignment, create_consignment, create_seller, get_consignment,
    list_consignments, list_sellers, register_payment, register_return,
    register_settlement, update_seller,
)


def currency(cents):
    return f"R$ {cents / 100:,.2f}".replace(",", "X").replace(
        ".", ","
    ).replace("X", ".")


class SellerForm(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nova loja parceira")
        self.setMinimumWidth(440)
        layout = QVBoxLayout(self)
        title = QLabel("Cadastrar loja parceira")
        title.setObjectName("page_title")
        layout.addWidget(title)
        form = QFormLayout()
        self.name = QLineEdit()
        self.contact = QLineEdit()
        self.phone = QLineEdit()
        self.address = QLineEdit()
        self.commission_type = QComboBox()
        self.commission_type.addItem("Percentual (%)", "percentage")
        self.commission_type.addItem("Valor fixo por peça", "fixed")
        self.commission = QDoubleSpinBox()
        self.commission.setMaximum(1000000)
        self.commission.setDecimals(2)
        self.commission.setSuffix(" %" )
        self.commission_type.currentIndexChanged.connect(self._commission_changed)
        form.addRow("Nome da loja *", self.name)
        form.addRow("Responsável", self.contact)
        form.addRow("Telefone", self.phone)
        form.addRow("Endereço", self.address)
        form.addRow("Tipo de comissão", self.commission_type)
        form.addRow("Comissão", self.commission)
        layout.addLayout(form)
        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel = QPushButton("Cancelar")
        cancel.clicked.connect(self.reject)
        save = QPushButton("Cadastrar loja")
        save.setObjectName("primary_button")
        save.clicked.connect(self._save)
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        layout.addLayout(buttons)

    def _commission_changed(self):
        fixed = self.commission_type.currentData() == "fixed"
        self.commission.setSuffix(" R$" if fixed else " %")
        self.commission.setMaximum(1000000 if fixed else 100)

    def _save(self):
        name = self.name.text().strip()
        if not name:
            QMessageBox.warning(self, "Campo obrigatório", "Informe o nome da loja.")
            return
        value = round(self.commission.value() * 100) if (
            self.commission_type.currentData() == "fixed"
        ) else round(self.commission.value() * 100)
        try:
            create_seller(
                name, self.commission_type.currentData(), value,
                self.contact.text(), self.phone.text(), self.address.text(),
            )
        except ValueError as error:
            QMessageBox.warning(self, "Não foi possível cadastrar", str(error))
            return
        self.accept()


class ConsignmentForm(QDialog):
    def __init__(self, seller_id, parent=None):
        super().__init__(parent)
        self.seller_id = seller_id
        self.items = []
        self.setWindowTitle("Nova remessa em consignação")
        self.resize(620, 480)
        layout = QVBoxLayout(self)
        title = QLabel("Nova remessa em consignação")
        title.setObjectName("page_title")
        layout.addWidget(title)
        self.product = QComboBox()
        with get_connection() as connection:
            products = connection.execute(
                """
                SELECT p.id, p.name, p.sale_price_cents, u.symbol
                FROM products p JOIN units u ON u.id = p.stock_unit_id
                WHERE p.active = 1 ORDER BY p.name
                """
            ).fetchall()
        for product in products:
            self.product.addItem(
                f"{product['name']} — {currency(product['sale_price_cents'] or 0)}",
                dict(product),
            )
        row = QHBoxLayout()
        row.addWidget(self.product, 1)
        self.quantity = QSpinBox()
        self.quantity.setRange(1, 100000)
        row.addWidget(self.quantity)
        add = QPushButton("Adicionar")
        add.clicked.connect(self._add_item)
        row.addWidget(add)
        layout.addLayout(row)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Produto", "Quantidade", "Preço unitário"])
        self.table.horizontalHeader().setSectionResizeMode(0, self.table.horizontalHeader().ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)
        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel = QPushButton("Cancelar")
        cancel.clicked.connect(self.reject)
        save = QPushButton("Registrar remessa")
        save.setObjectName("primary_button")
        save.clicked.connect(self._save)
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        layout.addLayout(buttons)

    def _add_item(self):
        product = self.product.currentData()
        if not product:
            return
        if product["sale_price_cents"] is None:
            QMessageBox.warning(
                self, "Preço não cadastrado",
                "Cadastre o preço de venda do produto antes da remessa.",
            )
            return
        product_id = product["id"]
        if any(item["product_id"] == product_id for item in self.items):
            QMessageBox.warning(self, "Produto repetido", "Esse produto já foi adicionado.")
            return
        quantity = self.quantity.value()
        self.items.append({"product_id": product_id, "quantity": quantity})
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(product["name"]))
        self.table.setItem(row, 1, QTableWidgetItem(str(quantity)))
        self.table.setItem(row, 2, QTableWidgetItem(currency(product["sale_price_cents"])))
        
    def _save(self):
        if not self.items:
            QMessageBox.warning(self, "Remessa vazia", "Adicione pelo menos um produto.")
            return
        try:
            create_consignment(self.seller_id, date.today().isoformat(), self.items)
        except ValueError as error:
            QMessageBox.warning(self, "Não foi possível registrar", str(error))
            return
        self.accept()


class ConsignmentDetailsDialog(QDialog):
    def __init__(self, consignment_id, parent=None):
        super().__init__(parent)
        self.consignment_id = consignment_id
        self.setWindowTitle("Detalhes da consignação")
        self.resize(850, 560)
        layout = QVBoxLayout(self)
        self.heading = QLabel()
        self.heading.setObjectName("page_title")
        layout.addWidget(self.heading)
        self.summary = QLabel()
        self.summary.setObjectName("page_subtitle")
        layout.addWidget(self.summary)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels([
            "Produto", "Entregue", "Vendido", "Devolvido", "Na loja"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, self.table.horizontalHeader().ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)
        actions = QHBoxLayout()
        for label, callback in [
            ("Registrar acerto", self._settle),
            ("Registrar devolução", self._return),
            ("Registrar repasse", self._pay),
            ("Encerrar remessa", self._close),
        ]:
            button = QPushButton(label)
            button.clicked.connect(callback)
            actions.addWidget(button)
        layout.addLayout(actions)
        close = QPushButton("Fechar")
        close.clicked.connect(self.accept)
        layout.addWidget(close)
        self.refresh_data()

    def refresh_data(self):
        self.data = get_consignment(self.consignment_id)
        if not self.data:
            self.reject()
            return
        self.heading.setText(
            f"Remessa #{self.data['id']} — {self.data['seller_name']}"
        )
        self.summary.setText(
            f"Valor pendente de repasse: {self.data['pending_cents'] / 100:,.2f} "
            f"a repassar".replace(",", "X").replace(".", ",").replace("X", ".")
        )
        self.table.setRowCount(len(self.data["items"]))
        for row, item in enumerate(self.data["items"]):
            values = [
                item["product_name_snapshot"],
                str(item["delivered_quantity_milli"] // 1000),
                str(item["sold_quantity_milli"] // 1000),
                str(item["returned_quantity_milli"] // 1000),
                str(item["custody_quantity_milli"] // 1000),
            ]
            for col, value in enumerate(values):
                cell = QTableWidgetItem(value)
                if col == 0:
                    cell.setData(Qt.ItemDataRole.UserRole, item["id"])
                self.table.setItem(row, col, cell)

    def _selected_item(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Selecione um produto", "Selecione um produto na tabela.")
            return None
        return self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)

    def _quantity(self, title, prompt, maximum):
        value, ok = QInputDialog.getInt(self, title, prompt, 1, 1, maximum)
        return value if ok else None

    def _settle(self):
        item_id = self._selected_item()
        if item_id is None:
            return
        item = next(i for i in self.data["items"] if i["id"] == item_id)
        available = item["custody_quantity_milli"] // 1000
        if available <= 0:
            QMessageBox.information(self, "Sem saldo", "Não há unidades desse produto disponíveis na loja.")
            return
        quantity = self._quantity("Acerto de vendas", "Quantidade vendida:", available)
        if quantity is None:
            return
        try:
            register_settlement(
                self.consignment_id, date.today().isoformat(),
                [{"consignment_item_id": item_id, "quantity": quantity}],
            )
        except ValueError as error:
            QMessageBox.warning(self, "Acerto não registrado", str(error))
        self.refresh_data()

    def _return(self):
        item_id = self._selected_item()
        if item_id is None:
            return
        item = next(i for i in self.data["items"] if i["id"] == item_id)
        available = item["custody_quantity_milli"] // 1000
        if available <= 0:
            QMessageBox.information(self, "Sem saldo", "Não há unidades para devolver.")
            return
        quantity = self._quantity("Devolução", "Quantidade devolvida:", available)
        if quantity is None:
            return
        try:
            register_return(
                self.consignment_id, item_id, date.today().isoformat(), quantity
            )
        except ValueError as error:
            QMessageBox.warning(self, "Devolução não registrada", str(error))
        self.refresh_data()

    def _pay(self):
        pending = self.data["pending_cents"]
        if pending <= 0:
            QMessageBox.information(self, "Sem pendências", "Não há valores pendentes de repasse.")
            return
        value, ok = QInputDialog.getDouble(
            self, "Registrar repasse", "Valor recebido (R$):",
            pending / 100, 0.01, pending / 100, 2,
        )
        if not ok:
            return
        try:
            register_payment(
                self.consignment_id, date.today().isoformat(),
                round(value * 100), "Outro",
            )
        except ValueError as error:
            QMessageBox.warning(self, "Repasse não registrado", str(error))
        self.refresh_data()

    def _close(self):
        try:
            close_consignment(self.consignment_id)
        except ValueError as error:
            QMessageBox.warning(self, "Não foi possível encerrar", str(error))
            return
        QMessageBox.information(self, "Remessa encerrada", "A remessa foi encerrada.")
        self.accept()


class SellersPage(QWidget):
    def __init__(self):
        super().__init__()
        self.rows = []
        self._create_interface()
        self.refresh_data()

    def _create_interface(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(35, 30, 35, 30)
        layout.setSpacing(16)
        title = QLabel("Vendedores / Lojas parceiras")
        title.setObjectName("page_title")
        layout.addWidget(title)
        subtitle = QLabel(
            "Controle produtos consignados, vendas, comissões, devoluções e repasses."
        )
        subtitle.setObjectName("page_subtitle")
        layout.addWidget(subtitle)
        toolbar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Buscar loja...")
        self.search.textChanged.connect(self.refresh_data)
        toolbar.addWidget(self.search, 1)
        new = QPushButton("+ Nova loja")
        new.setObjectName("primary_button")
        new.clicked.connect(self._new_seller)
        toolbar.addWidget(new)
        layout.addLayout(toolbar)
        actions = QHBoxLayout()
        self.dispatch = QPushButton("Nova remessa")
        self.dispatch.setObjectName("primary_button")
        self.dispatch.clicked.connect(self._new_consignment)
        self.details = QPushButton("Ver remessas / acertos")
        self.details.clicked.connect(self._open_consignments)
        self.edit = QPushButton("Editar comissão")
        self.edit.clicked.connect(self._edit_commission)
        for button in (self.dispatch, self.details, self.edit):
            button.setEnabled(False)
            actions.addWidget(button)
        actions.addStretch()
        layout.addLayout(actions)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels([
            "Loja parceira", "Comissão", "Produtos na loja", "A receber", "Situação"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, self.table.horizontalHeader().ResizeMode.Stretch)
        for col in range(1, 5):
            self.table.horizontalHeader().setSectionResizeMode(
                col, self.table.horizontalHeader().ResizeMode.ResizeToContents
            )
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self._update_actions)
        self.table.cellDoubleClicked.connect(lambda row, col: self._open_consignments())
        layout.addWidget(self.table)

