
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QMessageBox,
    QVBoxLayout,
)

from app.services.material_service import list_materials
from app.services.recipe_service import (
    add_recipe_item,
    list_material_compatible_units,
)


class RecipeItemForm(QDialog):
    def __init__(self, recipe_id, parent=None):
        super().__init__(parent)

        self.recipe_id = recipe_id

        self.setWindowTitle("Adicionar material à receita")
        self.setMinimumWidth(420)

        self._create_interface()
        self._load_materials()

    def _create_interface(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.material_combo = QComboBox()
        self.material_combo.currentIndexChanged.connect(
            self._load_units
        )
        form.addRow("Material:", self.material_combo)

        self.quantity_input = QDoubleSpinBox()
        self.quantity_input.setDecimals(6)
        self.quantity_input.setMinimum(0.000001)
        self.quantity_input.setMaximum(999999999)
        self.quantity_input.setValue(1)
        form.addRow("Quantidade:", self.quantity_input)

        self.unit_combo = QComboBox()
        form.addRow("Unidade:", self.unit_combo)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )

        buttons.button(
            QDialogButtonBox.StandardButton.Save
        ).setText("Adicionar")

        buttons.button(
            QDialogButtonBox.StandardButton.Cancel
        ).setText("Cancelar")

        buttons.accepted.connect(self._save_item)
        buttons.rejected.connect(self.reject)

        layout.addWidget(buttons)

    def _load_materials(self):
        materials = list_materials()

        for material in materials:
            self.material_combo.addItem(
                material["name"],
                material["id"],
            )

        if not materials:
            self.material_combo.addItem(
                "Nenhum material cadastrado"
            )
            self.material_combo.setEnabled(False)
            self.unit_combo.setEnabled(False)

        else:
            self._load_units()

    def _load_units(self):
        material_id = self.material_combo.currentData()

        self.unit_combo.clear()

        if material_id is None:
            return

        units = list_material_compatible_units(material_id)

        for unit in units:
            self.unit_combo.addItem(
                f"{unit['name']} ({unit['symbol']})",
                unit["symbol"],
            )

    def _save_item(self):
        material_id = self.material_combo.currentData()
        unit_symbol = self.unit_combo.currentData()

        if material_id is None or unit_symbol is None:
            QMessageBox.warning(
                self,
                "Atenção",
                "Selecione um material e uma unidade.",
            )
            return

        try:
            add_recipe_item(
                recipe_id=self.recipe_id,
                material_id=material_id,
                quantity=str(self.quantity_input.value()),
                unit_symbol=unit_symbol,
            )

            QMessageBox.information(
                self,
                "Sucesso",
                "Material adicionado à receita!",
            )

            self.accept()

        except ValueError as error:
            QMessageBox.warning(
                self,
                "Não foi possível adicionar",
                str(error),
            )
