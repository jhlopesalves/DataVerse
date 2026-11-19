"""Explicit font lifecycle, pinned downloads and fallback rendering."""

from __future__ import annotations

import hashlib
import io
from pathlib import Path

import matplotlib.pyplot as plt
import pytest
from matplotlib import font_manager

from dataverse_style import (
    DEFAULT_THEME,
    editorial_subplots,
    ensure_fonts,
    register_fonts,
    style_axes,
)
from dataverse_style import fonts as implementation


def test_local_registration_is_idempotent_and_never_downloads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbid(*_args: object, **_kwargs: object) -> None:
        pytest.fail("Unexpected network request")

    monkeypatch.setattr(implementation, "urlopen", forbid)
    assert ensure_fonts(tmp_path / "absent") == []
    assert not (tmp_path / "absent").exists()
    font = Path(font_manager.findfont("DejaVu Sans"))
    before = len(font_manager.fontManager.ttflist)
    assert register_fonts([font, font]) == [font]
    assert register_fonts(font) == [font]
    assert len(font_manager.fontManager.ttflist) == before


def test_deliberate_download_checks_hash_and_keeps_existing_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    content = Path(font_manager.findfont("DejaVu Sans")).read_bytes()
    files = (("test-package", "test-font.ttf", hashlib.sha256(content).hexdigest()),)
    monkeypatch.setattr(implementation, "_PLEX_FILES", files)
    requests: list[str] = []

    def download(url: str, *, timeout: int) -> io.BytesIO:
        assert implementation._PLEX_REVISION in url
        assert timeout == 30
        requests.append(url)
        return io.BytesIO(content)

    monkeypatch.setattr(implementation, "urlopen", download)
    directory = tmp_path / "fonts"
    try:
        assert ensure_fonts(directory, download=True) == [directory / "test-font.ttf"]
        ensure_fonts(directory, download=True)
        assert len(requests) == 1
        assert (directory / "test-font.ttf").read_bytes() == content
        assert sorted(p.name for p in directory.iterdir()) == ["test-font.ttf"]
    finally:
        font_manager.fontManager.ttflist[:] = [
            entry
            for entry in font_manager.fontManager.ttflist
            if Path(entry.fname) != (directory / "test-font.ttf").resolve()
        ]


def test_bad_download_leaves_no_partial_font(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(implementation, "_PLEX_FILES", (("test", "invalid.ttf", "0" * 64),))
    monkeypatch.setattr(implementation, "urlopen", lambda *_a, **_kw: io.BytesIO(b"incomplete"))
    with pytest.raises(ValueError, match="SHA-256"):
        ensure_fonts(tmp_path, download=True)
    assert list(tmp_path.iterdir()) == []


def test_missing_families_and_weights_render_without_fallback_logs(
    caplog: pytest.LogCaptureFixture,
) -> None:
    custom = DEFAULT_THEME.replace(title_font="UnavailableSerifXYZ", text_font="UnavailableSansXYZ")
    fig, ax = editorial_subplots(
        title="A fallback headline", source="Synthetic", signature="DataVerse", theme=custom
    )
    style_axes(ax, unit="Unit")
    fig.canvas.draw()
    plt.close(fig)
    assert not [
        record for record in caplog.records if record.name.startswith("matplotlib.font_manager")
    ]
