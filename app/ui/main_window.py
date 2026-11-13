
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.ui.pages.dashboard_page import DashboardPage
from app.ui.pages.categories_page import CategoriesPage
from app.ui.pages.materials_page import MaterialsPage
from app.ui.pages.products_page import ProductsPage
from app.ui.pages.productions_page import ProductionsPage
from app.ui.pages.purchases_page import PurchasesPage
from app.ui.pages.recipes_page import RecipesPage
from app.ui.pages.sales_page import SalesPage
from app.ui.pages.suppliers_page import SuppliersPage
from app.ui.pages.reports_page import ReportsPage

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("MAZURON ERP")
        self.resize(1200, 750)
        self.setMinimumSize(950, 600)

        self.menu_buttons = {}

        self._create_interface()

    def _create_interface(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        sidebar = self._create_sidebar()
        main_layout.addWidget(sidebar)

        self.pages = QStackedWidget()
        self.pages.addWidget(DashboardPage())
        self.pages.addWidget(ProductsPage())
        self.pages.addWidget(MaterialsPage())
        self.pages.addWidget(PurchasesPage())
        self.pages.addWidget(RecipesPage())
        self.pages.addWidget(ProductionsPage())
        self.pages.addWidget(SalesPage())
        self.pages.addWidget(CategoriesPage())
        self.pages.addWidget(SuppliersPage())
        self.pages.addWidget(ReportsPage())

        main_layout.addWidget(self.pages)

        self._navigate_to(0)

    def _create_sidebar(self):
        sidebar = QFrame()
        sidebar.setFixedWidth(245)
        sidebar.setObjectName("sidebar")

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(20, 28, 20, 20)
        layout.setSpacing(9)

        # Identidade da marca
        brand_layout = QHBoxLayout()
        brand_layout.setSpacing(12)

        brand_mark = QLabel("M")
        brand_mark.setObjectName("brand_mark")
        brand_mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_layout.addWidget(brand_mark)

        brand_text_layout = QVBoxLayout()
        brand_text_layout.setSpacing(0)

        brand_name = QLabel("MAZURON")
        brand_name.setObjectName("brand_name")
        brand_text_layout.addWidget(brand_name)

        brand_erp = QLabel("E R P")
        brand_erp.setObjectName("brand_erp")
        brand_text_layout.addWidget(brand_erp)

        brand_layout.addLayout(brand_text_layout)
        brand_layout.addStretch()

        layout.addLayout(brand_layout)

        tagline = QLabel("Mais controle para o seu negócio.")
        tagline.setObjectName("brand_tagline")
        tagline.setWordWrap(True)
        layout.addWidget(tagline)

        layout.addSpacing(28)

        menu_items = [
            ("Visão geral", 0),
            ("Produtos", 1),
            ("Materiais", 2),
            ("Compras", 3),
            ("Receitas", 4),
            ("Produção", 5),
            ("Vendas", 6),
            ("Categorias", 7),
            ("Fornecedores", 8),
            ("Relatórios", 9),
        ]

        for item, page_index in menu_items:
            button = QPushButton(item)
            button.setObjectName("menu_button")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setCheckable(True)

            if page_index is not None:
                self.menu_buttons[page_index] = button
                button.clicked.connect(
                    lambda checked=False, index=page_index:
                    self._navigate_to(index)
                )

            layout.addWidget(button)

        layout.addStretch()

        footer = QLabel("MAZURON ERP  •  Gestão inteligente")
        footer.setObjectName("sidebar_footer")
        layout.addWidget(footer)

        return sidebar

    def _navigate_to(self, index):
        self.pages.setCurrentIndex(index)

        page = self.pages.widget(index)
        refresh = getattr(page, "refresh_data", None)
        if callable(refresh):
            refresh()

        for page_index, button in self.menu_buttons.items():
            button.setChecked(page_index == index)
