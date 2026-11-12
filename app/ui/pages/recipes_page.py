from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.services.recipe_service import list_all_recipes
from PySide6.QtCore import Qt

from app.ui.pages.recipe_form import RecipeForm

from app.ui.pages.recipe_details_dialog import RecipeDetailsDialog

class RecipesPage(QWidget):
    def __init__(self):
        super().__init__()
        self._create_interface()
        self.search_input.textChanged.connect(self.load_recipes)
        self.load_recipes()

    def _create_interface(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(35, 30, 35, 30)
        layout.setSpacing(18)

        title = QLabel("Receitas")
        title.setObjectName("page_title")
        layout.addWidget(title)

        subtitle = QLabel(
            "Gerencie as receitas e a composição dos seus produtos."
        )
        subtitle.setObjectName("page_subtitle")
        layout.addWidget(subtitle)

        toolbar = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "Pesquisar por produto ou nome da receita..."
        )
        toolbar.addWidget(self.search_input)

        self.new_button = QPushButton("+ Nova receita")
        self.new_button.setObjectName("primary_button")
        self.new_button.clicked.connect(self.open_new_recipe)
        toolbar.addWidget(self.new_button)

        layout.addLayout(toolbar)

        actions = QHBoxLayout()

        self.view_button = QPushButton("Visualizar selecionada")
        self.view_button.setEnabled(False)
        self.view_button.clicked.connect(self.view_selected_recipe)
        actions.addWidget(self.view_button)

        actions.addStretch()
        layout.addLayout(actions)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            "Produto",
            "Receita",
            "Versão atual",
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
        self.table.horizontalHeader().setStretchLastSection(True)

        self.table.itemSelectionChanged.connect(
            self._update_action_buttons
        )

        layout.addWidget(self.table)

    def _update_action_buttons(self):
        selected = self.table.currentRow() >= 0
        self.view_button.setEnabled(selected)

    def open_new_recipe(self):
        dialog = RecipeForm(self)

        if dialog.exec():
            self.load_recipes()

    def load_recipes(self):
        recipes = list_all_recipes(
            search=self.search_input.text()
        )

        self.table.setRowCount(len(recipes))

        for row, recipe in enumerate(recipes):
            version = recipe["version_number"]

            if version is None:
                version_text = "-"
                status = "Sem versão"

            else:
                version_text = str(version)

                status = (
                    "Finalizada"
                    if recipe["finalized_at"] is not None
                    else "Em edição"
                )

            values = [
                recipe["product_name"],
                recipe["name"],
                version_text,
                status,
            ]

            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))

                if column == 0:
                    item.setData(
                        Qt.ItemDataRole.UserRole,
                        recipe["id"],
                    )

                self.table.setItem(row, column, item)

        self._update_action_buttons()

    def view_selected_recipe(self):
        row = self.table.currentRow()

        if row < 0:
            return

        item = self.table.item(row, 0)

        if item is None:
            return

        recipe_id = item.data(Qt.ItemDataRole.UserRole)

        dialog = RecipeDetailsDialog(recipe_id, self)
        dialog.exec()
        self.load_recipes()