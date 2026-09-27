import asyncio
import json
import socket
from contextlib import suppress
import httpx
import pytest
import uvicorn
from websockets.asyncio.client import connect
from src.api.app import create_app
from src.api.session import SessionManager
from src.core.config_store import ConfigStore
from src.core.events import EventBus
from src.core.keyboard import KeyboardExecutor
from src.core.listener_service import ListenerService


async def test_network_flow_continues_without_browser(tmp_path, twitch_auth):
    calls = []

    class Port:
        def execute(self, keys):
            calls.append(keys)

    class Client:
        async def connect(self, cb):
            self.cb = cb
            self.task = asyncio.create_task(asyncio.Event().wait())
            return self.task

        async def disconnect(self):
            self.task.cancel()

    client = Client()
    store = ConfigStore(tmp_path / "config.json")
    await store.load()
    static = tmp_path / "static"
    static.mkdir()
    (static / "index.html").write_text("panel")
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    sock.listen(128)
    sock.setblocking(False)
    origin = f"http://127.0.0.1:{sock.getsockname()[1]}"
    bus = EventBus("integration")
    sessions = SessionManager("integration", origin)
    keyboard = KeyboardExecutor(Port())
    listener = ListenerService(lambda _: client, keyboard, bus)
    server = uvicorn.Server(
        uvicorn.Config(
            create_app(store, listener, bus, sessions, static, twitch_auth=twitch_auth),
            log_config=None,
            access_log=False,
            ws="websockets-sansio",
        )
    )
    task = asyncio.create_task(server.serve(sockets=[sock]))
    try:
        for _ in range(100):
            if server.started:
                break
            await asyncio.sleep(0.01)
        async with httpx.AsyncClient(base_url=origin, trust_env=False) as http:
            session = (
                await http.post(
                    "/api/session",
                    json={"token": sessions.issue_launch_token()},
                    headers={"Origin": origin},
                )
            ).json()
            headers = {"Origin": origin, "X-CSRF-Token": session["csrf_token"]}
            config = {
                "version": 3,
                "tiktok": {"channel": "test"},
                "countdown_enabled": False,
                "mappings": [
                    {"id": "1", "trigger": "x", "keys": ["ctrl", "a"]},
                    {"id": "2", "trigger": "y", "keys": ["left"]},
                ],
            }
            response = await http.put(
                "/api/config",
                json={"config": config, "expected_revision": 1},
                headers=headers,
            )
            assert response.status_code == 200
            assert (
                await http.post(
                    "/api/listener/start",
                    json={"expected_revision": 2},
                    headers=headers,
                )
            ).status_code == 202
            for _ in range(100):
                if listener.state().output == "enabled":
                    break
                await asyncio.sleep(0.01)
            cookie = "; ".join(f"{k}={v}" for k, v in http.cookies.items())
            async with connect(
                origin.replace("http:", "ws:") + "/api/events",
                origin=origin,
                additional_headers={"Cookie": cookie},
            ) as ws:
                assert json.loads(await ws.recv())["type"] == "snapshot"
                await client.cb("viewer", "x")
            await client.cb("viewer", "y")
            for _ in range(100):
                if len(calls) == 2:
                    break
                await asyncio.sleep(0.01)
            assert calls == [("ctrl", "a"), ("left",)]
            async with connect(
                origin.replace("http:", "ws:") + "/api/events",
                origin=origin,
                additional_headers={"Cookie": cookie},
            ) as ws:
                assert json.loads(await ws.recv())["state"]["status"] == "connected"
            assert (
                await http.post("/api/listener/stop", headers=headers)
            ).status_code == 202
            await client.cb("viewer", "x")
            await asyncio.sleep(0.02)
            assert len(calls) == 2
    finally:
        server.should_exit = True
        await asyncio.wait_for(task, 5)
        await keyboard.close(1)
        sock.close()
