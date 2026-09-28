"""Translate application-owned text only; never comments, mappings or identifiers."""

import json
from pathlib import Path

_EN = json.loads(
    (Path(__file__).resolve().parent.parent / "locales" / "en.json").read_text(
        encoding="utf-8"
    )
)


def translate(text, language="pl"):
    return _EN.get(text, text) if language == "en" else text
