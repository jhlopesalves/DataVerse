"""Local font registration and optional pinned IBM Plex downloads."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Sequence
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.request import urlopen

from matplotlib import font_manager

_GENERIC_FAMILIES = frozenset({"serif", "sans-serif", "monospace", "cursive", "fantasy"})
_PLEX_REVISION = "bc6a7e4b37634eb79785d59781893db63ee3edcb"
_PLEX_FILES = (
    (
        "plex-sans",
        "IBMPlexSans-Regular.ttf",
        "b47ebd72b5ce53b60f909033ff84d6fc12358cc147e2981f8c321ad3f36246b6",
    ),
    (
        "plex-sans",
        "IBMPlexSans-Medium.ttf",
        "a494d5a69fa094f7071a9ffbc98e86c85337d1a29f3fc1ff7c2e1c46161ddf27",
    ),
    (
        "plex-sans",
        "IBMPlexSans-SemiBold.ttf",
        "c51119b25f4a296da2b66edf3201b9aa1735091ed7efc1fca0313346f3851a4d",
    ),
    (
        "plex-serif",
        "IBMPlexSerif-SemiBold.ttf",
        "857edeaaff0f3913f4dfaf6bc0e9c89ef73e475429cf63d6a3cb5d1022a213d5",
    ),
)


def resolve_font_family(
    preferred: str,
    fallbacks: Sequence[str] = ("DejaVu Sans", "sans-serif"),
) -> str:
    """Return the first registered font family from ``(preferred, *fallbacks)``."""
    available = {entry.name for entry in font_manager.fontManager.ttflist} | _GENERIC_FAMILIES
    return next((name for name in (preferred, *fallbacks) if name in available), "sans-serif")


def _resolved_weight(family: str, weight: str | int) -> str | int:
    requested = font_manager.weight_dict[weight] if isinstance(weight, str) else weight
    weights = {
        font_manager.weight_dict[entry.weight] if isinstance(entry.weight, str) else entry.weight
        for entry in font_manager.fontManager.ttflist
        if entry.name == family
    }
    return (
        min(weights, key=lambda candidate: (abs(candidate - requested), candidate))
        if weights
        else weight
    )


def register_fonts(font_dir: str | Path | Iterable[str | Path] = "fonts") -> list[Path]:
    """Register local ``.ttf`` and ``.otf`` files with Matplotlib and return their paths."""
    paths = [Path(font_dir)] if isinstance(font_dir, (str, Path)) else map(Path, font_dir)
    known = {Path(entry.fname).resolve() for entry in font_manager.fontManager.ttflist}
    registered: list[Path] = []
    seen: set[Path] = set()
    for path in paths:
        candidates = [path] if path.is_file() else sorted(path.iterdir()) if path.is_dir() else []
        for candidate in candidates:
            if not candidate.is_file() or candidate.suffix.lower() not in {".ttf", ".otf"}:
                continue
            resolved = candidate.resolve()
            if resolved in seen:
                continue
            if resolved not in known:
                font_manager.fontManager.addfont(str(resolved))
                known.add(resolved)
            seen.add(resolved)
            registered.append(candidate)
    return registered


def ensure_fonts(font_dir: str | Path = "fonts", *, download: bool = False) -> list[Path]:
    """Register local fonts, optionally downloading missing pinned IBM Plex files."""
    directory = Path(font_dir)
    if download:
        directory.mkdir(parents=True, exist_ok=True)
        for package, filename, digest in _PLEX_FILES:
            destination = directory / filename
            if destination.exists():
                continue
            url = (
                f"https://raw.githubusercontent.com/IBM/plex/{_PLEX_REVISION}/"
                f"packages/{package}/fonts/complete/ttf/{filename}"
            )
            with urlopen(url, timeout=30) as response:
                content = response.read()
            if hashlib.sha256(content).hexdigest() != digest:
                raise ValueError(
                    f"SHA-256 mismatch for IBM Plex font {filename}; file not installed."
                )
            with TemporaryDirectory(prefix=".plex-", dir=directory) as temporary:
                staged = Path(temporary) / filename
                staged.write_bytes(content)
                staged.replace(destination)
    return register_fonts(directory)
