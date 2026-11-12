
import sys

from PySide6.QtWidgets import QApplication

from app.database.initialize import initialize_database
from app.database.seed_units import seed_units
from app.ui.main_window import MainWindow
from app.ui.styles import APP_STYLE


def main():
    initialize_database()
    seed_units()

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(APP_STYLE)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
