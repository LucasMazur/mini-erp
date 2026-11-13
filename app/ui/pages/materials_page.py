from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
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

from app.services.material_service import (
    deactivate_material,
    get_material,
    list_materials,
)
from app.services.stock_service import get_stock_balance
from app.ui.pages.material_form import MaterialForm
from app.ui.pages.stock_history_dialog import StockHistoryDialog


class MaterialsPage(QWidget):
    def __init__(self):
        super().__init__()
        self._create_interface()
        self.load_materials()

    def _create_interface(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(35, 30, 35, 30)
        layout.setSpacing(18)

        title = QLabel("Materiais")
        title.setObjectName("page_title")
        layout.addWidget(title)

        subtitle = QLabel(
            "Cadastre e gerencie suas matérias-primas."
        )
        subtitle.setObjectName("page_subtitle")
        layout.addWidget(subtitle)

        toolbar = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "Pesquisar por nome ou código..."
        )
        self.search_input.textChanged.connect(self.load_materials)
        toolbar.addWidget(self.search_input)

        self.new_button = QPushButton("+ Novo material")
        self.new_button.setObjectName("primary_button")
        self.new_button.clicked.connect(self.open_new_material)
        toolbar.addWidget(self.new_button)

        layout.addLayout(toolbar)

        actions = QHBoxLayout()

        self.edit_button = QPushButton("Editar selecionado")
        self.edit_button.setEnabled(False)
        self.edit_button.clicked.connect(
            self.edit_selected_material
        )
        actions.addWidget(self.edit_button)

        self.deactivate_button = QPushButton(
            "Desativar selecionado"
        )
        self.history_button = QPushButton("Histórico de estoque")
        self.history_button.setEnabled(False)
        self.history_button.clicked.connect(
            self.open_stock_history
        )
        actions.addWidget(self.history_button)
        self.deactivate_button.setEnabled(False)
        self.deactivate_button.clicked.connect(
            self.deactivate_selected_material
        )
        actions.addWidget(self.deactivate_button)

        actions.addStretch()
        layout.addLayout(actions)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Código",
            "Material",
            "Unidade",
            "Estoque atual",
            "Estoque mínimo",
            "Situação",
        ])

        self.table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self.table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.table.setSelectionMode(
            QTableWidget.SelectionMode.SingleSelection
        )
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()

        header.setSectionResizeMode(
            0, header.ResizeMode.ResizeToContents
        )
        header.setSectionResizeMode(
            1, header.ResizeMode.Stretch
        )
        header.setSectionResizeMode(
            2, header.ResizeMode.ResizeToContents
        )
        header.setSectionResizeMode(
            3, header.ResizeMode.ResizeToContents
        )
        header.setSectionResizeMode(
            4, header.ResizeMode.ResizeToContents
        )
        header.setSectionResizeMode(
            5, header.ResizeMode.ResizeToContents
        )

        self.table.itemSelectionChanged.connect(
            self._update_action_buttons
        )
        self.table.cellDoubleClicked.connect(
            lambda row, column: self.open_stock_history()
        )

        layout.addWidget(self.table)

    
    def load_materials(self):
        materials = list_materials(
            search=self.search_input.text()
        )

        self.table.setRowCount(len(materials))

        for row, material in enumerate(materials):
            material_id = material["id"]

            current_stock = get_stock_balance(
                "material",
                material_id,
            )

            minimum_stock = material["minimum_stock_quantity_milli"]

            if current_stock <= 0:
                status = "Sem estoque"
                status_color = "#FDE8E8"
                text_color = "#B42318"

            elif minimum_stock > 0 and current_stock < minimum_stock:
                status = "Abaixo do mínimo"
                status_color = "#FFF1DB"
                text_color = "#A15C00"

            else:
                status = "Normal"
                status_color = "#E5F5EC"
                text_color = "#187443"

            values = [
                material["code"] or "-",
                material["name"],
                material["unit_symbol"],
                self._format_quantity(current_stock),
                self._format_quantity(minimum_stock),
                status,
            ]

            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))

                if column == 0:
                    item.setData(
                        Qt.ItemDataRole.UserRole,
                        material_id,
                    )

                if column in (3, 4):
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight
                        | Qt.AlignmentFlag.AlignVCenter
                    )

                if column == 5:
                    from PySide6.QtGui import QBrush, QColor

                    item.setBackground(QBrush(QColor(status_color)))
                    item.setForeground(QBrush(QColor(text_color)))
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignCenter
                        | Qt.AlignmentFlag.AlignVCenter
                    )

                self.table.setItem(row, column, item)

        self._update_action_buttons()

    def _get_selected_material_id(self):
        row = self.table.currentRow()

        if row < 0:
            return None

        item = self.table.item(row, 0)

        if item is None:
            return None

        return item.data(Qt.ItemDataRole.UserRole)

    def _update_action_buttons(self):
        selected = self._get_selected_material_id() is not None

        self.edit_button.setEnabled(selected)
        self.deactivate_button.setEnabled(selected)
        self.history_button.setEnabled(selected)

    def open_new_material(self):
        dialog = MaterialForm(self)

        if dialog.exec():
            self.load_materials()

    def edit_selected_material(self):
        material_id = self._get_selected_material_id()

        if material_id is None:
            return

        material = get_material(material_id)

        if material is None:
            QMessageBox.warning(
                self,
                "Material não encontrado",
                "Não foi possível localizar o material.",
            )
            self.load_materials()
            return

        dialog = MaterialForm(self, material=material)

        if dialog.exec():
            self.load_materials()

    def deactivate_selected_material(self):
        material_id = self._get_selected_material_id()

        if material_id is None:
            return

        material = get_material(material_id)

        if material is None:
            QMessageBox.warning(
                self,
                "Material não encontrado",
                "Não foi possível localizar o material.",
            )
            self.load_materials()
            return

        confirmation = QMessageBox.question(
            self,
            "Confirmar desativação",
            (
                f"Deseja realmente desativar o material "
                f"'{material['name']}'?\n\n"
                "O histórico será preservado."
            ),
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if confirmation != QMessageBox.StandardButton.Yes:
            return

        try:
            deactivate_material(material_id)

            QMessageBox.information(
                self,
                "Sucesso",
                "Material desativado com sucesso!",
            )

            self.load_materials()

        except ValueError as error:
            QMessageBox.critical(
                self,
                "Erro ao desativar",
                str(error),
            )

    @staticmethod
    def _format_quantity(quantity_milli):
        quantity = quantity_milli / 1_000_000
        return f"{quantity:,.6f}".replace(",", "X").replace(
            ".", ","
        ).replace("X", ".")

    def open_stock_history(self):
        material_id = self._get_selected_material_id()

        if material_id is None:
            return

        material = get_material(material_id)

        if material is None:
            QMessageBox.warning(
                self,
                "Material não encontrado",
                "Não foi possível localizar o material.",
            )
            self.load_materials()
            return

        dialog = StockHistoryDialog(material, item_type="material", parent=self)
        dialog.exec()