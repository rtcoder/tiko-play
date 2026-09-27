import pytest
from src.core.models import AppConfig
from src.core.matching import Matcher, normalize_trigger
from src.core.presets import get_presets


def test_whole_comment_filter_and_cooldown():
    now = [0.0]
    cfg = AppConfig(
        streamer_id="alice",
        target_user="bob",
        mappings=[{"id": "1", "trigger": " LEWO ", "keys": ["ctrl", "a"]}],
    )
    matcher = Matcher(cfg, lambda: now[0])
    assert normalize_trigger(" LEWO ") == "lewo"
    assert matcher.match("Bob", "lewo") is None
    assert matcher.match("bob", "lewo teraz") is None
    assert matcher.match("bob", " LEWO ") == ("ctrl", "a")
    now[0] = 0.299
    assert matcher.match("bob", "lewo") is None
    now[0] = 0.3
    assert matcher.match("bob", "lewo") == ("ctrl", "a")


def test_presets():
    p = get_presets()
    assert len(p) == 4
    assert [m["keys"] for m in p["Hugo (Polsat 😄)"]] == [
        ["left"],
        ["right"],
        ["up"],
        ["down"],
    ]


@pytest.mark.parametrize(
    "mappings",
    [
        [
            {"id": "1", "trigger": "x", "keys": ["a"]},
            {"id": "2", "trigger": " X ", "keys": ["b"]},
        ],
        [
            {"id": "1", "trigger": "x", "keys": ["a"]},
            {"id": "1", "trigger": "y", "keys": ["b"]},
        ],
        [{"id": "1", "trigger": "", "keys": ["a"]}],
        [{"id": "1", "trigger": "x", "keys": ["not-a-key"]}],
    ],
)
def test_reject_invalid_mappings(mappings):
    with pytest.raises(ValueError):
        AppConfig(mappings=mappings)


def test_extra_fields_and_key_order():
    c = AppConfig(
        mappings=[{"id": "1", "trigger": "x", "keys": ["ctrl", "a"]}], custom="kept"
    )
    assert c.model_dump()["custom"] == "kept"
    assert c.mappings[0].keys == ("ctrl", "a")
