from PySide6.QtCore import QObject, Signal

class UILogger(QObject):
    message = Signal(str)

    def log(self, text: str):
        self.message.emit(text)

    def connect_log_view(self, log_view):
        if log_view is None:
            raise ValueError("Log view cannot be None")
        self.message.connect(log_view.append_log)
