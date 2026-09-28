from pathlib import Path


def validate_assets(root: Path):
    dist = root / "frontend" / "dist"
    if not (dist / "index.html").is_file() or not list((dist / "assets").glob("*.js")):
        raise RuntimeError(
            "Brak gotowego panelu: npm --prefix frontend ci && npm --prefix frontend run build"
        )
    for icon in ("tiko_play.ico", "tiko_play.icns"):
        if not (root / icon).is_file():
            raise RuntimeError(f"Brak ikony {icon}")
    return [
        (str(dist), "frontend/dist"),
        (str(root / "src" / "locales"), "src/locales"),
        (str(root / "tiko_play.ico"), "."),
        (str(root / "tiko_play.icns"), "."),
    ]
