from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel,
    QPushButton, QScrollArea, QHBoxLayout
)

from src.views.key_editor.mapping_row import MappingRow


class KeysEditor(QWidget):
    def __init__(self, config, on_save):
        super().__init__()
        self.config = config
        self.on_save = on_save

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        # HEADER
        root.addWidget(QLabel("Mapowanie komentarzy → klawisze"))

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

    def add_row(self, mapping):
        index = len(self.config["mappings"]) - 1

        row = MappingRow(
            mapping,
            index=index,
            on_change=lambda: None,
            on_remove=lambda r=mapping: self.remove_mapping(r)
        )
        self.rows_layout.addWidget(row)

    def add_mapping(self):
        mapping = {"trigger": "", "keys": [""]}
        self.config["mappings"].append(mapping)
        self.add_row(mapping)

    def remove_mapping(self, index):
        print(f"removing {index}")

        if 0 <= index < len(self.config["mappings"]):
            self.config["mappings"].pop(index)

        self.rebuild()

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
