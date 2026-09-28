"""Portable profile format. Never serialize credentials, filters or arbitrary extras."""

import json
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from src.core.models import AppError, GameProfile, Mapping

MAX_IMPORT_BYTES = 1024 * 1024


class PortableMapping(BaseModel):
    model_config = ConfigDict(extra="forbid")
    trigger: str
    keys: tuple[str, ...]


class PortableProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    format_version: int
    name: str
    mappings: tuple[PortableMapping, ...] = Field(max_length=500)


def export_profile(profile: GameProfile) -> dict:
    return {
        "format_version": 1,
        "name": profile.name,
        "mappings": [
            {"trigger": m.trigger, "keys": list(m.keys)} for m in profile.mappings
        ],
    }


def import_profile(payload: dict) -> GameProfile:
    try:
        if (
            len(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
            > MAX_IMPORT_BYTES
        ):
            raise ValueError("size")
        portable = PortableProfile.model_validate(payload)
        if portable.format_version != 1:
            raise ValueError("version")
        return GameProfile(
            name=portable.name,
            mappings=tuple(
                Mapping(id=str(uuid4()), trigger=m.trigger, keys=m.keys)
                for m in portable.mappings
            ),
        )
    except (ValueError, TypeError, ValidationError) as exc:
        raise AppError(
            "profile_import_error",
            "Niepoprawny profil. Obsługiwany format: 1, maksymalnie 1 MiB i 500 mapowań.",
            status=422,
        ) from exc
