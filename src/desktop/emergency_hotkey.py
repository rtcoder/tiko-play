"""Native registered hotkeys on the Qt main thread (no keyboard recording)."""

import concurrent.futures
import ctypes as c
import itertools
import sys

from PySide6.QtCore import QAbstractNativeEventFilter, QCoreApplication, QObject, Signal

_IDS = itertools.count(0x5100)


class MacRegistration:
    class EventType(c.Structure):
        _fields_ = [("eventClass", c.c_uint32), ("eventKind", c.c_uint32)]

    class HotkeyID(c.Structure):
        _fields_ = [("signature", c.c_uint32), ("id", c.c_uint32)]

    CALLBACK = c.CFUNCTYPE(c.c_int32, c.c_void_p, c.c_void_p, c.c_void_p)

    def __init__(self, key, callback):
        self.lib = c.CDLL("/System/Library/Frameworks/Carbon.framework/Carbon")
        self.ref = c.c_void_p()
        self.handler = c.c_void_p()
        self.id = next(_IDS)
        lib = self.lib
        lib.GetApplicationEventTarget.restype = c.c_void_p
        lib.InstallEventHandler.argtypes = [
            c.c_void_p,
            self.CALLBACK,
            c.c_uint32,
            c.POINTER(self.EventType),
            c.c_void_p,
            c.POINTER(c.c_void_p),
        ]
        lib.RegisterEventHotKey.argtypes = [
            c.c_uint32,
            c.c_uint32,
            self.HotkeyID,
            c.c_void_p,
            c.c_uint32,
            c.POINTER(c.c_void_p),
        ]
        lib.UnregisterEventHotKey.argtypes = [c.c_void_p]
        lib.RemoveEventHandler.argtypes = [c.c_void_p]
        lib.GetEventParameter.argtypes = [
            c.c_void_p,
            c.c_uint32,
            c.c_uint32,
            c.c_void_p,
            c.c_uint32,
            c.c_void_p,
            c.c_void_p,
        ]

        @self.CALLBACK
        def receive(_, event, __):
            identifier = self.HotkeyID()
            if (
                lib.GetEventParameter(
                    event,
                    0x2D2D2D2D,
                    0x686B6964,
                    None,
                    c.sizeof(identifier),
                    None,
                    c.byref(identifier),
                )
                == 0
                and identifier.id == self.id
                and identifier.signature == 0x54696B6F
            ):
                callback()
                return 0
            return -9874  # eventNotHandledErr

        self.receive = receive
        event_type = self.EventType(0x6B657962, 6)
        target = lib.GetApplicationEventTarget()
        status = lib.InstallEventHandler(
            target, receive, 1, c.byref(event_type), None, c.byref(self.handler)
        )
        if status:
            raise RuntimeError(f"handler {status}")
        status = lib.RegisterEventHotKey(
            {"F9": 101, "F10": 109, "F11": 103}[key],
            (1 << 12) | (1 << 11) | (1 << 9),
            self.HotkeyID(0x54696B6F, self.id),
            target,
            0,
            c.byref(self.ref),
        )
        if status:
            self.close()
            raise RuntimeError(f"hotkey {status}")

    def close(self):
        if self.ref.value:
            self.lib.UnregisterEventHotKey(self.ref)
            self.ref = c.c_void_p()
        if self.handler.value:
            self.lib.RemoveEventHandler(self.handler)
            self.handler = c.c_void_p()


class WindowsRegistration(QAbstractNativeEventFilter):
    def __init__(self, key, callback):
        super().__init__()
        from ctypes import wintypes as w

        self.w = w
        self.callback = callback
        self.id = next(_IDS)
        self.lib = c.WinDLL("user32", use_last_error=True)
        self.lib.RegisterHotKey.argtypes = [w.HWND, c.c_int, w.UINT, w.UINT]
        self.lib.UnregisterHotKey.argtypes = [w.HWND, c.c_int]
        if not self.lib.RegisterHotKey(
            None,
            self.id,
            0x4000 | 1 | 2 | 4,
            {"F9": 0x78, "F10": 0x79, "F11": 0x7A}[key],
        ):
            raise RuntimeError(f"hotkey {c.get_last_error()}")
        QCoreApplication.instance().installNativeEventFilter(self)

    def nativeEventFilter(self, eventType, message):
        msg = self.w.MSG.from_address(int(message))
        if msg.message == 0x0312 and msg.wParam == self.id:
            self.callback()
            return True, 0
        return False, 0

    def close(self):
        QCoreApplication.instance().removeNativeEventFilter(self)
        self.lib.UnregisterHotKey(None, self.id)


class EmergencyHotkey(QObject):
    change_requested = Signal(str, object)

    def __init__(self, callback, *, factory=None):
        super().__init__()
        self.callback = callback
        self.factory = factory or (
            MacRegistration
            if sys.platform == "darwin"
            else WindowsRegistration
            if sys.platform == "win32"
            else None
        )
        self.registration = None
        self.key = "F10"
        self.error = None
        self.change_requested.connect(self._change)
        self._change("F10", None)

    def state(self):
        return {
            "key": self.key,
            "active": self.registration is not None,
            "error": self.error,
        }

    def configure(self, key):
        future = concurrent.futures.Future()
        self.change_requested.emit(key, future)
        return future

    def _change(self, key, future):
        try:
            if key not in ("F9", "F10", "F11"):
                raise ValueError("key")
            if key != self.key or self.registration is None:
                if self.factory is None:
                    raise RuntimeError("platform")
                registration = self.factory(key, self.callback)
                old = self.registration
                self.registration = registration
                self.key = key
                if old:
                    old.close()
            self.error = None
        except Exception:
            self.error = "Nie można zarejestrować skrótu. Wybierz inny klawisz lub sprawdź ustawienia systemowe."
        if future and not future.done():
            future.set_result(self.state())

    def close(self):
        if self.registration:
            self.registration.close()
            self.registration = None
