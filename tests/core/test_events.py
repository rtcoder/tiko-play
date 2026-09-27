from src.core.events import EventBus


def test_bounds_and_slow_client():
    bus = EventBus("one")
    slow = bus.subscribe()
    for n in range(1001):
        bus.publish("comment", {"comment": "a" * 2001})
    assert len(bus.recent()) == 1000 and bus.recent()[0]["id"] == 2
    assert len(bus.recent()[-1]["payload"]["comment"]) == 2000
    assert slow.closed
    fresh = bus.subscribe()
    bus.publish("status", {})
    assert fresh.queue.get_nowait()["id"] == 1002
    bus.unsubscribe(fresh)
    assert fresh not in bus.subscribers
