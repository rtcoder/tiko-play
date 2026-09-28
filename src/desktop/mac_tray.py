"""AppKit owns menu tracking, avoiding Qt's macOS status-menu event filter."""
from AppKit import NSImage, NSMenu, NSMenuItem, NSStatusBar, NSVariableStatusItemLength
from Foundation import NSData, NSObject
from PySide6.QtCore import QBuffer, QIODevice


class TikoPlayMenuTarget(NSObject):
    def invoke_(self, sender):
        self.actions[sender.tag()].trigger()


class MacTray:
    def __init__(self, icon, actions):
        self.target = TikoPlayMenuTarget.alloc().init()
        self.target.actions = list(actions)
        self.menu = NSMenu.alloc().initWithTitle_("TikoPlay")
        self.menu.setAutoenablesItems_(False)
        self._connections = []
        for index, action in enumerate(self.target.actions):
            if action.isSeparator():
                self.menu.addItem_(NSMenuItem.separatorItem())
                continue
            item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                action.text(), "invoke:", ""
            )
            item.setTarget_(self.target)
            item.setTag_(index)
            item.setEnabled_(action.isEnabled())
            self.menu.addItem_(item)

            def sync(action=action, item=item):
                item.setTitle_(action.text())
                item.setEnabled_(action.isEnabled())

            action.changed.connect(sync)
            self._connections.append((action, sync))

        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        icon.pixmap(36, 36).save(buffer, "PNG")
        raw = bytes(buffer.data())
        image = NSImage.alloc().initWithData_(NSData.dataWithBytes_length_(raw, len(raw)))
        image.setSize_((18, 18))
        image.setTemplate_(True)
        self.item = NSStatusBar.systemStatusBar().statusItemWithLength_(NSVariableStatusItemLength)
        self.item.button().setImage_(image)
        # An attached NSMenu handles both left and right clicks in AppKit.
        self.item.setMenu_(self.menu)

    def set_tooltip(self, text):
        self.item.button().setToolTip_(text)

    def close(self):
        for action, sync in self._connections:
            action.changed.disconnect(sync)
        self._connections.clear()
        if self.item is not None:
            self.item.setMenu_(None)
            NSStatusBar.systemStatusBar().removeStatusItem_(self.item)
            self.item = None
        self.target.actions = []
