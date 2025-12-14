from PySide6.QtWidgets import QPushButton


class KeyChip(QPushButton):
    def __init__(self, key, on_remove):
        super().__init__(key.upper())
        self.setFixedHeight(28)
        self.clicked.connect(on_remove)

        self.setStyleSheet("""
        QPushButton {
            background: #2a2a2a;
            border: 1px solid #444;
            border-radius: 6px;
            padding: 4px 8px;
        }
        QPushButton:hover {
            background: #3a3a3a;
        }
        """)
