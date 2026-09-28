from src.core.presets import get_presets


def get_profile_templates():
    """Suggested keyboard layouts, not verified game integrations."""
    presets = get_presets()
    directions = [
        dict(trigger=trigger, keys=[key])
        for trigger, key in (
            ("lewo", "left"),
            ("prawo", "right"),
            ("gora", "up"),
            ("dol", "down"),
        )
    ]
    note = "Szablon klawiatury. Dopasuj klawisze do swojej wersji gry; zgodność nie była testowana w grze."
    return [
        {
            "id": "wasd",
            "name": "WASD (klasyczne)",
            "category": "Ogólne",
            "description": "Litery czatu W/A/S/D wysyłają odpowiednie klawisze.",
            "mappings": presets["WASD (klasyczne)"],
        },
        {
            "id": "arrows",
            "name": "Strzałki",
            "category": "Ogólne",
            "description": "Komentarze up/down/left/right wysyłają strzałki.",
            "mappings": presets["Strzałki"],
        },
        {
            "id": "numpad",
            "name": "NumPad 2468",
            "category": "Ogólne",
            "description": "Cyfry czatu: 2 → dół, 4 → lewo, 6 → prawo, 8 → góra. Wysyłane są strzałki, nie klawisze numeryczne.",
            "mappings": presets["NumPad 2468"],
        },
        {
            "id": "hugo",
            "name": "Hugo",
            "category": "Retro",
            "description": note,
            "mappings": presets["Hugo (Polsat 😄)"],
        },
        {
            "id": "tetris",
            "name": "Tetris",
            "category": "Retro",
            "description": note,
            "mappings": [
                {"trigger": "lewo", "keys": ["left"]},
                {"trigger": "prawo", "keys": ["right"]},
                {"trigger": "obrot", "keys": ["up"]},
                {"trigger": "dol", "keys": ["down"]},
                {"trigger": "zrzut", "keys": ["space"]},
            ],
        },
        {
            "id": "pacman",
            "name": "Pac-Man",
            "category": "Retro",
            "description": note,
            "mappings": directions,
        },
        {
            "id": "sokoban",
            "name": "Sokoban",
            "category": "Retro",
            "description": note,
            "mappings": [*directions, {"trigger": "cofnij", "keys": ["z"]}],
        },
        {
            "id": "baba",
            "name": "Baba Is You",
            "category": "Nowsze",
            "description": note,
            "mappings": [
                *directions,
                {"trigger": "cofnij", "keys": ["z"]},
                {"trigger": "czekaj", "keys": ["space"]},
            ],
        },
    ]
