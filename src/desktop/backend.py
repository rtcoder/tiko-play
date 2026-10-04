import asyncio
import concurrent.futures
import socket
import threading
import time
from uuid import uuid4

import httpx
import uvicorn
from PySide6.QtCore import QObject, Signal
from websockets.asyncio.client import connect as websocket_connect

from src.adapters.chat import ChatAdapterFactory
from src.adapters.focus import focus_port
from src.adapters.pyautogui_keyboard import PyAutoGUIKeyboard
from src.adapters.twitch_auth import TwitchAuthService
from src.adapters.twitch_credentials import NativeCredentialStore
from src.adapters.youtube_key import YouTubeKeyStore
from src.api.app import create_app
from src.api.session import SessionManager
from src.core.config_store import ConfigStore
from src.core.diagnostics import configure_diagnostics
from src.core.events import EventBus
from src.core.keyboard import KeyboardExecutor
from src.core.listener_service import ListenerService
from src.core.models import AppError
from src.core.output_guard import OutputGuard
from src.core.overlay import OverlayProjection, OverlayStore
from src.core.preferences import PreferencesStore
from src.desktop.overlay_server import OverlayServer
from src.twitch_settings import get_twitch_client_id


class BackendHost(QObject):
    ready = Signal(str)
    failed = Signal(str)
    state_changed = Signal(dict)
    language_changed = Signal(str)

    def __init__(self, data_dir, static_dir, *, preferences=None, hotkey=None):
        super().__init__()
        self.hotkey = hotkey
        self.preferences = preferences or PreferencesStore(
            data_dir / "preferences.json"
        )
        self.data_dir = data_dir
        self.static_dir = static_dir
        self.origin = None
        self.loop = None
        self.server = None
        self.listener = None
        self.overlay = None
        self.sessions = None
        self._closing = False
        self._finished = concurrent.futures.Future()
        self.thread = threading.Thread(
            target=self._thread_main, name="TikoPlay-backend", daemon=True
        )

    @property
    def language(self):
        return self.preferences.effective_language

    def start(self):
        self.thread.start()

    def _thread_main(self):
        try:
            asyncio.run(self._run())
        except Exception:
            self.failed.emit(
                "Nie udało się uruchomić lokalnego panelu. Sprawdź instalację i uprawnienia do katalogu danych."
            )
            if hasattr(self, "logger"):
                self.logger.error("Backend startup/runtime failure", exc_info=True)
        finally:
            self.loop = None
            if not self._finished.done():
                self._finished.set_result(None)

    async def _run(self):
        self.loop = asyncio.get_running_loop()
        self.logger = configure_diagnostics(self.data_dir / "logs")
        if not (self.static_dir / "index.html").is_file():
            raise RuntimeError("Missing frontend assets")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        keyboard = None
        server_task = None
        watch_task = None
        restore_task = None
        auth = None
        twitch_http = None
        try:
            sock.bind(("127.0.0.1", 0))
            sock.listen(128)
            sock.setblocking(False)
            self.origin = f"http://127.0.0.1:{sock.getsockname()[1]}"
            bus = EventBus(uuid4().hex)
            self.sessions = SessionManager(bus.instance_id, self.origin)
            store = ConfigStore(self.data_dir / "config.json")
            try:
                await store.load()
            except AppError:
                pass

            def report(kind, payload):
                if self.loop and not self.loop.is_closed():
                    self.loop.call_soon_threadsafe(
                        self.listener.keyboard_result, kind, payload
                    )

            guard = OutputGuard(focus_port())
            keyboard = KeyboardExecutor(
                PyAutoGUIKeyboard(), report=report, output_check=guard.can_execute
            )
            twitch_http = httpx.AsyncClient(
                timeout=10, follow_redirects=False, trust_env=False
            )
            auth = TwitchAuthService(
                get_twitch_client_id(), NativeCredentialStore(), twitch_http, bus
            )
            youtube_keys = YouTubeKeyStore()
            self.listener = ListenerService(
                ChatAdapterFactory(
                    auth, twitch_http, websocket_connect, youtube_keys=youtube_keys
                ),
                keyboard,
                bus,
                guard=guard,
            )
            overlay_store = OverlayStore(self.data_dir / "overlay.json")
            self.overlay = OverlayServer(
                overlay_store,
                OverlayProjection(
                    self.listener, store, overlay_store, lambda: self.language
                ),
                self.static_dir,
            )
            await self.overlay.start()
            auth.subscribe_invalidated(self.listener.authorization_lost)
            restore_task = asyncio.create_task(auth.restore())
            app = create_app(
                store,
                self.listener,
                bus,
                self.sessions,
                self.static_dir,
                twitch_auth=auth,
                youtube_keys=youtube_keys,
                preferences=self.preferences,
                on_language_changed=self.language_changed.emit,
                overlay=self.overlay,
                output_guard=guard,
                emergency_hotkey=self.hotkey,
            )
            config = uvicorn.Config(
                app,
                host="127.0.0.1",
                port=sock.getsockname()[1],
                workers=1,
                log_config=None,
                access_log=False,
                timeout_graceful_shutdown=2,
                ws="websockets-sansio",
            )
            self.server = uvicorn.Server(config)
            server_task = asyncio.create_task(self.server.serve(sockets=[sock]))
            deadline = time.monotonic() + 15

            async with httpx.AsyncClient(trust_env=False) as client:
                while True:
                    if self._closing:
                        self.server.should_exit = True
                        return
                    if server_task.done():
                        await server_task
                        raise RuntimeError("Server exited before ready")
                    if time.monotonic() > deadline:
                        raise TimeoutError("Readiness timeout")
                    if self.server.started:
                        try:
                            health = await client.get(
                                self.origin + "/api/health", timeout=0.5
                            )
                            page = await client.get(self.origin + "/", timeout=0.5)
                            if health.status_code == 200 and page.status_code == 200:
                                break
                        except httpx.HTTPError:
                            pass
                    await asyncio.sleep(0.03)
            self.ready.emit(self.origin)
            sub = bus.subscribe()

            async def watch():
                while not sub.closed:
                    event = await sub.queue.get()
                    if event["type"] == "status":
                        self.state_changed.emit(event["payload"])

            watch_task = asyncio.create_task(watch())
            await server_task
            if not self._closing:
                raise RuntimeError("Server stopped unexpectedly")
        finally:
            if self.listener:
                await self.listener.stop()
            if auth:
                await auth.close()
            if restore_task:
                restore_task.cancel()
                await asyncio.gather(restore_task, return_exceptions=True)
            if twitch_http:
                await twitch_http.aclose()
            if keyboard:
                await keyboard.close(1)
            if self.server:
                self.server.should_exit = True
            if server_task and not server_task.done():
                try:
                    await asyncio.wait_for(server_task, 2)
                except (TimeoutError, asyncio.CancelledError):
                    pass
            if watch_task:
                watch_task.cancel()
                await asyncio.gather(watch_task, return_exceptions=True)
            sock.close()
            if self.overlay:
                await self.overlay.close()

    def open_url(self):
        async def issue():
            return self.origin + "/#token=" + self.sessions.issue_launch_token()

        if not self.loop:
            raise RuntimeError("Backend nie jest gotowy")
        return asyncio.run_coroutine_threadsafe(issue(), self.loop)

    def request_stop(self):
        if self.loop and self.listener:
            asyncio.run_coroutine_threadsafe(self.listener.stop(), self.loop)

    def shutdown(self):
        self._closing = True

        def stop():
            if self.listener:
                self.listener.request_stop()
            if self.server:
                self.server.should_exit = True

        if self.loop:
            self.loop.call_soon_threadsafe(stop)
        return self._finished
