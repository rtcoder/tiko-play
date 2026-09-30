"""Lifecycle of the optional fixed-port, loopback-only overlay server."""

import asyncio
import socket

import uvicorn

from src.api.overlay import create_overlay_app
from src.core.models import AppError


class OverlayServer:
    def __init__(self, store, projection, static_dir):
        self.store = store
        self.projection = projection
        self.static_dir = static_dir
        self.server = None
        self.task = None
        self.socket = None
        self.port = None
        self.error = store.error
        self.lock = asyncio.Lock()

    def state(self):
        running = (
            self.server is not None and self.server.started and not self.task.done()
        )
        return {
            "settings": self.store.settings.model_dump(),
            "running": running,
            "url": f"http://127.0.0.1:{self.port}/overlay#token={self.store.token}"
            if running
            else None,
            "error": self.error or self.store.error,
        }

    async def start(self):
        if self.store.error:
            return
        try:
            await self.configure(self.store.settings, persist=False)
        except AppError as exc:
            self.error = exc.message

    async def _stop(self, server, task, sock):
        if server:
            server.should_exit = True
        if task:
            try:
                await asyncio.wait_for(asyncio.shield(task), 3)
            except TimeoutError:
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
        if sock:
            sock.close()

    async def configure(self, settings, *, persist=True):
        async with self.lock:
            replacement = None
            running = (
                self.server is not None
                and self.task is not None
                and not self.task.done()
            )
            if settings.enabled and (not running or settings.port != self.port):
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    sock.bind(("127.0.0.1", settings.port))
                    sock.listen(32)
                    sock.setblocking(False)
                except OSError as exc:
                    sock.close()
                    raise AppError(
                        "overlay_port_busy",
                        "Port nakładki jest zajęty lub niedostępny. Wybierz inny port.",
                        status=409,
                    ) from exc
                server = uvicorn.Server(
                    uvicorn.Config(
                        create_overlay_app(
                            self.store,
                            self.projection,
                            self.static_dir,
                            f"http://127.0.0.1:{settings.port}",
                        ),
                        host="127.0.0.1",
                        port=settings.port,
                        log_config=None,
                        access_log=False,
                        ws="websockets-sansio",
                        ws_max_size=2048,
                        timeout_graceful_shutdown=1,
                    )
                )
                task = asyncio.create_task(server.serve(sockets=[sock]))
                replacement = server, task, sock
                try:
                    async with asyncio.timeout(5):
                        while not server.started:
                            if task.done():
                                await task
                                raise RuntimeError("Overlay stopped before ready")
                            await asyncio.sleep(0.01)
                except BaseException:
                    await self._stop(*replacement)
                    raise
            try:
                if persist:
                    self.store.save(settings)
            except OSError as exc:
                if replacement:
                    await self._stop(*replacement)
                raise AppError(
                    "overlay_save_failed",
                    "Nie można zapisać ustawień nakładki. Sprawdź uprawnienia katalogu danych.",
                    status=500,
                ) from exc
            if replacement or not settings.enabled:
                old = self.server, self.task, self.socket
                self.server, self.task, self.socket = replacement or (None, None, None)
                self.port = settings.port if replacement else None
                await self._stop(*old)
            self.error = None

    async def rotate(self):
        async with self.lock:
            try:
                self.store.rotate()
            except OSError as exc:
                raise AppError(
                    "overlay_save_failed",
                    "Nie można zapisać ustawień nakładki. Sprawdź uprawnienia katalogu danych.",
                    status=500,
                ) from exc
            self.error = None

    async def close(self):
        async with self.lock:
            old = self.server, self.task, self.socket
            self.server = self.task = self.socket = None
            self.port = None
            await self._stop(*old)
