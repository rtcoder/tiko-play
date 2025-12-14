from PySide6.QtWidgets import QTextEdit

class LogView(QTextEdit):
    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setMinimumHeight(120)

    def append_log(self, text):
        self.append(text)
        self.verticalScrollBar().setValue(
            self.verticalScrollBar().maximum()
        )
