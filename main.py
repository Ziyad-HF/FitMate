import sys
from PyQt5.QtWidgets import QApplication
from gui.mainwindow_ui import MainWindow
from utils.helpers import load_stylesheet


def main():
    app = QApplication(sys.argv)
    # Load and apply stylesheet
    stylesheet = load_stylesheet("style.qss")
    if stylesheet:
        app.setStyleSheet(stylesheet)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
