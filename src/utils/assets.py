"""Static asset loaders (SVG, etc.)."""
from functools import lru_cache
from pathlib import Path

_ASSETS_DIR = Path(__file__).resolve().parents[2] / "assets"


@lru_cache(maxsize=8)
def load_svg(name: str) -> str:
    """Read an SVG file from /assets and return its markup. Empty string if missing."""
    path = _ASSETS_DIR / name
    return path.read_text(encoding="utf-8") if path.exists() else ""


def f1_logo(class_name: str = "f1-mark") -> str:
    """Return the F1 wordmark SVG, wrapped in a span with the given class for CSS sizing."""
    svg = load_svg("f1-logo.svg")
    if not svg:
        return ""
    return f'<span class="{class_name}">{svg}</span>'
