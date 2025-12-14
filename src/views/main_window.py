import asyncio
import threading

from PySide6.QtWidgets import (
    QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QStackedWidget
)

from src.config import load_config, save_config
from src.views.key_editor.key_editor import KeysEditor
from src.listener import TikTokListener
from src.views.log_view import LogView
from src.ui_logger import UILogger


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TikoPlay")
        self.resize(900, 550)
        self.config = load_config()

        self.log_view = None
        self.logger = None

        if self.config.get("show_logs", True):
            self.logger = UILogger()
            self.log_view = LogView()
            self.logger.message.connect(self.log_view.append_log)

        self.listener = TikTokListener(logger=self.logger)

        root = QWidget()
        self.setCentralWidget(root)

        layout = QHBoxLayout(root)

        # SIDEBAR
        sidebar = QVBoxLayout()
        self.btn_streamer = QPushButton("Streamer")
        self.btn_keys = QPushButton("Klawisze")
        self.btn_user = QPushButton("Użytkownik")
        self.btn_toggle = QPushButton("🎧 Nasłuchuj")

        for b in (self.btn_streamer, self.btn_keys, self.btn_user):
            b.setCheckable(True)

        sidebar.addWidget(self.btn_streamer)
        sidebar.addWidget(self.btn_keys)
        sidebar.addWidget(self.btn_user)
        sidebar.addStretch()
        sidebar.addWidget(self.btn_toggle)

        layout.addLayout(sidebar, 1)

        # CONTENT
        self.stack = QStackedWidget()
        layout.addWidget(self.stack, 4)

        if self.log_view:
            content = QVBoxLayout()
            content.addWidget(self.stack, 1)
            content.addWidget(self.log_view)
            layout.addLayout(content, 4)

        # VIEWS
        self.view_streamer = self.build_streamer_view()
        self.view_keys = KeysEditor(
            self.config,
            on_save=lambda: save_config(self.config)
        )
        self.view_user = self.build_user_view()

        self.stack.addWidget(self.view_streamer)
        self.stack.addWidget(self.view_keys)
        self.stack.addWidget(self.view_user)

        self.stack.setCurrentWidget(self.view_streamer)

        self.switch_view(self.view_streamer)
        self.btn_streamer.setChecked(True)

        # SIGNALS
        self.btn_streamer.clicked.connect(lambda: self.switch_view(self.view_streamer))
        self.btn_keys.clicked.connect(lambda: self.switch_view(self.view_keys))
        self.btn_user.clicked.connect(lambda: self.switch_view(self.view_user))
        self.btn_toggle.clicked.connect(self.toggle_listener)

    def switch_view(self, widget):
        self.stack.setCurrentWidget(widget)

    def build_streamer_view(self):
        w = QWidget()
        l = QVBoxLayout(w)

        l.addWidget(QLabel("ID Streamera TikTok"))
        self.input_streamer = QLineEdit(self.config["streamer_id"])
        l.addWidget(self.input_streamer)

        save = QPushButton("Zapisz")
        save.clicked.connect(self.save_streamer)
        l.addWidget(save)
        l.addStretch()
        return w

    def build_user_view(self):
        w = QWidget()
        l = QVBoxLayout(w)

        l.addWidget(QLabel("Nick użytkownika (opcjonalnie)"))
        self.input_user = QLineEdit(self.config["target_user"])
        l.addWidget(self.input_user)

        save = QPushButton("Zapisz")
        save.clicked.connect(self.save_user)
        l.addWidget(save)
        l.addStretch()
        return w

    def build_keys_view(self):
        w = QWidget()
        l = QVBoxLayout(w)

        l.addWidget(QLabel("Mapowania komentarzy"))
        self.list = QListWidget()

        for m in self.config["mappings"]:
            item = QListWidgetItem(f"{m['trigger']} -> {', '.join(m['keys'])}")
            self.list.addItem(item)

        l.addWidget(self.list)
        l.addStretch()
        return w

    def save_streamer(self):
        self.config["streamer_id"] = self.input_streamer.text()
        save_config(self.config)

    def save_user(self):
        self.config["target_user"] = self.input_user.text()
        save_config(self.config)

    def toggle_listener(self):
        if self.listener.running:
            self.listener.stop()
            self.btn_toggle.setText("🎧 Nasłuchuj")
        else:
            self.config = load_config()
            self.btn_toggle.setText("⏹ Zatrzymaj")
            threading.Thread(
                target=lambda: asyncio.run(self.listener.start(self.config)),
                daemon=True
            ).start()
