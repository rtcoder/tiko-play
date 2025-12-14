from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLineEdit,
    QPushButton, QComboBox
)

from src.views.key_editor.key_chip import KeyChip
from src.views.key_editor.special_keys import SPECIAL_KEYS


class MappingRow(QWidget):
    def __init__(self, mapping: dict, index, on_change, on_remove):
        super().__init__()
        self.index = index
        self.mapping = mapping
        self.on_change = on_change

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.keys_layout = QHBoxLayout()
        self.keys_layout.setSpacing(6)
        self.keys_layout.addStretch()
        layout.addLayout(self.keys_layout)

        # trigger
        self.input_trigger = QLineEdit(mapping.get("trigger", ""))
        self.input_trigger.setPlaceholderText("komentarz")
        self.input_trigger.textChanged.connect(self.update)
        layout.addWidget(self.input_trigger)

        # klawisze
        self.key_boxes = []
        for key in mapping.get("keys", []):
            self.add_key_box(key)

        btn_add = QPushButton("+")
        btn_add.clicked.connect(lambda: self.add_key_box())
        layout.addWidget(btn_add)

        btn_remove = QPushButton("✕")
        btn_remove.clicked.connect(
            lambda: on_remove(self.index)
        )
        layout.addWidget(btn_remove)
        self.render_keys()

    def add_key_box(self, value=""):
        box = QComboBox()
        box.addItems(SPECIAL_KEYS)
        if value:
            box.setCurrentText(value)
        box.currentTextChanged.connect(self.update)
        self.key_boxes.append(box)
        self.update()

    def update(self):
        self.mapping["trigger"] = self.input_trigger.text().strip()
        self.mapping["keys"] = [b.currentText() for b in self.key_boxes]
        self.on_change()

    def add_key(self, value):
        if value and value not in self.mapping["keys"]:
            self.mapping["keys"].append(value)
            self.render_keys()

        self.on_change()

    def remove_key(self, index):
        if 0 <= index < len(self.mapping["keys"]):
            self.mapping["keys"].pop(index)
            self.render_keys()

        self.on_change()

    def render_keys(self):
        # wyczyść layout
        while self.keys_layout.count():
            item = self.keys_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # istniejące klawisze → chipy
        for i, key in enumerate(self.mapping["keys"]):
            chip = KeyChip(
                key,
                on_remove=lambda idx=i: self.remove_key(idx)
            )
            self.keys_layout.addWidget(chip)

        # select do dodawania nowego
        box = QComboBox()
        box.addItem("+ klawisz")
        box.addItems(SPECIAL_KEYS)
        def on_select(value):
            if value != "+ klawisz":
                self.add_key(value)
                box.setCurrentIndex(0)

        box.currentTextChanged.connect(on_select)
        self.keys_layout.addWidget(box)

        self.keys_layout.addStretch()
