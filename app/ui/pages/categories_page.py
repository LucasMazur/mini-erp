from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.services.category_service import (
    create_category,
    deactivate_category,
    list_categories,
    update_category,
)


class CategoryForm(QDialog):
    def __init__(self, parent=None, category=None):
        super().__init__(parent)
        self.category = category
        self.setWindowTitle("Editar categoria" if category else "Nova categoria")
        self.setFixedWidth(460)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(14)

        title = QLabel("Editar categoria" if category else "Nova categoria")
        title.setObjectName("page_title")
        layout.addWidget(title)

        hint = QLabel(
            "Organize seus cadastros para facilitar filtros e consultas."
        )
        hint.setObjectName("page_subtitle")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        form = QFormLayout()
        form.setVerticalSpacing(12)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Ex.: Brincos, Colares, PLA...")
        form.addRow("Nome *", self.name_input)

        self.kind_combo = QComboBox()
        self.kind_combo.addItem("Produto", "product")
        self.kind_combo.addItem("Material", "material")
        form.addRow("Aplicar a *", self.kind_combo)
        layout.addLayout(form)

        if category:
            self.name_input.setText(category["name"])
            index = self.kind_combo.findData(category["kind"])
            self.kind_combo.setCurrentIndex(index)
            self.kind_combo.setEnabled(False)

        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel = QPushButton("Cancelar")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(cancel)

        save = QPushButton("Salvar categoria")
        save.setObjectName("primary_button")
        save.clicked.connect(self._save)
        buttons.addWidget(save)
        layout.addLayout(buttons)

    def _save(self):
        name = self.name_input.text().strip()
        try:
            if self.category:
                update_category(self.category["id"], name)
            else:
                create_category(name, self.kind_combo.currentData())
        except ValueError as error:
            QMessageBox.warning(self, "Não foi possível salvar", str(error))
            return
        self.accept()


class CategoriesPage(QWidget):
    def __init__(self):
        super().__init__()
        self._create_interface()
        self.load_categories()

    def _create_interface(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(35, 30, 35, 30)
        layout.setSpacing(18)

        title = QLabel("Categorias")
        title.setObjectName("page_title")
        layout.addWidget(title)

        subtitle = QLabel(
            "Organize produtos e materiais em grupos para facilitar a gestão."
        )
        subtitle.setObjectName("page_subtitle")
        layout.addWidget(subtitle)

        toolbar = QHBoxLayout()
        self.filter_combo = QComboBox()
        self.filter_combo.addItem("Todas as categorias", None)
        self.filter_combo.addItem("Somente produtos", "product")
        self.filter_combo.addItem("Somente materiais", "material")
        self.filter_combo.currentIndexChanged.connect(self.load_categories)
        toolbar.addWidget(self.filter_combo)

        toolbar.addStretch()
        new_button = QPushButton("+ Nova categoria")
        new_button.setObjectName("primary_button")
        new_button.clicked.connect(self.open_new_category)
        toolbar.addWidget(new_button)
        layout.addLayout(toolbar)

        actions = QHBoxLayout()
        self.edit_button = QPushButton("Editar selecionada")
        self.edit_button.setEnabled(False)
        self.edit_button.clicked.connect(self.edit_selected)
        actions.addWidget(self.edit_button)

        self.deactivate_button = QPushButton("Desativar selecionada")
        self.deactivate_button.setEnabled(False)
        self.deactivate_button.clicked.connect(self.deactivate_selected)
        actions.addWidget(self.deactivate_button)
        actions.addStretch()
        layout.addLayout(actions)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            "Categoria", "Aplicação", "Cadastros vinculados", "Status"
        ])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setColumnWidth(1, 150)
        self.table.setColumnWidth(2, 190)
        self.table.setColumnWidth(3, 120)
        self.table.itemSelectionChanged.connect(self._update_actions)
        self.table.cellDoubleClicked.connect(
            lambda row, column: self.edit_selected()
        )
        layout.addWidget(self.table)

        self.rows = []

    def load_categories(self):
        kind = self.filter_combo.currentData()
        self.rows = list_categories(kind=kind)
        self.table.setRowCount(len(self.rows))

        for row, category in enumerate(self.rows):
            values = [
                category["name"],
                category["kind_label"],
                str(category["linked_items"]),
                "Ativa" if category["active"] else "Inativa",
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setData(Qt.ItemDataRole.UserRole, category["id"])
                if column == 2:
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignCenter
                    )
                self.table.setItem(row, column, item)

        self._update_actions()

    def _selected_category(self):
        row = self.table.currentRow()
        return self.rows[row] if 0 <= row < len(self.rows) else None

    def _update_actions(self):
        selected = self._selected_category()
        self.edit_button.setEnabled(selected is not None)
        self.deactivate_button.setEnabled(
            selected is not None and bool(selected["active"])
        )

    def open_new_category(self):
        dialog = CategoryForm(self)
        if dialog.exec():
            self.load_categories()

    def edit_selected(self):
        category = self._selected_category()
        if category is None:
            return
        dialog = CategoryForm(self, category)
        if dialog.exec():
            self.load_categories()

    def deactivate_selected(self):
        category = self._selected_category()
        if category is None:
            return

        answer = QMessageBox.question(
            self,
            "Desativar categoria",
            f"Deseja desativar a categoria '{category['name']}'?\n\n"
            "Os produtos e materiais já vinculados serão preservados, "
            "mas a categoria não aparecerá em novos cadastros.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            deactivate_category(category["id"])
        except ValueError as error:
            QMessageBox.warning(self, "Não foi possível desativar", str(error))
            return
        self.load_categories()
