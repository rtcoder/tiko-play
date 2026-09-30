import socket

import httpx
import pytest

from src.core.models import AppError
from src.core.overlay import OverlaySettings, OverlayStore
from src.desktop.overlay_server import OverlayServer


class Projection:
    def snapshot(self):
        return {"sequence": 1, "paused": True}


async def test_port_conflict_preserves_running_server_and_settings(tmp_path):
    static = tmp_path / "static"
    static.mkdir()
    (static / "index.html").write_text("overlay")
    store = OverlayStore(tmp_path / "overlay.json")
    server = OverlayServer(store, Projection(), static)
    with socket.socket() as available:
        available.bind(("127.0.0.1", 0))
        port = available.getsockname()[1]
    settings = OverlaySettings(enabled=True, port=port)
    await server.configure(settings)
    try:
        url = server.state()["url"]
        assert "#token=" in url
        async with httpx.AsyncClient(trust_env=False) as c:
            assert (await c.get(url.split("#")[0])).status_code == 200
        with socket.socket() as occupied:
            occupied.bind(("127.0.0.1", 0))
            occupied.listen()
            with pytest.raises(AppError):
                await server.configure(
                    settings.model_copy(update={"port": occupied.getsockname()[1]})
                )
        assert store.settings == settings
        assert server.state()["url"] == url
        await server.rotate()
        assert server.state()["url"] != url
        await server.configure(settings.model_copy(update={"enabled": False}))
        assert server.state()["url"] is None
    finally:
        await server.close()


async def test_restart_reuses_address_and_token_after_open_websocket(tmp_path):
    import json

    from websockets.asyncio.client import connect

    static = tmp_path / "static"
    static.mkdir()
    (static / "index.html").write_text("overlay")
    store = OverlayStore(tmp_path / "overlay.json")
    with socket.socket() as available:
        available.bind(("127.0.0.1", 0))
        port = available.getsockname()[1]
    runtime = OverlayServer(store, Projection(), static)
    await runtime.configure(OverlaySettings(enabled=True, port=port))
    first = runtime.state()["url"]
    try:
        async with connect(
            f"ws://127.0.0.1:{port}/overlay/events", origin=f"http://127.0.0.1:{port}"
        ) as ws:
            await ws.send(json.dumps({"type": "auth", "token": store.token}))
            assert json.loads(await ws.recv())["paused"]
            await runtime.close()
        restored = OverlayStore(tmp_path / "overlay.json")
        runtime = OverlayServer(restored, Projection(), static)
        await runtime.start()
        assert runtime.state()["url"] == first
    finally:
        await runtime.close()


async def test_failed_persistence_preserves_previous_address(tmp_path, monkeypatch):
    static = tmp_path / "static"
    static.mkdir()
    (static / "index.html").write_text("overlay")
    store = OverlayStore(tmp_path / "overlay.json")
    runtime = OverlayServer(store, Projection(), static)
    with socket.socket() as available:
        available.bind(("127.0.0.1", 0))
        port = available.getsockname()[1]
    await runtime.configure(OverlaySettings(enabled=True, port=port))
    original = runtime.state()
    try:

        def fail(_):
            raise OSError("full disk")

        monkeypatch.setattr(store, "save", fail)
        with pytest.raises(AppError):
            await runtime.configure(
                store.settings.model_copy(update={"enabled": False})
            )
        assert runtime.state() == original
    finally:
        await runtime.close()
