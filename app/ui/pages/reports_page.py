from collections import defaultdict

from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.services.financial_service import (
    get_financial_summary,
    list_transactions,
)
from app.services.sales_service import get_sales_report
from app.services.purchase_service import list_purchases
from app.database.connection import get_connection
from app.ui.pages.financial_transaction_dialog import FinancialTransactionDialog


class ReportsPage(QWidget):
    def __init__(self):
        super().__init__()
        self._create_interface()
        self.refresh_data()

    @staticmethod
    def _currency(cents):
        return f"R$ {cents / 100:,.2f}".replace(",", "X").replace(
            ".", ","
        ).replace("X", ".")

    @staticmethod
    def _iso_date(date):
        return date.toString("yyyy-MM-dd")

    def _create_card(self, title):
        card = QFrame()
        card.setObjectName("dashboard_card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 15, 18, 15)
        card_layout.setSpacing(7)
        caption = QLabel(title)
        caption.setObjectName("card_name")
        card_layout.addWidget(caption)
        value = QLabel("0")
        value.setObjectName("card_value")
        card_layout.addWidget(value)
        return card, value

    def _create_table(self, headers, stretch_column=0):
        table = QTableWidget()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.verticalHeader().setVisible(False)
        header = table.horizontalHeader()
        for column in range(len(headers)):
            mode = (
                header.ResizeMode.Stretch
                if column == stretch_column
                else header.ResizeMode.ResizeToContents
            )
            header.setSectionResizeMode(column, mode)
        return table

    def _create_interface(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(35, 30, 35, 30)
        layout.setSpacing(15)

        title = QLabel("Relatórios")
        title.setObjectName("page_title")
        layout.addWidget(title)
        subtitle = QLabel(
            "Analise o desempenho financeiro e comercial do seu negócio."
        )
        subtitle.setObjectName("page_subtitle")
        layout.addWidget(subtitle)

        filters = QHBoxLayout()
        filters.setSpacing(10)
        today = QDate.currentDate()
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDisplayFormat("dd/MM/yyyy")
        self.start_date.setDate(today.addDays(1 - today.day()))
        filters.addWidget(QLabel("De"))
        filters.addWidget(self.start_date)

        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDisplayFormat("dd/MM/yyyy")
        self.end_date.setDate(today)
        filters.addWidget(QLabel("Até"))
        filters.addWidget(self.end_date)

        apply_button = QPushButton("Gerar relatório")
        apply_button.setObjectName("primary_button")
        apply_button.clicked.connect(self.refresh_data)
        filters.addWidget(apply_button)
        month_button = QPushButton("Este mês")
        month_button.clicked.connect(self._current_month)
        filters.addWidget(month_button)
        filters.addStretch()
        layout.addLayout(filters)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)
        self._create_financial_tab()
        self._create_sales_tab()
        self._create_purchases_tab()
        self._create_stock_tab()

    def _create_financial_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 12, 8, 8)
        layout.setSpacing(14)

        cards = QHBoxLayout()
        income_card, self.income_value = self._create_card("Total de receitas")
        expense_card, self.expense_value = self._create_card("Total de despesas")
        balance_card, self.balance_value = self._create_card("Resultado do período")
        cards.addWidget(income_card)
        cards.addWidget(expense_card)
        cards.addWidget(balance_card)
        layout.addLayout(cards)

        actions = QHBoxLayout()
        actions.addStretch()
        income_button = QPushButton("+ Nova receita")
        income_button.setObjectName("primary_button")
        income_button.clicked.connect(lambda: self._open_transaction("income"))
        actions.addWidget(income_button)
        expense_button = QPushButton("+ Nova despesa")
        expense_button.clicked.connect(lambda: self._open_transaction("expense"))
        actions.addWidget(expense_button)
        layout.addLayout(actions)

        transaction_filters = QHBoxLayout()
        transaction_filters.addWidget(QLabel("Exibir:"))
        self.direction_filter = QComboBox()
        self.direction_filter.addItem("Todas as movimentações", None)
        self.direction_filter.addItem("Receitas", "income")
        self.direction_filter.addItem("Despesas", "expense")
        self.direction_filter.currentIndexChanged.connect(self._refresh_transactions)
        transaction_filters.addWidget(self.direction_filter)
        transaction_filters.addStretch()
        layout.addLayout(transaction_filters)

        section = QLabel("Lançamentos financeiros")
        section.setObjectName("section_title")
        layout.addWidget(section)
        self.transactions_table = self._create_table(
            ["Data", "Descrição", "Categoria", "Tipo", "Forma de pagamento", "Valor"],
            stretch_column=1,
        )
        layout.addWidget(self.transactions_table, 1)

        category_section = QLabel("Resumo por categoria")
        category_section.setObjectName("section_title")
        layout.addWidget(category_section)
        self.category_table = self._create_table(
            ["Categoria", "Tipo", "Quantidade de lançamentos", "Valor total"]
        )
        layout.addWidget(self.category_table, 1)
        self.financial_status = QLabel("")
        self.financial_status.setObjectName("page_subtitle")
        layout.addWidget(self.financial_status)
        self.tabs.addTab(tab, "Financeiro")

    def _create_sales_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 12, 8, 8)
        layout.setSpacing(14)

        cards = QHBoxLayout()
        revenue_card, self.sales_revenue_value = self._create_card(
            "Faturamento líquido"
        )
        count_card, self.sales_count_value = self._create_card("Vendas realizadas")
        quantity_card, self.units_sold_value = self._create_card("Unidades vendidas")
        cards.addWidget(revenue_card)
        cards.addWidget(count_card)
        cards.addWidget(quantity_card)
        layout.addLayout(cards)

        product_title = QLabel("Produtos vendidos")
        product_title.setObjectName("section_title")
        layout.addWidget(product_title)
        self.products_table = self._create_table(
            ["Produto", "Quantidade vendida", "Valor bruto", "Vendas"],
            stretch_column=0,
        )
        layout.addWidget(self.products_table, 1)

        payment_title = QLabel("Vendas por forma de pagamento")
        payment_title.setObjectName("section_title")
        layout.addWidget(payment_title)
        self.payment_table = self._create_table(
            ["Forma de pagamento", "Quantidade de vendas", "Faturamento"],
            stretch_column=0,
        )
        layout.addWidget(self.payment_table, 1)
        self.sales_status = QLabel("")
        self.sales_status.setObjectName("page_subtitle")
        layout.addWidget(self.sales_status)
        self.tabs.addTab(tab, "Vendas")


    def _create_purchases_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 12, 8, 8)
        layout.setSpacing(14)

        cards = QHBoxLayout()
        total_card, self.purchase_total_value = self._create_card(
            "Total comprado"
        )
        count_card, self.purchase_count_value = self._create_card(
            "Compras realizadas"
        )
        suppliers_card, self.purchase_suppliers_value = self._create_card(
            "Fornecedores utilizados"
        )
        cards.addWidget(total_card)
        cards.addWidget(count_card)
        cards.addWidget(suppliers_card)
        layout.addLayout(cards)

        supplier_title = QLabel("Compras por fornecedor")
        supplier_title.setObjectName("section_title")
        layout.addWidget(supplier_title)
        self.purchase_supplier_table = self._create_table(
            ["Fornecedor", "Compras", "Valor total"], stretch_column=0
        )
        layout.addWidget(self.purchase_supplier_table, 1)

        material_title = QLabel("Materiais adquiridos")
        material_title.setObjectName("section_title")
        layout.addWidget(material_title)
        self.purchase_material_table = self._create_table(
            ["Material", "Quantidade adquirida", "Custo total"],
            stretch_column=0,
        )
        layout.addWidget(self.purchase_material_table, 1)

        self.purchase_status = QLabel("")
        self.purchase_status.setObjectName("page_subtitle")
        layout.addWidget(self.purchase_status)
        self.tabs.addTab(tab, "Compras")

    def _refresh_purchases(self, start_date, end_date):
        purchases = list_purchases(start_date=start_date, end_date=end_date)
        valid_purchases = [
            purchase for purchase in purchases if not purchase["is_reversed"]
        ]
        total_cents = sum(
            purchase["total_cost_cents"] for purchase in valid_purchases
        )
        supplier_totals = defaultdict(lambda: {"count": 0, "total": 0})
        valid_ids = []

        for purchase in valid_purchases:
            supplier = purchase["supplier_name"] or "Sem fornecedor"
            supplier_totals[supplier]["count"] += 1
            supplier_totals[supplier]["total"] += purchase["total_cost_cents"]
            valid_ids.append(purchase["id"])

        self.purchase_total_value.setText(self._currency(total_cents))
        self.purchase_count_value.setText(str(len(valid_purchases)))
        self.purchase_suppliers_value.setText(str(len(supplier_totals)))

        supplier_rows = sorted(
            supplier_totals.items(),
            key=lambda item: item[1]["total"],
            reverse=True,
        )
        self.purchase_supplier_table.setRowCount(len(supplier_rows))
        for row, (supplier, values) in enumerate(supplier_rows):
            cells = [
                supplier,
                str(values["count"]),
                self._currency(values["total"]),
            ]
            for column, value in enumerate(cells):
                item = QTableWidgetItem(value)
                if column > 0:
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    )
                self.purchase_supplier_table.setItem(row, column, item)

        material_totals = defaultdict(lambda: {"quantity": 0, "cost": 0})
        if valid_ids:
            placeholders = ",".join("?" for _ in valid_ids)
            with get_connection() as connection:
                rows = connection.execute(
                    f"""
                    SELECT material_name_snapshot AS name,
                           unit_symbol_snapshot AS unit,
                           SUM(quantity_milli) AS quantity,
                           SUM(landed_cost_cents) AS cost
                    FROM purchase_items
                    WHERE purchase_id IN ({placeholders})
                    GROUP BY material_name_snapshot, unit_symbol_snapshot
                    ORDER BY cost DESC, name
                    """,
                    valid_ids,
                ).fetchall()
            for item in rows:
                material_totals[(item["name"], item["unit"])] = {
                    "quantity": item["quantity"],
                    "cost": item["cost"],
                }

        material_rows = sorted(
            material_totals.items(),
            key=lambda item: item[1]["cost"],
            reverse=True,
        )
        self.purchase_material_table.setRowCount(len(material_rows))
        for row, ((name, unit), values) in enumerate(material_rows):
            quantity = f"{values['quantity'] / 1000:,.3f}".replace(
                ",", "X"
            ).replace(".", ",").replace("X", ".")
            cells = [
                name,
                f"{quantity} {unit}",
                self._currency(values["cost"]),
            ]
            for column, value in enumerate(cells):
                item = QTableWidgetItem(value)
                if column > 0:
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    )
                self.purchase_material_table.setItem(row, column, item)

        self.purchase_status.setText(
            f"{len(valid_purchases)} compra(s) considerada(s). "
            f"{len(purchases) - len(valid_purchases)} compra(s) estornada(s) "
            "foram desconsideradas."
        )

    def _create_stock_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 12, 8, 8)
        layout.setSpacing(14)

        note = QLabel(
            "Posição atual do estoque. Este painel não é limitado pelo período "
            "selecionado nos filtros acima."
        )
        note.setObjectName("page_subtitle")
        layout.addWidget(note)

        cards = QHBoxLayout()
        value_card, self.stock_value_label = self._create_card(
            "Valor total do estoque"
        )
        materials_card, self.stock_material_count_label = self._create_card(
            "Materiais cadastrados com saldo"
        )
        products_card, self.stock_product_count_label = self._create_card(
            "Produtos cadastrados com saldo"
        )
        alert_card, self.stock_alert_count_label = self._create_card(
            "Materiais no mínimo ou abaixo"
        )
        for card in (value_card, materials_card, products_card, alert_card):
            cards.addWidget(card)
        layout.addLayout(cards)

        materials_title = QLabel("Estoque de materiais")
        materials_title.setObjectName("section_title")
        layout.addWidget(materials_title)
        self.stock_materials_table = self._create_table(
            ["Material", "Saldo atual", "Estoque mínimo", "Valor em estoque", "Situação"],
            stretch_column=0,
        )
        layout.addWidget(self.stock_materials_table, 1)

        products_title = QLabel("Estoque de produtos")
        products_title.setObjectName("section_title")
        layout.addWidget(products_title)
        self.stock_products_table = self._create_table(
            ["Produto", "Saldo atual", "Valor em estoque"],
            stretch_column=0,
        )
        layout.addWidget(self.stock_products_table, 1)

        self.stock_status = QLabel("")
        self.stock_status.setObjectName("page_subtitle")
        layout.addWidget(self.stock_status)
        self.tabs.addTab(tab, "Estoque")

    @staticmethod
    def _format_quantity(quantity_milli, unit):
        quantity = f"{quantity_milli / 1000:,.3f}".replace(
            ",", "X"
        ).replace(".", ",").replace("X", ".")
        return f"{quantity} {unit}"

    def _refresh_stock(self):
        with get_connection() as connection:
            materials = connection.execute(
                """
                SELECT m.name, u.symbol AS unit,
                       COALESCE(SUM(sm.quantity_milli), 0) AS quantity,
                       COALESCE(SUM(sm.value_cents), 0) AS value,
                       m.minimum_stock_quantity_milli AS minimum
                FROM materials m
                JOIN units u ON u.id = m.stock_unit_id
                LEFT JOIN stock_movements sm ON sm.material_id = m.id
                WHERE m.active = 1
                GROUP BY m.id
                ORDER BY m.name COLLATE NOCASE
                """
            ).fetchall()
            products = connection.execute(
                """
                SELECT p.name, u.symbol AS unit,
                       COALESCE(SUM(sm.quantity_milli), 0) AS quantity,
                       COALESCE(SUM(sm.value_cents), 0) AS value
                FROM products p
                JOIN units u ON u.id = p.stock_unit_id
                LEFT JOIN stock_movements sm ON sm.product_id = p.id
                WHERE p.active = 1
                GROUP BY p.id
                ORDER BY p.name COLLATE NOCASE
                """
            ).fetchall()

        material_rows = [dict(row) for row in materials]
        product_rows = [dict(row) for row in products]
        materials_with_stock = [
            row for row in material_rows if row["quantity"] > 0
        ]
        products_with_stock = [
            row for row in product_rows if row["quantity"] > 0
        ]
        low_stock = [
            row for row in material_rows
            if row["minimum"] > 0 and row["quantity"] <= row["minimum"]
        ]
        total_value = sum(
            row["value"] for row in material_rows + product_rows
        )

        self.stock_value_label.setText(self._currency(total_value))
        self.stock_material_count_label.setText(str(len(materials_with_stock)))
        self.stock_product_count_label.setText(str(len(products_with_stock)))
        self.stock_alert_count_label.setText(str(len(low_stock)))

        self.stock_materials_table.setRowCount(len(material_rows))
        for row, material in enumerate(material_rows):
            minimum = material["minimum"]
            if minimum > 0 and material["quantity"] <= minimum:
                status = "Repor"
                status_color = QColor("#B42318")
            else:
                status = "Normal"
                status_color = QColor("#187443")
            values = [
                material["name"],
                self._format_quantity(material["quantity"], material["unit"]),
                self._format_quantity(minimum, material["unit"]),
                self._currency(material["value"]),
                status,
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 4:
                    item.setForeground(status_color)
                if column in (1, 2, 3):
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    )
                self.stock_materials_table.setItem(row, column, item)

        self.stock_products_table.setRowCount(len(product_rows))
        for row, product in enumerate(product_rows):
            values = [
                product["name"],
                self._format_quantity(product["quantity"], product["unit"]),
                self._currency(product["value"]),
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column in (1, 2):
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    )
                self.stock_products_table.setItem(row, column, item)

        self.stock_status.setText(
            f"{len(material_rows)} material(is) e {len(product_rows)} produto(s) "
            "ativo(s) analisados. O valor considera o custo registrado nos "
            "movimentos de estoque."
        )

    def _open_transaction(self, direction):
        dialog = FinancialTransactionDialog(direction, self)
        if dialog.exec():
            self.refresh_data()

    def _refresh_transactions(self):
        start_date = self._iso_date(self.start_date.date())
        end_date = self._iso_date(self.end_date.date())
        if start_date <= end_date:
            self._populate_transactions(start_date, end_date)

    def _current_month(self):
        today = QDate.currentDate()
        self.start_date.setDate(today.addDays(1 - today.day()))
        self.end_date.setDate(today)
        self.refresh_data()

    def refresh_data(self):
        start_date = self._iso_date(self.start_date.date())
        end_date = self._iso_date(self.end_date.date())
        if start_date > end_date:
            self._show_invalid_period()
            return

        self._refresh_financial(start_date, end_date)
        self._refresh_sales(start_date, end_date)
        self._refresh_purchases(start_date, end_date)
        self._refresh_stock()

    def _show_invalid_period(self):
        for label in (
            self.income_value,
            self.expense_value,
            self.sales_revenue_value,
        ):
            label.setText("—")
        self.balance_value.setText("Período inválido")
        self.sales_count_value.setText("—")
        self.units_sold_value.setText("—")
        self.category_table.setRowCount(0)
        self.transactions_table.setRowCount(0)
        self.products_table.setRowCount(0)
        self.payment_table.setRowCount(0)
        self.purchase_supplier_table.setRowCount(0)
        self.purchase_material_table.setRowCount(0)
        self.stock_materials_table.setRowCount(0)
        self.stock_products_table.setRowCount(0)
        self.financial_status.setText(
            "A data inicial deve ser anterior à data final."
        )
        self.sales_status.setText(
            "A data inicial deve ser anterior à data final."
        )

    def _refresh_financial(self, start_date, end_date):
        summary = get_financial_summary(start_date, end_date)
        transactions = list_transactions(start_date, end_date)
        self.income_value.setText(self._currency(summary["income_cents"]))
        self.expense_value.setText(self._currency(summary["expense_cents"]))
        self.balance_value.setText(self._currency(summary["balance_cents"]))
        self.balance_value.setStyleSheet(
            "color: #187443;" if summary["balance_cents"] >= 0
            else "color: #B42318;"
        )

        self._populate_transactions(start_date, end_date)

        grouped = defaultdict(lambda: {"amount": 0, "count": 0})
        for transaction in transactions:
            category = transaction["category"] or "Sem categoria"
            direction = transaction["direction"]
            group = grouped[(category, direction)]
            group["amount"] += transaction["amount_cents"]
            group["count"] += 1

        rows = sorted(
            grouped.items(),
            key=lambda item: (item[0][0].casefold(), item[0][1]),
        )
        self.category_table.setRowCount(len(rows))
        for row, ((category, direction), values) in enumerate(rows):
            is_income = direction == "income"
            cells = [
                category,
                "Receita" if is_income else "Despesa",
                str(values["count"]),
                self._currency(values["amount"]),
            ]
            for column, value in enumerate(cells):
                item = QTableWidgetItem(value)
                if column in (1, 3):
                    item.setForeground(
                        QColor("#187443") if is_income else QColor("#B42318")
                    )
                if column in (2, 3):
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    )
                self.category_table.setItem(row, column, item)

        self.financial_status.setText(
            f"{len(transactions)} lançamento(s) no período selecionado."
        )

    def _populate_transactions(self, start_date, end_date):
        transactions = list_transactions(
            start_date,
            end_date,
            self.direction_filter.currentData(),
        )
        self.transactions_table.setRowCount(len(transactions))
        for row, transaction in enumerate(transactions):
            date = transaction["transaction_date"]
            formatted_date = f"{date[8:10]}/{date[5:7]}/{date[:4]}"
            is_income = transaction["direction"] == "income"
            values = [
                formatted_date,
                transaction["description"],
                transaction["category"] or "—",
                "Receita" if is_income else "Despesa",
                transaction["payment_method"] or "—",
                self._currency(transaction["amount_cents"]),
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if column in (3, 5):
                    item.setForeground(
                        QColor("#187443") if is_income else QColor("#B42318")
                    )
                if column == 5:
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    )
                self.transactions_table.setItem(row, column, item)

    def _refresh_sales(self, start_date, end_date):
        report = get_sales_report(start_date, end_date)
        self.sales_revenue_value.setText(
            self._currency(report["revenue_cents"])
        )
        self.sales_count_value.setText(str(report["sales_count"]))
        self.units_sold_value.setText(
            f"{report['quantity_milli'] / 1000:,.3f}".replace(",", "X")
            .replace(".", ",").replace("X", ".")
        )

        products = report["by_product"]
        self.products_table.setRowCount(len(products))
        for row, product in enumerate(products):
            quantity = product["quantity_milli"] / 1000
            cells = [
                product["product_name"],
                f"{quantity:,.3f}".replace(",", "X").replace(
                    ".", ","
                ).replace("X", "."),
                self._currency(product["gross_cents"]),
                str(product["sales_count"]),
            ]
            for column, value in enumerate(cells):
                item = QTableWidgetItem(value)
                if column in (1, 2, 3):
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    )
                self.products_table.setItem(row, column, item)

        payments = report["by_payment"]
        self.payment_table.setRowCount(len(payments))
        for row, payment in enumerate(payments):
            cells = [
                payment["payment_method"],
                str(payment["sales_count"]),
                self._currency(payment["revenue_cents"]),
            ]
            for column, value in enumerate(cells):
                item = QTableWidgetItem(value)
                if column == 2:
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    )
                self.payment_table.setItem(row, column, item)

        self.sales_status.setText(
            f"{len(products)} produto(s) com vendas no período selecionado. "
            "Vendas estornadas não entram neste relatório."
        )
