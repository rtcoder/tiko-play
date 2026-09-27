from dataclasses import dataclass
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from src.core.keys import get_keys
from src.core.users import allowed_users


class AppError(Exception):
    def __init__(self, code: str, message: str, field_errors=None, status=400):
        super().__init__(message)
        self.code, self.message, self.field_errors, self.status = (
            code,
            message,
            field_errors or {},
            status,
        )

    def as_dict(self):
        return dict(
            code=self.code, message=self.message, field_errors=self.field_errors
        )


class Mapping(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=True)
    id: str = Field(min_length=1)
    trigger: str
    keys: tuple[str, ...]

    @field_validator("trigger")
    @classmethod
    def trigger_valid(cls, value):
        value = value.strip().lower()
        if not value:
            raise ValueError("Komentarz nie może być pusty")
        return value

    @field_validator("keys")
    @classmethod
    def keys_valid(cls, value):
        if not value or any(k not in get_keys() for k in value):
            raise ValueError("Wybierz poprawne klawisze")
        return value


Platform = Literal["tiktok", "twitch"]


class ChannelConfig(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=True)
    channel: str = ""
    target_user: str = ""

    @field_validator("target_user")
    @classmethod
    def users_valid(cls, value):
        if value.strip() and not allowed_users(value):
            raise ValueError("Wpisz nicki użytkowników lub wyczyść pole, aby dopuścić wszystkich")
        return value

    @field_validator("channel")
    @classmethod
    def streamer_valid(cls, value):
        return value.strip().removeprefix("@")


class TwitchChannelConfig(ChannelConfig):
    @field_validator("channel")
    @classmethod
    def twitch_channel(cls, value):
        import re
        value = value.lower()
        if value and not re.fullmatch(r"[a-z0-9_]+", value):
            raise ValueError("Podaj login kanału Twitch, bez adresu URL")
        return value


class AppConfig(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=True)
    version: Literal[3] = 3
    platform: Platform = "tiktok"
    tiktok: ChannelConfig = Field(default_factory=ChannelConfig)
    twitch: TwitchChannelConfig = Field(default_factory=TwitchChannelConfig)
    mappings: tuple[Mapping, ...] = ()
    show_logs: bool = False
    countdown_enabled: bool = True

    def active_source(self) -> ChannelConfig:
        return self.tiktok if self.platform == "tiktok" else self.twitch

    @model_validator(mode="after")
    def unique(self):
        for attr in ("id", "trigger"):
            values = [getattr(m, attr) for m in self.mappings]
            if len(set(values)) != len(values):
                raise ValueError(f"Powtórzone {attr} mapowania")
        return self


@dataclass(frozen=True)
class ConfigSnapshot:
    config: AppConfig
    revision: int


class ListenerState(BaseModel):
    status: str = "stopped"
    output: str = "disabled"
    active_config_revision: int | None = None
    error: dict | None = None
    generation: int = 0
