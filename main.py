import sys

from PySide6.QtWidgets import QApplication

from src.views.main_window import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)

    app.setStyleSheet("""
    QMainWindow { background: #121212; color: #eee; }
    QPushButton {
        background: #1e1e1e;
        color: #eee;
        padding: 8px;
        border-radius: 6px;
    }
    QPushButton:checked { background: #333; }
    QPushButton:hover { background: #2a2a2a; }
    QLineEdit {
        background: #1e1e1e;
        border: 1px solid #333;
        padding: 6px;
        color: #eee;
    }
    QListWidget {
        background: #1e1e1e;
        border: 1px solid #333;
    }
    """)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())
