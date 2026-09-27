from fastapi import APIRouter
from pydantic import BaseModel, Field, field_validator

from src.core.models import AppError


class KeyWrite(BaseModel):
    key: str = Field(min_length=1, max_length=256, repr=False)

    @field_validator("key")
    @classmethod
    def valid(cls, value):
        value = value.strip()
        if not value or any(
            c.isspace() or not c.isascii() or not c.isprintable() for c in value
        ):
            raise ValueError("Wpisz poprawny klucz API, bez białych znaków")
        return value


def create_youtube_router(store, listener):
    router = APIRouter(prefix="/api/youtube/key")

    def ensure_idle():
        state = listener.state()
        if state.active_platform == "youtube" and state.status in (
            "connecting",
            "connected",
            "stopping",
        ):
            raise AppError(
                "listener_busy",
                "Zatrzymaj nasłuch YouTube przed zmianą klucza.",
                status=409,
            )

    @router.get("")
    async def state():
        async with store.lock:
            return {"configured": bool(await store.load())}

    @router.put("")
    async def save(body: KeyWrite):
        async with store.lock:
            ensure_idle()
            await store.save(body.key)
            return {"configured": True}

    @router.delete("")
    async def delete():
        async with store.lock:
            ensure_idle()
            await store.delete()
            return {"configured": False}

    return router
