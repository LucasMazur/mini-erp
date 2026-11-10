
from PySide6.QtWidgets import (
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
from app.services.material_service import (
    create_material,
    update_material,
)


class MaterialForm(QDialog):
    def __init__(self, parent=None, material=None):
        super().__init__(parent)

        self.material = material

        if self.material:
            self.setWindowTitle("Editar material")
        else:
            self.setWindowTitle("Novo material")

        self.setMinimumWidth(450)

        self._create_interface()
        self._load_options()

        if self.material:
            self._fill_material_data()

    def _create_interface(self):
        layout = QVBoxLayout(self)

        if self.material:
            title_text = "Editar material"
        else:
            title_text = "Cadastrar material"

        title = QLabel(title_text)
        title.setObjectName("page_title")
        layout.addWidget(title)

        form = QFormLayout()

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Ex.: Filamento PLA")
        form.addRow("Nome *", self.name_input)

        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("Ex.: MAT001")
        form.addRow("Código", self.code_input)

        self.category_combo = QComboBox()
        form.addRow("Categoria", self.category_combo)

        self.unit_combo = QComboBox()
        form.addRow("Unidade de estoque *", self.unit_combo)

        self.minimum_stock_input = QDoubleSpinBox()
        self.minimum_stock_input.setDecimals(3)
        self.minimum_stock_input.setMinimum(0)
        self.minimum_stock_input.setMaximum(999999999)
        self.minimum_stock_input.setSingleStep(1)
        form.addRow("Estoque mínimo", self.minimum_stock_input)

        self.notes_input = QTextEdit()
        self.notes_input.setMaximumHeight(90)
        form.addRow("Observações", self.notes_input)

        layout.addLayout(form)

        buttons = QHBoxLayout()

        cancel_button = QPushButton("Cancelar")
        cancel_button.clicked.connect(self.reject)

        if self.material:
            save_text = "Salvar alterações"
        else:
            save_text = "Salvar material"

        save_button = QPushButton(save_text)
        save_button.setObjectName("primary_button")
        save_button.clicked.connect(self._save_material)

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
                WHERE kind = 'material' AND active = 1
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

    def _fill_material_data(self):
        self.name_input.setText(self.material["name"])
        self.code_input.setText(self.material["code"] or "")

        category_index = self.category_combo.findData(
            self.material["category_id"]
        )
        if category_index >= 0:
            self.category_combo.setCurrentIndex(category_index)

        unit_index = self.unit_combo.findData(
            self.material["stock_unit_id"]
        )
        if unit_index >= 0:
            self.unit_combo.setCurrentIndex(unit_index)

        minimum = self.material["minimum_stock_quantity_milli"]
        self.minimum_stock_input.setValue(minimum / 1000)

        self.notes_input.setPlainText(
            self.material["notes"] or ""
        )

    def _save_material(self):
        name = self.name_input.text().strip()

        if not name:
            QMessageBox.warning(
                self,
                "Campo obrigatório",
                "Informe o nome do material.",
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

        minimum_stock = round(
            self.minimum_stock_input.value() * 1000
        )

        try:
            if self.material:
                update_material(
                    material_id=self.material["id"],
                    name=name,
                    code=self.code_input.text(),
                    category_id=self.category_combo.currentData(),
                    stock_unit_id=self.unit_combo.currentData(),
                    minimum_stock_quantity_milli=minimum_stock,
                    notes=self.notes_input.toPlainText(),
                )

                message = "Material atualizado com sucesso!"

            else:
                create_material(
                    name=name,
                    code=self.code_input.text(),
                    category_id=self.category_combo.currentData(),
                    stock_unit_id=self.unit_combo.currentData(),
                    minimum_stock_quantity_milli=minimum_stock,
                    notes=self.notes_input.toPlainText(),
                )

                message = "Material cadastrado com sucesso!"

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
