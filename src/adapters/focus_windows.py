"""Win32 foreground process identity; process handles always closed."""

import ctypes as c
from ctypes import wintypes as w
from pathlib import PureWindowsPath

from src.core.output_guard import TargetIdentity


class WindowsFocus:
    def __init__(self):
        self.user = c.WinDLL("user32", use_last_error=True)
        self.kernel = c.WinDLL("kernel32", use_last_error=True)
        self.user.GetForegroundWindow.restype = w.HWND
        self.user.GetWindowThreadProcessId.argtypes = [w.HWND, c.POINTER(w.DWORD)]
        self.user.IsWindowVisible.argtypes = [w.HWND]
        self.kernel.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
        self.kernel.OpenProcess.restype = w.HANDLE
        self.kernel.QueryFullProcessImageNameW.argtypes = [
            w.HANDLE,
            w.DWORD,
            w.LPWSTR,
            c.POINTER(w.DWORD),
        ]
        self.kernel.GetProcessTimes.argtypes = [w.HANDLE] + [c.POINTER(w.FILETIME)] * 4
        self.kernel.CloseHandle.argtypes = [w.HANDLE]
        self._enum_type = c.WINFUNCTYPE(w.BOOL, w.HWND, w.LPARAM)
        self.user.EnumWindows.argtypes = [self._enum_type, w.LPARAM]

    def identity(self, hwnd):
        if not hwnd:
            return None
        pid = w.DWORD()
        self.user.GetWindowThreadProcessId(hwnd, c.byref(pid))
        handle = self.kernel.OpenProcess(0x1000, False, pid.value)
        if not handle:
            return None
        try:
            size = w.DWORD(32768)
            path = c.create_unicode_buffer(size.value)
            times = [w.FILETIME() for _ in range(4)]
            if not self.kernel.QueryFullProcessImageNameW(
                handle, 0, path, c.byref(size)
            ):
                return None
            if not self.kernel.GetProcessTimes(handle, *[c.byref(t) for t in times]):
                return None
            started = (times[0].dwHighDateTime << 32) | times[0].dwLowDateTime
            return TargetIdentity(
                app=path.value.casefold(),
                pid=pid.value,
                started=str(started),
                name=PureWindowsPath(path.value).name[:256],
            )
        finally:
            self.kernel.CloseHandle(handle)

    def current_target(self):
        return self.identity(self.user.GetForegroundWindow())

    def targets(self):
        import os

        found = {}

        @self._enum_type
        def visit(hwnd, _):
            if self.user.IsWindowVisible(hwnd):
                target = self.identity(hwnd)
                if target and target.pid != os.getpid():
                    found[target.pid] = target
            return True

        if not self.user.EnumWindows(visit, 0):
            raise OSError("Cannot enumerate windows")
        return list(found.values())
