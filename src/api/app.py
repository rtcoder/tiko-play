import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, WebSocket
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src.api.events import stream_events
from src.api.twitch import create_twitch_router
from src.api.youtube import create_youtube_router
from src.core.keys import get_keys
from src.core.models import AppConfig, AppError
from src.core.preferences import Preferences, PreferencesStore
from src.core.presets import get_presets


class ConfigWrite(BaseModel):
    config: AppConfig
    expected_revision: int = Field(ge=1)


class Revision(BaseModel):
    expected_revision: int = Field(ge=1)


class Token(BaseModel):
    token: str = Field(max_length=256)


def create_app(
    store,
    listener,
    events,
    sessions,
    static_dir: Path,
    *,
    twitch_auth,
    youtube_keys=None,
    preferences=None,
    on_language_changed=None,
):
    preferences = preferences or PreferencesStore(
        store.path.with_name("preferences.json")
    )
    tasks = set()

    def spawn(coro):
        task = asyncio.create_task(coro)
        tasks.add(task)
        task.add_done_callback(tasks.discard)

    @asynccontextmanager
    async def lifespan(app):
        yield
        for sub in tuple(events.subscribers):
            events.unsubscribe(sub)
        await listener.stop()
        await twitch_auth.close()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)

    def state():
        return {
            **listener.state().model_dump(),
            "instance_id": events.instance_id,
            "language": preferences.effective_language,
            "config_revision": store._snapshot.revision if store._snapshot else None,
            "config_error": store.error.as_dict() if store.error else None,
            "recovery_data": store.recovery_data if store.error else None,
        }

    def config_result(snap):
        return {
            "config": snap.config.model_dump(mode="json"),
            "config_revision": snap.revision,
        }

    @app.exception_handler(AppError)
    async def app_error(request, exc):
        return JSONResponse(exc.as_dict(), status_code=exc.status)

    @app.exception_handler(RequestValidationError)
    async def validation(request, exc):
        return JSONResponse(
            {
                "code": "validation_error",
                "message": "Popraw zaznaczone pola.",
                "field_errors": {
                    ".".join(map(str, e["loc"])): e["msg"] for e in exc.errors()
                },
            },
            status_code=422,
        )

    @app.middleware("http")
    async def security(request: Request, call_next):
        try:
            sessions.validate_host(request.headers.get("host"))
            if request.method not in ("GET", "HEAD", "OPTIONS"):
                sessions.validate_origin(request.headers.get("origin"))
            if (
                request.url.path.startswith("/api/")
                and request.url.path != "/api/health"
            ):
                if not (
                    request.url.path == "/api/session" and request.method == "POST"
                ):
                    session = sessions.authenticate(
                        request.cookies.get(sessions.cookie_name)
                    )
                    request.state.session = session
                    if request.method not in ("GET", "HEAD", "OPTIONS"):
                        sessions.validate_csrf(
                            session, request.headers.get("x-csrf-token")
                        )
            response = await call_next(request)
        except AppError as exc:
            response = JSONResponse(exc.as_dict(), status_code=exc.status)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/api/health")
    async def health():
        return {"ready": True}

    @app.post("/api/session")
    async def exchange(body: Token, request: Request):
        session = sessions.exchange(
            body.token, request.cookies.get(sessions.cookie_name)
        )
        response = JSONResponse({"csrf_token": session.csrf_token})
        response.set_cookie(
            sessions.cookie_name,
            session.id,
            httponly=True,
            samesite="strict",
            path="/api",
        )
        return response

    @app.get("/api/session")
    async def current_session(request: Request):
        return {"csrf_token": request.state.session.csrf_token}

    @app.get("/api/state")
    async def get_state():
        return state()

    @app.get("/api/preferences")
    async def get_preferences():
        return {"language": preferences.effective_language}

    @app.put("/api/preferences")
    async def put_preferences(body: Preferences):
        try:
            preferences.save(body.language)
        except OSError as exc:
            raise AppError(
                "preferences_error",
                "Nie można zapisać języka. Sprawdź uprawnienia katalogu danych.",
                status=500,
            ) from exc
        if on_language_changed:
            on_language_changed(body.language)
        result = {"language": body.language}
        events.publish("preferences_changed", result)
        return result

    @app.get("/api/config")
    async def get_config():
        return config_result(store.snapshot())

    @app.put("/api/config")
    async def put_config(body: ConfigWrite):
        snap = await store.save(body.config, body.expected_revision)
        events.publish("config_changed", {"config_revision": snap.revision})
        return config_result(snap)

    @app.post("/api/config/repair")
    async def repair(body: AppConfig):
        snap = await store.repair(body)
        events.publish("config_changed", {"config_revision": snap.revision})
        return config_result(snap)

    @app.get("/api/presets")
    async def presets():
        return get_presets()

    @app.get("/api/keys")
    async def keys():
        return get_keys()

    @app.post("/api/listener/start", status_code=202)
    async def start(body: Revision):
        stop_revision = listener.stop_revision
        snap = store.snapshot()
        if body.expected_revision != snap.revision:
            raise AppError(
                "revision_conflict", "Odśwież konfigurację przed startem.", status=409
            )
        if not snap.config.active_source().channel:
            raise AppError("streamer_required", "Podaj nick kanału", status=422)
        if (
            snap.config.platform == "twitch"
            and twitch_auth.state()["status"] != "connected"
        ):
            raise AppError(
                "twitch_auth_required",
                "Połącz konto Twitch przed rozpoczęciem nasłuchu.",
                status=409,
            )
        if snap.config.platform == "youtube":
            if youtube_keys is None:
                raise AppError(
                    "youtube_key_required", "Zapisz klucz YouTube Data API.", status=409
                )
            async with youtube_keys.lock:
                if not await youtube_keys.load():
                    raise AppError(
                        "youtube_key_required",
                        "Zapisz klucz YouTube Data API.",
                        status=409,
                    )
                listener.start(snap, expected_stop_revision=stop_revision)
        else:
            listener.start(snap)
        return state()

    @app.post("/api/listener/stop", status_code=202)
    async def stop():
        listener.request_stop()
        spawn(listener.stop())
        return state()

    @app.get("/api/events/recent")
    async def recent():
        return events.recent()

    @app.websocket("/api/events")
    async def websocket(ws: WebSocket):
        try:
            sessions.validate_host(ws.headers.get("host"))
            sessions.validate_origin(ws.headers.get("origin"))
            sessions.authenticate(ws.cookies.get(sessions.cookie_name))
        except AppError:
            await ws.close(code=1008)
            return
        await stream_events(ws, events, state)

    app.include_router(create_twitch_router(twitch_auth))
    if youtube_keys is not None:
        app.include_router(create_youtube_router(youtube_keys, listener))

    @app.api_route(
        "/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"]
    )
    async def missing(path: str):
        raise AppError("not_found", "Nie znaleziono zasobu", status=404)

    if not (static_dir / "index.html").is_file():
        raise RuntimeError("Brak panelu. Wykonaj build frontendu.")

    @app.get("/", response_class=HTMLResponse)
    async def index():
        html = (static_dir / "index.html").read_text(encoding="utf-8")
        return html.replace(
            '<html lang="pl">', f'<html lang="{preferences.effective_language}">'
        )

    app.mount("/", StaticFiles(directory=static_dir, html=True), name="panel")
    return app
