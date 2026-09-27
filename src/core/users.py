"""Parse the backward-compatible target_user configuration field."""
import re


def allowed_users(value: str) -> frozenset[str]:
    return frozenset(
        user for item in re.split(r"[,;\r\n]", value)
        if (user := item.strip().removeprefix("@").strip())
    )
