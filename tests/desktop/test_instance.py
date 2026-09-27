from src.desktop.instance import InstanceGuard

def test_second_instance_notifies_owner(tmp_path,qtbot):
    first=InstanceGuard(tmp_path);second=InstanceGuard(tmp_path)
    assert first.acquire_or_notify()
    with qtbot.waitSignal(first.open_requested,timeout=3000):
        assert not second.acquire_or_notify()
    first.close()
    third=InstanceGuard(tmp_path);assert third.acquire_or_notify();third.close()
