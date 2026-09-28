import json

from fastapi import APIRouter, Request

from src.core.models import AppError
from src.core.profiles import MAX_IMPORT_BYTES, export_profile, import_profile
from src.core.profile_templates import get_profile_templates


def create_profiles_router(store):
    router = APIRouter()

    @router.get("/api/profile-templates")
    async def templates():
        return get_profile_templates()

    @router.get("/api/profiles/{profile_id}/export")
    async def export(profile_id: str):
        profile = next(
            (p for p in store.snapshot().config.profiles if p.id == profile_id), None
        )
        if profile is None:
            raise AppError("profile_not_found", "Nie znaleziono profilu.", status=404)
        return export_profile(profile)

    @router.post("/api/profiles/import-preview")
    async def preview(request: Request):
        raw = bytearray()
        async for chunk in request.stream():
            if len(raw) + len(chunk) > MAX_IMPORT_BYTES:
                raise AppError(
                    "profile_too_large", "Plik profilu przekracza 1 MiB.", status=413
                )
            raw.extend(chunk)
        try:
            payload = json.loads(raw)
        except (ValueError, UnicodeError) as exc:
            raise AppError(
                "profile_import_error", "Niepoprawny plik JSON profilu.", status=422
            ) from exc
        return import_profile(payload).model_dump(mode="json")

    return router
