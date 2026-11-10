from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.ui.pages.purchase_form import PurchaseForm


class PurchasesPage(QWidget):
    def __init__(self):
        super().__init__()

        self._create_interface()

    def _create_interface(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)

        title = QLabel("Compras")
        title.setObjectName("page_title")
        layout.addWidget(title)

        subtitle = QLabel(
            "Registre compras de materiais e acompanhe suas entradas."
        )
        subtitle.setObjectName("page_subtitle")
        layout.addWidget(subtitle)

        actions_layout = QHBoxLayout()
        actions_layout.addStretch()

        new_purchase_button = QPushButton("＋ Nova compra")
        new_purchase_button.setObjectName("primary_button")
        new_purchase_button.clicked.connect(self._open_purchase_form)

        actions_layout.addWidget(new_purchase_button)
        layout.addLayout(actions_layout)

        layout.addStretch()

    def _open_purchase_form(self):
        dialog = PurchaseForm(self)
        dialog.exec()