"""Persistent presentation settings and an explicit public, read-only projection."""

import json
import os
import secrets
import tempfile
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class OverlaySettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    enabled: bool = False
    port: int = Field(default=18765, strict=True, ge=1024, le=65535)
    show_commands: bool = True
    show_last_action: bool = True
    show_actor: bool = False
    show_status: bool = True
    font_size: int = Field(default=24, strict=True, ge=16, le=48)
    accent: str = Field(default="#7c83ff", pattern=r"^#[0-9a-fA-F]{6}$")


class OverlayDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    token: str = Field(min_length=43, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")
    settings: OverlaySettings = Field(default_factory=OverlaySettings)


class OverlayStore:
    def __init__(self, path: Path):
        self.path = path
        self.error = None
        self.document = OverlayDocument(token=secrets.token_urlsafe(32))
        try:
            self.document = OverlayDocument.model_validate_json(path.read_bytes())
            os.chmod(path, 0o600)
        except FileNotFoundError:
            try:
                self._write(self.document)
            except OSError:
                self.error = "Nie można zapisać ustawień nakładki. Sprawdź uprawnienia katalogu danych."
        except (ValueError, OSError):
            # Never serve with an invalid or unprotected persisted credential.
            self.document = OverlayDocument(token=secrets.token_urlsafe(32))
            self.error = (
                "Nie można odczytać ustawień nakładki. Zapisz je ponownie w panelu."
            )

    @property
    def settings(self):
        return self.document.settings

    @property
    def token(self):
        return self.document.token

    def _write(self, document):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(
            prefix=".overlay-", suffix=".tmp", dir=self.path.parent
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(document.model_dump(mode="json"), f)
                f.flush()
                os.fsync(f.fileno())
            os.replace(name, self.path)
        finally:
            if os.path.exists(name):
                os.unlink(name)
        self.document = document
        self.error = None

    def save(self, settings: OverlaySettings):
        self._write(OverlayDocument(token=self.token, settings=settings))

    def rotate(self):
        self._write(
            OverlayDocument(token=secrets.token_urlsafe(32), settings=self.settings)
        )


class OverlayProjection:
    def __init__(self, listener, config, store, language):
        self.listener = listener
        self.config = config
        self.store = store
        self.language = language
        self.sequence = 0
        self.previous = None

    def snapshot(self):
        state = self.listener.state()
        settings = self.store.settings
        snap = (
            self.listener.active_snapshot
            if state.status in ("connecting", "connected", "stopping")
            else self.config._snapshot
        )
        commands = []
        if snap and settings.show_commands:
            commands = [
                {"comment": m.trigger, "action": m.action.model_dump(mode="json")}
                for m in snap.config.mappings
            ]
        last = self.listener.last_executed
        action = None
        if settings.show_last_action and last:
            action = {
                "id": last["id"],
                "comment": last.get("comment", ""),
                "action": last["action"],
            }
            if settings.show_actor:
                action["actor"] = last.get("actor_id", "")
        public = {
            "schema_version": 1,
            "mode": "direct",
            "paused": state.output != "enabled",
            "commands": commands,
            "last_action": action,
            "language": self.language(),
            "presentation": {
                k: v
                for k, v in settings.model_dump().items()
                if k not in ("enabled", "port")
            },
        }
        if public != self.previous:
            self.sequence += 1
            self.previous = public
        return {**public, "sequence": self.sequence}
