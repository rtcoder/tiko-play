from dataclasses import dataclass
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.core.actions import ActionDefinition, PressStep
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
    action: ActionDefinition

    @model_validator(mode="before")
    @classmethod
    def legacy_keys(cls, value):
        if isinstance(value, dict) and "keys" in value:
            value = dict(value)
            keys = value.pop("keys")
            if "action" in value:
                raise ValueError("Podaj action albo keys, nie oba pola")
            value["action"] = {"steps": [{"type": "press", "keys": keys}]}
        return value

    @property
    def keys(self):
        if len(self.action.steps) != 1 or not isinstance(
            self.action.steps[0], PressStep
        ):
            raise ValueError("Sekwencja nie jest pojedynczą kombinacją")
        return self.action.steps[0].keys

    @field_validator("trigger")
    @classmethod
    def trigger_valid(cls, value):
        value = value.strip().lower()
        if not value:
            raise ValueError("Komentarz nie może być pusty")
        return value


Platform = Literal["tiktok", "twitch", "youtube", "kick"]


class ChannelConfig(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=True)
    channel: str = ""
    target_user: str = Field(default="", exclude=True)

    @field_validator("target_user")
    @classmethod
    def users_valid(cls, value):
        if value.strip() and not allowed_users(value):
            raise ValueError(
                "Wpisz nicki użytkowników lub wyczyść pole, aby dopuścić wszystkich"
            )
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


class YouTubeChannelConfig(ChannelConfig):
    @field_validator("channel")
    @classmethod
    def video_id(cls, value):
        from src.core.channel_ids import youtube_video_id

        return youtube_video_id(value)


class KickChannelConfig(ChannelConfig):
    chatroom_id: int | None = Field(default=None, gt=0, le=9007199254740991)

    @field_validator("channel")
    @classmethod
    def kick_channel(cls, value):
        import re

        value = value.lower()
        if value and not re.fullmatch(r"[a-z0-9_-]+", value):
            raise ValueError("Podaj login kanału Kick, bez adresu URL")
        return value


class ProfileFilters(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    tiktok: str = ""
    twitch: str = ""
    youtube: str = ""
    kick: str = ""

    @field_validator("tiktok", "twitch", "youtube", "kick")
    @classmethod
    def users_valid(cls, value):
        return ChannelConfig.users_valid(value)


class GameProfile(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=True)
    id: str = Field(default_factory=lambda: str(uuid4()), min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=80)
    mappings: tuple[Mapping, ...] = ()
    filters: ProfileFilters = Field(default_factory=ProfileFilters)

    @field_validator("name", mode="before")
    @classmethod
    def trim_name(cls, value):
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def unique_mappings(self):
        for attr in ("id", "trigger"):
            values = [getattr(m, attr) for m in self.mappings]
            if len(set(values)) != len(values):
                raise ValueError(f"Powtórzone {attr} mapowania")
        return self


class AppConfig(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=True)
    version: Literal[6] = 6
    platform: Platform = "tiktok"
    tiktok: ChannelConfig = Field(default_factory=ChannelConfig)
    twitch: TwitchChannelConfig = Field(default_factory=TwitchChannelConfig)
    youtube: YouTubeChannelConfig = Field(default_factory=YouTubeChannelConfig)
    kick: KickChannelConfig = Field(default_factory=KickChannelConfig)
    profiles: tuple[GameProfile, ...] = Field(min_length=1, max_length=100)
    active_profile_id: str
    show_logs: bool = False
    countdown_enabled: bool = True

    @model_validator(mode="before")
    @classmethod
    def initialize_profile(cls, value):
        if isinstance(value, dict) and "profiles" not in value:
            value = dict(value)
            profile_id = str(uuid4())
            filters = {}
            for platform in ("tiktok", "twitch", "youtube", "kick"):
                source = value.get(platform, {})
                filters[platform] = (
                    source.get("target_user", "")
                    if isinstance(source, dict)
                    else source.target_user
                )
            value["profiles"] = [
                {
                    "id": profile_id,
                    "name": "Domyślny",
                    "mappings": value.pop("mappings", ()),
                    "filters": filters,
                }
            ]
            value.setdefault("active_profile_id", profile_id)
        elif isinstance(value, dict) and "mappings" in value:
            raise ValueError("Mapowania muszą należeć do profilu")
        return value

    @property
    def active_profile(self) -> GameProfile:
        return next(p for p in self.profiles if p.id == self.active_profile_id)

    @property
    def mappings(self) -> tuple[Mapping, ...]:
        return self.active_profile.mappings

    def active_source(self) -> ChannelConfig:
        return getattr(self, self.platform).model_copy(
            update={"target_user": getattr(self.active_profile.filters, self.platform)}
        )

    @model_validator(mode="after")
    def unique(self):
        ids = [p.id for p in self.profiles]
        if len(set(ids)) != len(ids) or self.active_profile_id not in ids:
            raise ValueError("Wybierz istniejący profil o unikalnym ID")
        # Keep the internal channel view compatible; filters are stored only in profiles.
        for platform in ("tiktok", "twitch", "youtube", "kick"):
            object.__setattr__(
                self,
                platform,
                getattr(self, platform).model_copy(
                    update={
                        "target_user": getattr(self.active_profile.filters, platform)
                    }
                ),
            )
        return self


@dataclass(frozen=True)
class ConfigSnapshot:
    config: AppConfig
    revision: int


class ListenerState(BaseModel):
    active_profile_id: str | None = None
    active_profile_name: str | None = None
    active_platform: Platform | None = None
    active_channel: str | None = None
    status: str = "stopped"
    output: str = "disabled"
    active_config_revision: int | None = None
    error: dict | None = None
    generation: int = 0
