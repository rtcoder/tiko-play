from PySide6.QtCore import QLocale
from PySide6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QLabel, QVBoxLayout


def system_language(locale=None):
    locale = locale or QLocale.system()
    # uiLanguages honours OS display-language preference, unlike number/date locale.
    languages = locale.uiLanguages()
    primary = languages[0] if languages else locale.name()
    return "pl" if primary.replace("_", "-").split("-")[0].lower() == "pl" else "en"


class LanguageDialog(QDialog):
    def __init__(self, locale=None):
        super().__init__()
        self.setWindowTitle("TikoPlay — Wybierz język / Choose language")
        self.setMinimumWidth(380)
        layout = QVBoxLayout(self)
        label = QLabel("Wybierz język / Choose language")
        layout.addWidget(label)
        self.languages = QComboBox()
        self.languages.addItem("Polski", "pl")
        self.languages.addItem("English", "en")
        self.languages.setCurrentIndex(self.languages.findData(system_language(locale)))
        label.setBuddy(self.languages)
        self.languages.setAccessibleName(label.text())
        layout.addWidget(self.languages)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Dalej / Continue")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(
            "Anuluj / Cancel"
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


def choose_language(preferences, locale=None):
    if preferences.language is not None:
        return preferences.language
    dialog = LanguageDialog(locale)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None
    language = dialog.languages.currentData()
    preferences.save(language)
    return language
