"""Immutable, bounded keyboard actions; durations are declared, not real-time guarantees."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.core.keys import get_keys


class KeyStep(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    keys: tuple[str, ...]

    @field_validator("keys")
    @classmethod
    def valid_keys(cls, keys):
        if not keys or any(k not in get_keys() for k in keys):
            raise ValueError("Wybierz poprawne klawisze")
        return keys


class PressStep(KeyStep):
    type: Literal["press"] = "press"


class HoldStep(KeyStep):
    type: Literal["hold"] = "hold"
    duration_ms: int = Field(strict=True, ge=50, le=3000)


class WaitStep(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    type: Literal["wait"] = "wait"
    duration_ms: int = Field(strict=True, ge=10, le=3000)


ActionStep = Annotated[PressStep | HoldStep | WaitStep, Field(discriminator="type")]


class ActionDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    steps: tuple[ActionStep, ...] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def bounded_duration(self):
        if sum(getattr(step, "duration_ms", 0) for step in self.steps) > 10000:
            raise ValueError(
                "Łączny czas przytrzymań i pauz nie może przekraczać 10000 ms"
            )
        return self
