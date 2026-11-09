
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)


class DashboardPage(QWidget):
    def __init__(self):
        super().__init__()

        self._create_interface()

    def _create_interface(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(35, 30, 35, 30)
        layout.setSpacing(20)

        title = QLabel("Visão geral")
        title.setObjectName("page_title")
        layout.addWidget(title)

        subtitle = QLabel(
            "Acompanhe os principais indicadores do seu negócio."
        )
        subtitle.setObjectName("page_subtitle")
        layout.addWidget(subtitle)

        cards_layout = QGridLayout()
        cards_layout.setSpacing(18)

        indicators = [
            ("Vendas do mês", "R$ 0,00"),
            ("Produtos em estoque", "0"),
            ("Produções realizadas", "0"),
            ("Resultado financeiro", "R$ 0,00"),
        ]

        for index, (name, value) in enumerate(indicators):
            card = self._create_card(name, value)
            cards_layout.addWidget(card, index // 2, index % 2)

        layout.addLayout(cards_layout)
        layout.addStretch()

    def _create_card(self, name, value):
        card = QFrame()
        card.setObjectName("dashboard_card")

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(22, 20, 22, 20)
        card_layout.setSpacing(12)

        name_label = QLabel(name)
        name_label.setObjectName("card_name")

        value_label = QLabel(value)
        value_label.setObjectName("card_value")

        card_layout.addWidget(name_label)
        card_layout.addWidget(value_label)

        return card
