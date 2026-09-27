"""Platform-specific tray artwork, independent of the application/dock icon."""
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPainter, QPainterPath, QPen, QPixmap

from src.desktop.resources import resource_path


def create_tray_icon():
    if sys.platform != "darwin":
        return QIcon(str(resource_path("tiko_play.ico")))

    # macOS treats this alpha silhouette as an NSImage template and supplies
    # black/white itself, including appearance changes and menu highlighting.
    icon = QIcon()
    for size in (18, 36, 54):
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.scale(size / 18, size / 18)
        # Rounded, right-leaning capital T outline, matching the main logo.
        path = QPainterPath()
        path.moveTo(4.5, 2)
        path.lineTo(14.5, 2)
        path.cubicTo(16.4, 2, 16, 3.5, 15.5, 4.4)
        path.cubicTo(15.2, 5, 14.8, 5, 14.2, 5)
        path.lineTo(11, 5)
        path.cubicTo(10.2, 5, 10, 5.5, 9.8, 6.2)
        path.lineTo(7.3, 13.5)
        path.cubicTo(6.7, 15.2, 5.2, 15.7, 3.9, 15.7)
        path.cubicTo(3.4, 15.7, 3.6, 15, 3.8, 14.5)
        path.lineTo(6.4, 6.2)
        path.cubicTo(6.7, 5.4, 6.3, 5, 5.6, 5)
        path.lineTo(2, 5)
        path.cubicTo(1.5, 5, 1.8, 4.4, 2, 3.8)
        path.cubicTo(2.4, 2.5, 3.1, 2, 4.5, 2)
        path.closeSubpath()
        pen = QPen(Qt.GlobalColor.black, 1.25)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.strokePath(path, pen)
        painter.end()
        icon.addPixmap(pixmap)
    icon.setIsMask(True)
    return icon
