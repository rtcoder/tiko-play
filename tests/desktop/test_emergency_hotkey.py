from src.desktop.emergency_hotkey import EmergencyHotkey


def test_registration_failure_keeps_old_working_shortcut(qtbot):
    callbacks = []
    closed = []

    class Registration:
        def __init__(self, key, callback):
            if key == "F9":
                raise OSError("conflict")
            self.key = key
            callbacks.append(callback)

        def close(self):
            closed.append(self.key)

    stopped = []
    hotkey = EmergencyHotkey(lambda: stopped.append(True), factory=Registration)
    assert hotkey.state() == {"key": "F10", "active": True, "error": None}
    callbacks[-1]()
    callbacks[-1]()
    assert stopped == [True, True]
    future = hotkey.configure("F9")
    qtbot.waitUntil(future.done)
    assert (
        future.result()["key"] == "F10"
        and future.result()["active"]
        and future.result()["error"]
    )
    assert not closed
    future = hotkey.configure("F11")
    qtbot.waitUntil(future.done)
    assert future.result() == {"key": "F11", "active": True, "error": None}
    assert closed == ["F10"]
    hotkey.close()
    assert not hotkey.state()["active"]


def test_unavailable_shortcut_is_not_reported_active(qtbot):
    def fail(*args):
        raise OSError("unavailable")

    hotkey = EmergencyHotkey(lambda: None, factory=fail)
    assert not hotkey.state()["active"] and hotkey.state()["error"]
    hotkey.close()


def test_reconfiguration_from_backend_runs_on_qt_thread(qtbot):
    import threading
    main_thread = threading.get_ident()
    threads = []
    class Registration:
        def __init__(self, key, callback): threads.append(threading.get_ident())
        def close(self): threads.append(threading.get_ident())
    hotkey = EmergencyHotkey(lambda: None, factory=Registration)
    futures = []
    worker = threading.Thread(target=lambda: futures.append(hotkey.configure("F11")))
    worker.start(); worker.join(1)
    qtbot.waitUntil(lambda: bool(futures) and futures[0].done())
    hotkey.close()
    assert threads and all(t == main_thread for t in threads)
