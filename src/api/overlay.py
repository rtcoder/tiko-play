"""Dedicated read-only listener. Deliberately does not mount the operator API."""

import asyncio
import json
import secrets
from contextlib import suppress
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import APIRouter, FastAPI, Request, WebSocket
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.websockets import WebSocketDisconnect

from src.core.overlay import OverlaySettings


async def close_socket(ws):
    # A blocked transport can also block a close frame. Returning from ASGI
    # lets uvicorn close the transport even when the peer never reads again.
    with suppress(TimeoutError, RuntimeError, WebSocketDisconnect):
        await asyncio.wait_for(ws.close(code=1008), 0.2)


def create_overlay_router(runtime):
    router = APIRouter()

    @router.get("/api/overlay")
    async def state():
        return runtime.state()

    @router.put("/api/overlay")
    async def configure(settings: OverlaySettings):
        await runtime.configure(settings)
        return runtime.state()

    @router.post("/api/overlay/rotate")
    async def rotate():
        await runtime.rotate()
        return runtime.state()

    return router


def create_overlay_app(
    store, projection, static_dir: Path, origin: str, *, auth_timeout=5
):
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    host = urlsplit(origin).netloc
    connections = set()

    @app.middleware("http")
    async def security(request: Request, call_next):
        if request.headers.get("host") != host:
            return Response(status_code=403)
        if request.method not in ("GET", "HEAD"):
            return Response(status_code=405)
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
        )
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.get("/overlay", response_class=HTMLResponse)
    async def page():
        return (static_dir / "index.html").read_text(encoding="utf-8")

    @app.websocket("/overlay/events")
    async def stream(ws: WebSocket):
        if (
            ws.headers.get("host") != host
            or ws.headers.get("origin") != origin
            or len(connections) >= 16
        ):
            await close_socket(ws)
            return
        connections.add(ws)
        tasks = []
        try:
            await ws.accept()
            raw = await asyncio.wait_for(ws.receive_text(), auth_timeout)
            if len(raw) > 1024:
                await close_socket(ws)
                return
            auth = json.loads(raw)
            token = auth.get("token") if isinstance(auth, dict) else None
            if (
                not isinstance(token, str)
                or not token.isascii()
                or auth.get("type") != "auth"
                or not secrets.compare_digest(token, store.token)
            ):
                await close_socket(ws)
                return

            async def send():
                sequence = None
                while secrets.compare_digest(token, store.token):
                    snap = projection.snapshot()
                    if snap["sequence"] != sequence:
                        await asyncio.wait_for(ws.send_json(snap), 2)
                        sequence = snap["sequence"]
                    await asyncio.sleep(0.2)
                await close_socket(ws)

            async def receive():
                while True:
                    raw = await asyncio.wait_for(ws.receive_text(), 45)
                    if len(raw) > 1024 or json.loads(raw) != {"type": "ping"}:
                        await close_socket(ws)
                        return

            tasks = [asyncio.create_task(send()), asyncio.create_task(receive())]
            done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                task.result()
        except (ValueError, TimeoutError, KeyError, WebSocketDisconnect):
            with suppress(RuntimeError, WebSocketDisconnect):
                await close_socket(ws)
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            connections.discard(ws)

    if (static_dir / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=static_dir / "assets"))
    return app
