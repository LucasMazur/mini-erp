
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
from app.ui.pages.products_page import ProductsPage


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Mini ERP")
        self.resize(1200, 750)
        self.setMinimumSize(950, 600)

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

        main_layout.addWidget(self.pages)

    def _create_sidebar(self):
        sidebar = QFrame()
        sidebar.setFixedWidth(230)
        sidebar.setObjectName("sidebar")

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(18, 24, 18, 20)
        layout.setSpacing(10)

        logo = QLabel("MINI ERP")
        logo.setObjectName("logo")
        layout.addWidget(logo)

        subtitle = QLabel("Gestão do seu negócio")
        subtitle.setObjectName("sidebar_subtitle")
        layout.addWidget(subtitle)

        layout.addSpacing(30)

        menu_items = [
            "Visão geral",
            "Produtos",
            "Materiais",
            "Receitas",
            "Produção",
            "Vendas",
            "Financeiro",
            "Fornecedores",
            "Relatórios",
        ]

        for index, item in enumerate(menu_items):
            button = QPushButton(item)
            button.setObjectName("menu_button")
            button.setCursor(Qt.CursorShape.PointingHandCursor)

            if item == "Visão geral":
                button.clicked.connect(
                    lambda checked=False: self.pages.setCurrentIndex(0)
                )

            elif item == "Produtos":
                button.clicked.connect(
                    lambda checked=False: self.pages.setCurrentIndex(1)
                )

            layout.addWidget(button)

        return sidebar
