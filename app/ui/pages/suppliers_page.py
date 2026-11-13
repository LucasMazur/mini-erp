from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QTableWidget, QTableWidgetItem,
    QTextEdit, QVBoxLayout, QWidget,
)

from app.services.supplier_service import (
    create_supplier, deactivate_supplier, list_suppliers, update_supplier,
)


class SupplierForm(QDialog):
    def __init__(self, parent=None, supplier=None):
        super().__init__(parent)
        self.supplier = supplier
        self.setWindowTitle("Editar fornecedor" if supplier else "Novo fornecedor")
        self.setMinimumWidth(520)
        self.resize(560, 620)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 24, 26, 24)
        layout.setSpacing(14)

        title = QLabel("Editar fornecedor" if supplier else "Cadastrar fornecedor")
        title.setObjectName("page_title")
        layout.addWidget(title)

        subtitle = QLabel(
            "Mantenha os dados de contato e identificação dos seus fornecedores."
        )
        subtitle.setObjectName("page_subtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        form = QFormLayout()
        form.setVerticalSpacing(12)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Nome ou razão social")
        form.addRow("Nome / Razão social *", self.name_input)

        self.document_input = QLineEdit()
        self.document_input.setPlaceholderText("CPF ou CNPJ (opcional)")
        form.addRow("CPF / CNPJ", self.document_input)

        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("(00) 00000-0000")
        form.addRow("Telefone", self.phone_input)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("contato@empresa.com")
        form.addRow("E-mail", self.email_input)

        self.address_input = QLineEdit()
        self.address_input.setPlaceholderText("Rua, número, bairro, cidade/UF")
        form.addRow("Endereço", self.address_input)

        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Condições comerciais, contatos ou observações...")
        self.notes_input.setMaximumHeight(105)
        form.addRow("Observações", self.notes_input)

        layout.addLayout(form)
        layout.addStretch()

        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel = QPushButton("Cancelar")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(cancel)

        save = QPushButton("Salvar fornecedor")
        save.setObjectName("primary_button")
        save.clicked.connect(self._save)
        buttons.addWidget(save)
        layout.addLayout(buttons)

        if supplier:
            self.name_input.setText(supplier["name"] or "")
            self.document_input.setText(supplier["document"] or "")
            self.phone_input.setText(supplier["phone"] or "")
            self.email_input.setText(supplier["email"] or "")
            self.address_input.setText(supplier["address"] or "")
            self.notes_input.setPlainText(supplier["notes"] or "")

    def _save(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(
                self, "Campo obrigatório", "Informe o nome ou razão social."
            )
            self.name_input.setFocus()
            return

        values = {
            "name": name,
            "document": self.document_input.text().strip() or None,
            "phone": self.phone_input.text().strip() or None,
            "email": self.email_input.text().strip() or None,
            "address": self.address_input.text().strip() or None,
            "notes": self.notes_input.toPlainText().strip() or None,
        }
        try:
            if self.supplier:
                update_supplier(self.supplier["id"], **values)
            else:
                create_supplier(**values)
        except ValueError as error:
            QMessageBox.warning(self, "Não foi possível salvar", str(error))
            return
        self.accept()


class SuppliersPage(QWidget):
    def __init__(self):
        super().__init__()
        self.rows = []
        self._create_interface()
        self.refresh_data()

    def _create_interface(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(35, 30, 35, 30)
        layout.setSpacing(16)

        title = QLabel("Fornecedores")
        title.setObjectName("page_title")
        layout.addWidget(title)

        subtitle = QLabel(
            "Cadastre e mantenha organizados os dados dos fornecedores utilizados nas compras."
        )
        subtitle.setObjectName("page_subtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        toolbar = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar por nome ou CPF/CNPJ...")
        self.search_input.textChanged.connect(self.refresh_data)
        toolbar.addWidget(self.search_input, 1)

        self.show_inactive = QPushButton("Mostrar inativos")
        self.show_inactive.setCheckable(True)
        self.show_inactive.toggled.connect(self.refresh_data)
        toolbar.addWidget(self.show_inactive)

        new_button = QPushButton("+ Novo fornecedor")
        new_button.setObjectName("primary_button")
        new_button.clicked.connect(self._new_supplier)
        toolbar.addWidget(new_button)
        layout.addLayout(toolbar)

        actions = QHBoxLayout()
        self.edit_button = QPushButton("Editar selecionado")
        self.edit_button.setEnabled(False)
        self.edit_button.clicked.connect(self._edit_supplier)
        actions.addWidget(self.edit_button)

        self.deactivate_button = QPushButton("Desativar selecionado")
        self.deactivate_button.setEnabled(False)
        self.deactivate_button.clicked.connect(self._deactivate_supplier)
        actions.addWidget(self.deactivate_button)
        actions.addStretch()
        layout.addLayout(actions)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Fornecedor", "CPF / CNPJ", "Telefone", "E-mail", "Situação"
        ])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, header.ResizeMode.Stretch)
        header.setSectionResizeMode(1, header.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, header.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, header.ResizeMode.Stretch)
        header.setSectionResizeMode(4, header.ResizeMode.ResizeToContents)
        self.table.itemSelectionChanged.connect(self._update_actions)
        self.table.cellDoubleClicked.connect(lambda row, col: self._edit_supplier())
        layout.addWidget(self.table)

    def refresh_data(self, *_):
        self.rows = list_suppliers(
            search=self.search_input.text(),
            include_inactive=self.show_inactive.isChecked(),
        )
        self.table.setRowCount(len(self.rows))
        for row, supplier in enumerate(self.rows):
            values = [
                supplier["name"],
                supplier["document"] or "—",
                supplier["phone"] or "—",
                supplier["email"] or "—",
                "Ativo" if supplier["active"] else "Inativo",
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if column == 0:
                    item.setData(Qt.ItemDataRole.UserRole, supplier["id"])
                self.table.setItem(row, column, item)
        self._update_actions()

    def _selected_supplier(self):
        row = self.table.currentRow()
        return self.rows[row] if 0 <= row < len(self.rows) else None

    def _update_actions(self):
        supplier = self._selected_supplier()
        self.edit_button.setEnabled(supplier is not None)
        self.deactivate_button.setEnabled(
            supplier is not None and bool(supplier["active"])
        )

    def _new_supplier(self):
        if SupplierForm(self).exec():
            self.refresh_data()

    def _edit_supplier(self):
        supplier = self._selected_supplier()
        if supplier and SupplierForm(self, supplier).exec():
            self.refresh_data()

    def _deactivate_supplier(self):
        supplier = self._selected_supplier()
        if not supplier:
            return
        answer = QMessageBox.question(
            self,
            "Desativar fornecedor",
            f"Deseja desativar '{supplier['name']}'?\n\n"
            "O fornecedor continuará no histórico das compras, mas não poderá "
            "ser selecionado em novas compras.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            deactivate_supplier(supplier["id"])
        except ValueError as error:
            QMessageBox.warning(self, "Não foi possível desativar", str(error))
            return
        self.refresh_data()
