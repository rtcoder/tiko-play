from PySide6.QtCore import QObject, Signal

class UILogger(QObject):
    message = Signal(str)

    def log(self, text: str):
        self.message.emit(text)
