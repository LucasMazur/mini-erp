from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from app.services.financial_service import create_transaction
from app.services.sales_service import PAYMENT_METHODS


FINANCIAL_CATEGORIES = {
    "income": [
        "Venda de produtos",
        "Serviços",
        "Personalizados",
        "Outras receitas",
    ],
    "expense": [
        "Compra de materiais",
        "Embalagens",
        "Frete e transporte",
        "Marketing e divulgação",
        "Equipamentos e ferramentas",
        "Manutenção",
        "Taxas e tarifas",
        "Energia elétrica",
        "Outras despesas",
    ],
}


class FinancialTransactionDialog(QDialog):
    def __init__(self, direction, parent=None):
        super().__init__(parent)
        if direction not in {"income", "expense"}:
            raise ValueError("Tipo de lançamento inválido.")
        self.direction = direction
        self.setWindowTitle(
            "Nova receita" if direction == "income" else "Nova despesa"
        )
        self.setMinimumWidth(520)
        self._create_interface()

    def _create_interface(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 24, 25, 24)
        layout.setSpacing(15)

        title = QLabel(
            "Nova receita" if self.direction == "income" else "Nova despesa"
        )
        title.setObjectName("page_title")
        layout.addWidget(title)

        subtitle = QLabel("Preencha os dados do lançamento financeiro.")
        subtitle.setObjectName("page_subtitle")
        layout.addWidget(subtitle)

        form = QFormLayout()
        form.setVerticalSpacing(13)

        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDisplayFormat("dd/MM/yyyy")
        self.date_input.setDate(QDate.currentDate())
        form.addRow("Data *", self.date_input)

        self.description_input = QTextEdit()
        self.description_input.setFixedHeight(75)
        self.description_input.setPlaceholderText("Descreva o lançamento")
        form.addRow("Descrição *", self.description_input)

        self.category_combo = QComboBox()
        self.category_combo.addItems(FINANCIAL_CATEGORIES[self.direction])
        form.addRow("Categoria *", self.category_combo)

        self.amount_input = QDoubleSpinBox()
        self.amount_input.setDecimals(2)
        self.amount_input.setRange(0.01, 999999999.99)
        self.amount_input.setPrefix("R$ ")
        self.amount_input.setMinimumHeight(42)
        form.addRow("Valor *", self.amount_input)

        self.payment_combo = QComboBox()
        self.payment_combo.addItems(sorted(PAYMENT_METHODS))
        form.addRow("Forma de pagamento", self.payment_combo)

        layout.addLayout(form)

        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel_button = QPushButton("Cancelar")
        cancel_button.clicked.connect(self.reject)
        buttons.addWidget(cancel_button)

        save_button = QPushButton("Salvar lançamento")
        save_button.setObjectName("primary_button")
        save_button.clicked.connect(self._save)
        buttons.addWidget(save_button)
        layout.addLayout(buttons)

    def _save(self):
        description = self.description_input.toPlainText().strip()
        if not description:
            QMessageBox.warning(
                self, "Campo obrigatório", "Informe a descrição do lançamento."
            )
            self.description_input.setFocus()
            return

        try:
            create_transaction(
                transaction_date=self.date_input.date().toString("yyyy-MM-dd"),
                direction=self.direction,
                description=description,
                amount_cents=round(self.amount_input.value() * 100),
                category=self.category_combo.currentText(),
                payment_method=self.payment_combo.currentText(),
            )
        except (ValueError, RuntimeError) as error:
            QMessageBox.warning(
                self, "Não foi possível salvar", str(error)
            )
            return

        self.accept()
