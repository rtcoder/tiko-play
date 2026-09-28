import json

import pytest
from PySide6.QtCore import QLocale, QTimer
from PySide6.QtWidgets import QComboBox


@pytest.mark.parametrize(
    "locale, expected",
    [("pl_PL", "pl"), ("en_GB", "en"), ("de_DE", "en"), ("fr_FR", "en")],
)
def test_system_language_preselection(qtbot, locale, expected):
    from src.desktop.language import LanguageDialog

    dialog = LanguageDialog(QLocale(locale))
    qtbot.addWidget(dialog)
    assert dialog.findChild(QComboBox).currentData() == expected


def test_confirmed_choice_survives_restart_and_system_language_change(qtbot, tmp_path):
    from src.core.preferences import PreferencesStore
    from src.desktop.language import LanguageDialog, choose_language

    path = tmp_path / "preferences.json"

    def confirm():
        from PySide6.QtWidgets import QApplication

        dialog = QApplication.activeModalWidget()
        assert isinstance(dialog, LanguageDialog)
        dialog.findChild(QComboBox).setCurrentIndex(0)  # Polski
        dialog.accept()

    QTimer.singleShot(0, confirm)
    assert choose_language(PreferencesStore(path), QLocale("en_US")) == "pl"
    assert json.loads(path.read_text())["language"] == "pl"
    # No modal can appear on the second call.
    assert choose_language(PreferencesStore(path), QLocale("de_DE")) == "pl"


def test_cancel_does_not_save_language(qtbot, tmp_path):
    from PySide6.QtWidgets import QApplication

    from src.core.preferences import PreferencesStore
    from src.desktop.language import choose_language

    path = tmp_path / "preferences.json"
    QTimer.singleShot(0, lambda: QApplication.activeModalWidget().reject())
    assert choose_language(PreferencesStore(path), QLocale("pl_PL")) is None
    assert not path.exists()


def test_unsupported_primary_display_language_does_not_use_secondary_polish():
    from types import SimpleNamespace

    from src.desktop.language import system_language

    assert (
        system_language(SimpleNamespace(uiLanguages=lambda: ["de-DE", "pl-PL"])) == "en"
    )


@pytest.mark.parametrize("content", ['{"language":"de"}', "{broken", "{}"])
def test_invalid_preference_asks_again_without_touching_config(tmp_path, content):
    from src.core.preferences import PreferencesStore

    path = tmp_path / "preferences.json"
    path.write_text(content)
    config = tmp_path / "config.json"
    config.write_text('{"version":4,"mappings":[{"trigger":"lewo"}]}')
    before = config.read_bytes()
    assert PreferencesStore(path).language is None
    assert config.read_bytes() == before


def test_failed_preference_write_retains_previous_choice(tmp_path, monkeypatch):
    import src.core.preferences as module

    prefs = module.PreferencesStore(tmp_path / "preferences.json")
    prefs.save("pl")

    def denied(*args):
        raise PermissionError("read only")

    monkeypatch.setattr(module.os, "replace", denied)
    with pytest.raises(PermissionError):
        prefs.save("en")
    assert prefs.language == "pl"
    assert module.PreferencesStore(prefs.path).language == "pl"
    assert not list(tmp_path.glob(".preferences-*.tmp"))
