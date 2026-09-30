"""Simulation reads a saved snapshot; it has no access to the live listener."""

import asyncio

from fastapi import APIRouter, Request
from pydantic import ValidationError

from src.core.models import AppError
from src.core.simulation import SimulationRequest, simulate

MAX_SIMULATION_BYTES = 4 * 1024 * 1024


def create_simulation_router(store):
    router = APIRouter()

    @router.post("/api/simulation")
    async def run(request: Request):
        raw = bytearray()
        async for chunk in request.stream():
            if len(raw) + len(chunk) > MAX_SIMULATION_BYTES:
                raise AppError(
                    "simulation_too_large", "Scenariusz przekracza 4 MiB.", status=413
                )
            raw.extend(chunk)
        try:
            body = SimulationRequest.model_validate_json(raw)
        except ValidationError as exc:
            raise AppError(
                "invalid_simulation",
                "Scenariusz: 1–1000 wiadomości, czas 0–60000 ms, widz 1–128 znaków, komentarz do 2000 znaków.",
                status=422,
            ) from exc
        snapshot = store.snapshot()
        if body.expected_revision != snapshot.revision:
            raise AppError(
                "simulation_conflict",
                "Ustawienia zmieniły się. Wczytaj zapisane ustawienia i powtórz test.",
                status=409,
            )
        return await asyncio.to_thread(
            simulate,
            snapshot,
            body.messages,
            profile_id=body.profile_id,
            platform=body.platform,
        )

    return router
