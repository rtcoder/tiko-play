"""Application preferences, independent of listener configuration and revisions."""

import json
import os
import tempfile
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict


class Preferences(BaseModel):
    model_config = ConfigDict(extra="forbid")
    language: Literal["pl", "en"]


class PreferencesStore:
    def __init__(self, path: Path):
        self.path = path
        self.language = None
        try:
            self.language = Preferences.model_validate_json(path.read_bytes()).language
        except (OSError, ValueError):
            # Missing/invalid preference asks again; never reset listener settings.
            pass

    @property
    def effective_language(self):
        return self.language or "en"

    def save(self, language):
        value = Preferences(language=language)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(
            prefix=".preferences-", suffix=".tmp", dir=self.path.parent
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(value.model_dump(), f)
                f.flush()
                os.fsync(f.fileno())
            os.replace(name, self.path)
        finally:
            if os.path.exists(name):
                os.unlink(name)
        self.language = value.language
