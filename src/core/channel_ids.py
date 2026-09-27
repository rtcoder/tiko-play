"""Validate identifiers without fetching user-supplied URLs."""

import re
from urllib.parse import parse_qs, urlsplit


def youtube_video_id(value: str) -> str:
    value = value.strip()
    if not value or re.fullmatch(r"[A-Za-z0-9_-]{11}", value):
        return value
    try:
        url = urlsplit(value)
        if (
            url.scheme != "https"
            or url.username
            or url.password
            or url.port not in (None, 443)
        ):
            raise ValueError()
        if url.hostname == "youtu.be":
            candidate = url.path.strip("/")
        elif url.hostname in ("youtube.com", "www.youtube.com", "m.youtube.com"):
            if url.path == "/watch":
                candidate = parse_qs(url.query).get("v", [""])[0]
            elif url.path.startswith(("/live/", "/shorts/")):
                candidate = url.path.split("/")[2]
            else:
                raise ValueError()
        else:
            raise ValueError()
        if re.fullmatch(r"[A-Za-z0-9_-]{11}", candidate):
            return candidate
    except (ValueError, IndexError):
        pass
    raise ValueError("Podaj link do transmisji YouTube lub jej 11-znakowe ID")
