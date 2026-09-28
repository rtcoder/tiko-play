"""Shared build version and release preflight (stdlib only)."""

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent


def read_version(root: Path = ROOT) -> str:
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)", version):
        raise ValueError("VERSION musi mieć format <major>.<minor> bez prefiksu v")
    return version


def validate_release(root: Path, tag: str) -> Path:
    if tag != f"v{read_version(root)}":
        raise ValueError("Tag wydania musi odpowiadać VERSION: v<major>.<minor>")
    notes = root / "releases" / f"{tag}.md"
    if not notes.is_file() or not any(
        line.strip() and not line.lstrip().startswith("#")
        for line in notes.read_text(encoding="utf-8").splitlines()
    ):
        raise ValueError(f"Brak opisu zmian wydania w {notes}")
    return notes


if __name__ == "__main__":
    if len(sys.argv) > 1:
        validate_release(ROOT, sys.argv[1])
    print(read_version())
