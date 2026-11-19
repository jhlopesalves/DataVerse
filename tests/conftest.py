"""Shared pytest configuration and fixtures for ``dataverse_style``."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import matplotlib as mpl

mpl.use("Agg")

import matplotlib.pyplot as plt
import pytest

import dataverse_style.theme as theme_mod
from dataverse_style import DEFAULT_THEME, register_fonts

_FONT_DIR = Path(__file__).resolve().parent.parent / "fonts"
if _FONT_DIR.is_dir():
    register_fonts(_FONT_DIR)


@pytest.fixture(autouse=True)
def _isolated_matplotlib_state() -> Iterator[None]:
    """Reset rcParams and active theme around each test and close all figures."""
    saved_rc = dict(mpl.rcParams)
    saved_theme = getattr(theme_mod, "_ACTIVE_THEME", DEFAULT_THEME)
    try:
        yield
    finally:
        plt.close("all")
        mpl.rcParams.update(saved_rc)
        if hasattr(theme_mod, "_ACTIVE_THEME"):
            theme_mod._ACTIVE_THEME = saved_theme  # type: ignore[attr-defined]
