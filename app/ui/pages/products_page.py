
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

from app.services.product_service import (
    deactivate_product,
    get_product,
    list_products,
)
from app.ui.pages.product_form import ProductForm
from app.ui.pages.stock_history_dialog import StockHistoryDialog


class ProductsPage(QWidget):
    def __init__(self):
        super().__init__()
        self._create_interface()
        self.load_products()

    def _create_interface(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(35, 30, 35, 30)
        layout.setSpacing(18)

        title = QLabel("Produtos")
        title.setObjectName("page_title")
        layout.addWidget(title)

        subtitle = QLabel("Cadastre e gerencie seus produtos.")
        subtitle.setObjectName("page_subtitle")
        layout.addWidget(subtitle)

        toolbar = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "Pesquisar por nome ou código..."
        )
        self.search_input.textChanged.connect(self.load_products)

        toolbar.addWidget(self.search_input)

        self.new_button = QPushButton("+ Novo produto")
        self.new_button.setObjectName("primary_button")
        self.new_button.clicked.connect(self.open_new_product)
        toolbar.addWidget(self.new_button)

        layout.addLayout(toolbar)

        actions = QHBoxLayout()

        self.edit_button = QPushButton("Editar selecionado")
        self.edit_button.setEnabled(False)
        self.edit_button.clicked.connect(self.edit_selected_product)
        actions.addWidget(self.edit_button)

        self.deactivate_button = QPushButton("Desativar selecionado")
        self.deactivate_button.setEnabled(False)
        self.deactivate_button.clicked.connect(
            self.deactivate_selected_product
        )
        actions.addWidget(self.deactivate_button)

        self.history_button = QPushButton("Histórico de estoque")
        self.history_button.setEnabled(False)
        self.history_button.clicked.connect(self.open_stock_history)
        actions.addWidget(self.history_button)

        actions.addStretch()
        layout.addLayout(actions)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Código",
            "Produto",
            "Categoria",
            "Unidade",
            "Preço de venda",
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
        self.table.cellDoubleClicked.connect(
            lambda row, column: self.edit_selected_product()
        )

        layout.addWidget(self.table)

    def load_products(self):
        products = list_products(
            search=self.search_input.text()
        )

        self.table.setRowCount(len(products))

        for row, product in enumerate(products):
            price = product["sale_price_cents"]

            values = [
                product["code"] or "-",
                product["name"],
                product["category_name"] or "-",
                product["unit_symbol"],
                self._format_price(price),
            ]

            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))

                if column == 0:
                    item.setData(Qt.ItemDataRole.UserRole, product["id"])

                if column == 4:
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight
                        | Qt.AlignmentFlag.AlignVCenter
                    )

                self.table.setItem(row, column, item)

        self._update_action_buttons()

    def _get_selected_product_id(self):
        row = self.table.currentRow()

        if row < 0:
            return None

        item = self.table.item(row, 0)

        if item is None:
            return None

        return item.data(Qt.ItemDataRole.UserRole)

    def _update_action_buttons(self):
        selected = self._get_selected_product_id() is not None

        self.edit_button.setEnabled(selected)
        self.deactivate_button.setEnabled(selected)
        self.history_button.setEnabled(selected)

    def open_new_product(self):
        dialog = ProductForm(self)

        if dialog.exec():
            self.load_products()

    def edit_selected_product(self):
        product_id = self._get_selected_product_id()

        if product_id is None:
            return

        product = get_product(product_id)

        if product is None:
            QMessageBox.warning(
                self,
                "Produto não encontrado",
                "Não foi possível localizar o produto.",
            )
            self.load_products()
            return

        dialog = ProductForm(self, product=product)

        if dialog.exec():
            self.load_products()

    def open_stock_history(self):
        product_id = self._get_selected_product_id()

        if product_id is None:
            return

        product = get_product(product_id)

        if product is None:
            QMessageBox.warning(
                self,
                "Produto não encontrado",
                "Não foi possível localizar o produto.",
            )
            self.load_products()
            return

        dialog = StockHistoryDialog(
            product,
            item_type="product",
            parent=self,
        )
        dialog.exec()

    def deactivate_selected_product(self):
        product_id = self._get_selected_product_id()

        if product_id is None:
            return

        product = get_product(product_id)

        if product is None:
            QMessageBox.warning(
                self,
                "Produto não encontrado",
                "Não foi possível localizar o produto.",
            )
            self.load_products()
            return

        confirmation = QMessageBox.question(
            self,
            "Confirmar desativação",
            (
                f"Deseja realmente desativar o produto "
                f"'{product['name']}'?\n\n"
                "Ele deixará de aparecer na lista de produtos ativos."
            ),
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if confirmation != QMessageBox.StandardButton.Yes:
            return

        try:
            deactivate_product(product_id)

            QMessageBox.information(
                self,
                "Sucesso",
                "Produto desativado com sucesso!",
            )

            self.load_products()

        except ValueError as error:
            QMessageBox.critical(
                self,
                "Erro ao desativar",
                str(error),
            )

    @staticmethod
    def _format_price(price_cents):
        if price_cents is None:
            return "-"

        return (
            f"R$ {price_cents / 100:,.2f}"
            .replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )
