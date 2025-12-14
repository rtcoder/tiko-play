from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel,
    QPushButton, QScrollArea, QHBoxLayout, QComboBox, QMessageBox
)

from src.views.key_editor.presets import PRESETS
from src.config import save_config
from src.views.key_editor.mapping_row import MappingRow


class KeysEditor(QWidget):
    def __init__(self, config, on_save):
        super().__init__()
        self.config = config
        self.on_save = on_save

        self.autosave_timer = QTimer(self)
        self.autosave_timer.setSingleShot(True)
        self.autosave_timer.setInterval(500)  # ms
        self.autosave_timer.timeout.connect(self.autosave)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        # HEADER
        root.addWidget(QLabel("Mapowanie komentarzy → klawisze"))

        preset_bar = QHBoxLayout()
        self.preset_select = QComboBox()
        self.preset_select.addItem("— wybierz preset —")
        self.preset_select.addItems(PRESETS.keys())

        btn_apply = QPushButton("Zastosuj preset")
        btn_apply.clicked.connect(self.apply_preset)

        preset_bar.addWidget(QLabel("Presety:"))
        preset_bar.addWidget(self.preset_select)
        preset_bar.addWidget(btn_apply)
        preset_bar.addStretch()

        root.addLayout(preset_bar)

        # ===== SCROLL AREA =====
        self.container = QWidget()
        self.rows_layout = QVBoxLayout(self.container)
        self.rows_layout.setSpacing(8)
        self.rows_layout.addStretch()  # ważne!

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.container)
        scroll.setMinimumHeight(200)

        root.addWidget(scroll, 1)  # ← ROŚNIE

        # ===== FIXED BOTTOM BAR =====
        bottom = QHBoxLayout()

        btn_add = QPushButton("➕ Dodaj mapowanie")
        btn_add.clicked.connect(self.add_mapping)

        btn_save = QPushButton("💾 Zapisz")
        btn_save.clicked.connect(self.save)

        bottom.addWidget(btn_add)
        bottom.addStretch()
        bottom.addWidget(btn_save)

        root.addLayout(bottom)

        # init rows
        for m in self.config["mappings"]:
            self.add_row(m)

    def schedule_autosave(self):
        self.autosave_timer.start()

    def autosave(self):
        save_config(self.config)

        # opcjonalny log
        if hasattr(self, "logger") and self.logger:
            self.logger.log("💾 Autosave")

    def apply_preset(self):
        name = self.preset_select.currentText()

        if name not in PRESETS:
            return

        reply = QMessageBox.question(
            self,
            "Zastosować preset?",
            "To nadpisze aktualne mapowania.\nCzy kontynuować?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        self.config["mappings"] = [
            {"trigger": m["trigger"], "keys": list(m["keys"])}
            for m in PRESETS[name]
        ]

        self.rebuild()
        self.schedule_autosave()
        self.preset_select.setCurrentIndex(0)

    def add_row(self, mapping):
        index = len(self.config["mappings"]) - 1

        row = MappingRow(
            mapping,
            index=index,
            on_change=lambda: self.schedule_autosave,
            on_remove=lambda r=mapping: self.remove_mapping(r)
        )
        self.rows_layout.addWidget(row)

    def add_mapping(self):
        mapping = {"trigger": "", "keys": [""]}
        self.config["mappings"].append(mapping)
        self.add_row(mapping)
        self.schedule_autosave()

    def remove_mapping(self, index):
        print(f"removing {index}")

        if 0 <= index < len(self.config["mappings"]):
            self.config["mappings"].pop(index)

        self.rebuild()
        self.schedule_autosave()

    def rebuild(self):
        while self.rows_layout.count():
            item = self.rows_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for i, m in enumerate(self.config["mappings"]):
            row = MappingRow(
                m,
                index=i,
                on_change=lambda: None,
                on_remove=self.remove_mapping
            )
            self.rows_layout.addWidget(row)

    def save(self):
        # walidacja
        self.config["mappings"] = [
            m for m in self.config["mappings"]
            if m["trigger"] and m["keys"]
        ]
        self.on_save()
