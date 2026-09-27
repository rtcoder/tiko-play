from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon
from src.desktop import tray_icon
from src.desktop.resources import resource_path


def test_macos_template_has_transparent_background_and_monochrome_mark(qapp, monkeypatch):
    monkeypatch.setattr(tray_icon.sys, "platform", "darwin")
    icon = tray_icon.create_tray_icon()
    assert icon.isMask()
    for size in (18, 36, 54):
        image = icon.pixmap(QSize(size, size)).toImage()
        pixels = [image.pixelColor(x, y) for x in range(image.width()) for y in range(image.height())]
        assert image.pixelColor(0, 0).alpha() == 0
        assert any(pixel.alpha() == 255 for pixel in pixels)
        assert all(pixel.red() == pixel.green() == pixel.blue() == 0 for pixel in pixels if pixel.alpha())


def test_windows_keeps_existing_colored_icon(qapp, monkeypatch):
    monkeypatch.setattr(tray_icon.sys, "platform", "win32")
    icon = tray_icon.create_tray_icon()
    assert not icon.isMask()
    assert not icon.isNull()
    original = QIcon(str(resource_path("tiko_play.ico")))
    assert icon.pixmap(32, 32).toImage() == original.pixmap(32, 32).toImage()
