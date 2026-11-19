"""Figure composition metadata and theme resolution."""

from __future__ import annotations

from dataclasses import dataclass

from matplotlib.axes import Axes
from matplotlib.figure import Figure

from .theme import Theme, active_theme, resolve_theme


@dataclass(frozen=True)
class Composition:
    title: str
    subtitle: str
    source: str
    note: str
    signature: str
    lang: str
    accent_bar: bool = False
    footer_rule: bool = False
    header_theme: Theme | None = None
    footer_theme: Theme | None = None
    compress: bool = False
    wspace: float | None = None
    hspace: float | None = None


@dataclass(frozen=True)
class FigureState:
    theme: Theme
    composition: Composition


def figure_state(fig: Figure) -> FigureState | None:
    state = getattr(fig, "_dataverse_state", None)
    return state if isinstance(state, FigureState) else None


def associate(fig: Figure, state: FigureState) -> None:
    vars(fig)["_dataverse_state"] = state


def get_theme(target: Figure | Axes, *, theme: Theme | str | None = None) -> Theme:
    """Resolve an explicit theme, then the figure's stored theme, then the active theme."""
    if theme is not None:
        return resolve_theme(theme)
    fig = target.get_figure() if isinstance(target, Axes) else target
    state = figure_state(fig) if isinstance(fig, Figure) else None
    return state.theme if state is not None else active_theme()
