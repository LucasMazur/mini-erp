
APP_STYLE = """
/* ===== ESTILO GLOBAL MAZURON ===== */

QWidget {
    font-family: "Segoe UI";
    font-size: 13px;
    color: #303640;
}

QMainWindow {
    background-color: #F4F6F8;
}

/* ===== IDENTIDADE DA MARCA ===== */

#sidebar {
    background-color: #1A1A1A;
    border: none;
}

#brand_mark {
    color: #1A1A1A;
    background-color: #C0C6CC;
    border-radius: 10px;
    min-width: 48px;
    max-width: 48px;
    min-height: 48px;
    max-height: 48px;
    font-size: 30px;
    font-weight: 800;
}

#brand_name {
    color: #F8FAFC;
    font-size: 19px;
    font-weight: 800;
    letter-spacing: 3px;
}

#brand_erp {
    color: #AEB5BE;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 4px;
}

#brand_tagline {
    color: #9CA3AD;
    font-size: 11px;
}

#sidebar_footer {
    color: #737B86;
    font-size: 10px;
    padding-top: 12px;
    border-top: 1px solid #353A41;
}

/* ===== MENU LATERAL ===== */

#menu_button {
    color: #C5CAD1;
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 8px;
    text-align: left;
    padding: 12px 14px;
    font-size: 13px;
    font-weight: 500;
}

#menu_button:hover {
    background-color: #30343A;
    color: #FFFFFF;
}

#menu_button:checked {
    background-color: #3B4149;
    color: #FFFFFF;
    border-left: 3px solid #C0C6CC;
    font-weight: 700;
}

/* ===== TÍTULOS ===== */

#page_title {
    color: #252B33;
    font-size: 27px;
    font-weight: 700;
}

#page_subtitle {
    color: #8491A0;
    font-size: 13px;
}

/* ===== CARTÕES ===== */

#dashboard_card {
    background-color: #FFFFFF;
    border: 1px solid #E2E5E9;
    border-radius: 14px;
}

#card_name {
    color: #8491A0;
    font-size: 13px;
}

#card_value {
    color: #252B33;
    font-size: 27px;
    font-weight: 700;
}

/* ===== BOTÕES ===== */

QPushButton {
    background-color: #FFFFFF;
    color: #39414B;
    border: 1px solid #D9DEE4;
    border-radius: 8px;
    padding: 9px 16px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #F0F2F5;
    border-color: #AEB5BE;
}

QPushButton:pressed {
    background-color: #E1E5E9;
}

QPushButton:disabled {
    color: #AAB1BA;
    background-color: #F3F4F6;
    border-color: #E5E7EB;
}

#primary_button {
    background-color: #414A55;
    color: #FFFFFF;
    border: 1px solid #414A55;
    border-radius: 8px;
    padding: 10px 18px;
    font-weight: 600;
}

#primary_button:hover {
    background-color: #303842;
    border-color: #303842;
}

#primary_button:pressed {
    background-color: #20262E;
}

/* ===== CAMPOS DE TEXTO ===== */

QLineEdit,
QComboBox,
QDoubleSpinBox,
QSpinBox,
QDateEdit {
    background-color: #FFFFFF;
    color: #303640;
    border: 1px solid #D9DEE4;
    border-radius: 8px;
    padding: 10px 12px;
    min-height: 20px;
    selection-background-color: #7D8793;
}

QLineEdit:hover,
QComboBox:hover,
QDoubleSpinBox:hover,
QSpinBox:hover,
QDateEdit:hover {
    border-color: #AEB5BE;
}

QLineEdit:focus,
QComboBox:focus,
QDoubleSpinBox:focus,
QSpinBox:focus,
QDateEdit:focus {
    border: 1px solid #7D8793;
}

QLineEdit:disabled,
QComboBox:disabled {
    background-color: #F2F3F5;
    color: #9AA1AA;
}

QComboBox::drop-down {
    border: none;
    width: 28px;
}

QComboBox QAbstractItemView {
    background-color: #FFFFFF;
    color: #303640;
    border: 1px solid #D9DEE4;
    selection-background-color: #E9EDF1;
    selection-color: #252B33;
    padding: 5px;
}

/* ===== ÁREA DE OBSERVAÇÕES ===== */

QTextEdit {
    background-color: #FFFFFF;
    color: #303640;
    border: 1px solid #D9DEE4;
    border-radius: 8px;
    padding: 9px;
    selection-background-color: #7D8793;
}

QTextEdit:focus {
    border: 1px solid #7D8793;
}

/* ===== TABELAS ===== */

QTableWidget {
    background-color: #FFFFFF;
    alternate-background-color: #F7F8FA;
    color: #39414B;
    border: 1px solid #E2E5E9;
    border-radius: 10px;
    gridline-color: #ECEEF1;
    selection-background-color: #E9EDF1;
    selection-color: #252B33;
    outline: none;
}

QTableWidget::item {
    padding: 9px;
    border: none;
}

QTableWidget::item:selected {
    background-color: #E9EDF1;
    color: #252B33;
}

QHeaderView::section {
    background-color: #F1F3F5;
    color: #68717D;
    border: none;
    border-bottom: 1px solid #E2E5E9;
    padding: 12px 9px;
    font-size: 12px;
    font-weight: 700;
}

/* ===== FORMULÁRIOS ===== */

QLabel {
    background-color: transparent;
}

QCheckBox {
    spacing: 8px;
    color: #39414B;
}

QCheckBox::indicator {
    width: 17px;
    height: 17px;
}

QCheckBox::indicator:unchecked {
    border: 1px solid #BCC3CC;
    border-radius: 4px;
    background-color: #FFFFFF;
}

QCheckBox::indicator:checked {
    border: 1px solid #697480;
    border-radius: 4px;
    background-color: #697480;
}

/* ===== CAIXAS DE DIÁLOGO ===== */

QMessageBox,
QDialog {
    background-color: #F4F6F8;
}

/* ===== BARRAS DE ROLAGEM ===== */

QScrollBar:vertical {
    background-color: transparent;
    width: 9px;
    margin: 2px;
}

QScrollBar::handle:vertical {
    background-color: #C3C9D0;
    border-radius: 4px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background-color: #9DA6B0;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background-color: transparent;
    height: 9px;
    margin: 2px;
}

QScrollBar::handle:horizontal {
    background-color: #C3C9D0;
    border-radius: 4px;
    min-width: 30px;
}

QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {
    width: 0px;
}
"""
