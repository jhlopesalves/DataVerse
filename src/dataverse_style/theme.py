"""Visual parameters, named themes and session-wide Matplotlib configuration."""

from __future__ import annotations

import math
import warnings
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, fields
from dataclasses import replace as dataclass_replace
from types import MappingProxyType
from typing import Any

import matplotlib as mpl
from matplotlib.cbook import normalize_kwargs
from matplotlib.collections import PolyCollection
from matplotlib.colors import is_color_like
from matplotlib.font_manager import FontProperties
from matplotlib.lines import Line2D
from matplotlib.rcsetup import cycler

from .fonts import resolve_font_family

_DEFAULT_PALETTE: tuple[str, ...] = (
    "#0f766e",
    "#b45309",
    "#3b5ba5",
    "#9b3d6b",
    "#5b6b2f",
)


def _validate_figsize(figsize: tuple[float, float]) -> None:
    if len(figsize) != 2 or any(not math.isfinite(v) or v <= 0 for v in figsize):
        raise ValueError("figsize must contain two finite, positive dimensions in inches.")


@dataclass(frozen=True)
class Theme:
    """Visual parameters defining the DataVerse editorial house style.

    Length and typography fields with ``_pt`` or ``_size`` suffixes are in
    typographical points (1/72 inch).

    Parameters
    ----------
    paper, ink, subtle, muted, rule, axis : str
        Background, primary text, secondary text, label/footer, grid/rule and
        neutral spine colours.
    context : str, default ``"#b4b0a8"``
        Intentionally faint warm grey (2.07:1 against ``paper``, exempt from
        primary series contrast thresholds) for de-emphasised contextual marks.
    accent : str, default ``"#0f766e"``
        Primary colour for the header bar and the house line and band helpers.
    palette : tuple[str, ...], default ``("#0f766e", "#b45309", "#3b5ba5", "#9b3d6b", "#5b6b2f")``
        Native Matplotlib colour cycle. It is independent of ``accent``.
        More than four categorical series is discouraged in this house style.
    title_font, text_font : str
        Preferred serif title and sans body font families.
    fallback_serif, fallback_sans : tuple[str, ...]
        Ordered fallback font families when preferred fonts are not registered.
    title_size, subtitle_size, note_size, unit_size, tick_size, label_size, annotation_size : float
        Font sizes in points.
    title_weight, signature_weight : str
        Font weights for the title and footer signature.
    title_linespacing, subtitle_linespacing, note_linespacing : float
        Line spacing multipliers for wrapped text blocks.
    margin_pt, header_gap_pt, footer_gap_pt : float
        Outer page margin and vertical clearances between header/footer and plot.
    accent_bar_width_pt, accent_bar_height_pt, accent_bar_gap_pt, title_gap_pt : float
        Header accent bar dimensions and vertical gaps in points.
    footer_bottom_offset_pt, footer_rule_gap_pt, footer_rule_width : float
        Footer baseline offset, separator gap and rule line width in points.
    footer_text_width_fraction, footer_signature_gap_pt : float
        Footer column width fraction and signature horizontal clearance.
    spine_width, zero_spine_width, grid_width, tick_length, tick_width : float
        Spine, gridline and x-tick mark dimensions in points.
    xtick_pad, ytick_pad, unit_offset_pt, xlabel_pad_pt : float
        Tick, unit and x-axis label offsets in points.
    line_width, marker_size, marker_edge_width, band_alpha : float
        Series line, hollow-marker and uncertainty-band parameters.
    figsize : tuple[float, float], default ``(7.2, 9.0)``
        Figure width and height in inches.
    dpi : float, default ``150``
        Figure resolution in dots per inch.
    """

    paper: str = "#fbfaf7"
    ink: str = "#1f1f1f"
    subtle: str = "#4a4a48"
    muted: str = "#6b6b6b"
    rule: str = "#dcd8cf"
    axis: str = "#8f8b83"
    context: str = "#b4b0a8"
    accent: str = "#0f766e"
    palette: tuple[str, ...] = _DEFAULT_PALETTE

    title_font: str = "IBM Plex Serif"
    text_font: str = "IBM Plex Sans"
    fallback_serif: tuple[str, ...] = ("DejaVu Serif", "serif")
    fallback_sans: tuple[str, ...] = ("DejaVu Sans", "sans-serif")

    title_size: float = 20.0
    title_weight: str = "semibold"
    title_linespacing: float = 1.15
    subtitle_size: float = 11.0
    subtitle_linespacing: float = 1.4
    note_size: float = 7.5
    note_linespacing: float = 1.45
    signature_weight: str = "semibold"
    unit_size: float = 9.0
    tick_size: float = 9.0
    label_size: float = 9.5
    annotation_size: float = 9.0

    margin_pt: float = 26.0
    accent_bar_width_pt: float = 34.0
    accent_bar_height_pt: float = 3.0
    accent_bar_gap_pt: float = 12.0
    title_gap_pt: float = 7.0
    header_gap_pt: float = 18.0
    footer_gap_pt: float = 18.0
    footer_bottom_offset_pt: float = 4.0
    footer_rule_gap_pt: float = 7.0
    footer_rule_width: float = 0.8
    footer_text_width_fraction: float = 0.72
    footer_signature_gap_pt: float = 12.0

    spine_width: float = 0.8
    zero_spine_width: float = 1.0
    grid_width: float = 0.6
    tick_length: float = 3.5
    tick_width: float = 0.8
    xtick_pad: float = 4.0
    ytick_pad: float = 6.0
    unit_offset_pt: float = 8.0
    xlabel_pad_pt: float = 7.0

    line_width: float = 2.4
    marker_size: float = 5.5
    marker_edge_width: float = 1.7
    band_alpha: float = 0.13

    figsize: tuple[float, float] = (7.2, 9.0)
    dpi: float = 150

    def __post_init__(self) -> None:
        object.__setattr__(self, "figsize", tuple(self.figsize))
        object.__setattr__(self, "fallback_serif", tuple(self.fallback_serif))
        object.__setattr__(self, "fallback_sans", tuple(self.fallback_sans))
        object.__setattr__(self, "palette", tuple(self.palette))
        FontProperties(weight=self.title_weight)
        FontProperties(weight=self.signature_weight)
        for name in ("paper", "ink", "subtle", "muted", "rule", "axis", "context", "accent"):
            if not is_color_like(getattr(self, name)):
                raise ValueError(f"{name} must be a Matplotlib colour.")
        if not self.palette:
            raise ValueError("palette must not be empty.")
        for colour in self.palette:
            if not isinstance(colour, str) or not is_color_like(colour):
                raise ValueError(f"Palette entry {colour!r} must be a Matplotlib colour.")
        for field in fields(self):
            name = field.name
            value = getattr(self, name)
            if isinstance(value, (int, float)):
                if not math.isfinite(value) or value < 0:
                    raise ValueError(f"{name} must be finite and non-negative.")
                if (
                    name.endswith("_size") or name.endswith("linespacing") or name == "dpi"
                ) and value == 0:
                    raise ValueError(f"{name} must be positive.")
        if not 0 <= self.band_alpha <= 1:
            raise ValueError("band_alpha must be between 0 and 1.")
        if not 0 < self.footer_text_width_fraction < 1:
            raise ValueError("footer_text_width_fraction must be between 0 and 1.")
        _validate_figsize(self.figsize)

    def replace(self, **changes: object) -> Theme:
        """Return a copy of this theme with the given fields replaced."""
        return dataclass_replace(self, **changes)  # type: ignore[arg-type]  # dataclass_replace accepts keyword field values

    def resolved_title_font(self) -> str:
        """Return ``title_font`` if registered with Matplotlib, else a fallback."""
        return resolve_font_family(self.title_font, self.fallback_serif)

    def resolved_text_font(self) -> str:
        """Return ``text_font`` if registered with Matplotlib, else a fallback."""
        return resolve_font_family(self.text_font, self.fallback_sans)

    def rc_params(self) -> mpl.RcParams:
        """Return a :class:`matplotlib.RcParams` mapping for this theme."""
        return mpl.RcParams(
            {
                "figure.facecolor": self.paper,
                "axes.facecolor": self.paper,
                "savefig.facecolor": self.paper,
                "font.family": self.resolved_text_font(),
                "text.color": self.ink,
                "axes.labelcolor": self.muted,
                "axes.labelsize": self.label_size,
                "axes.labelpad": self.xlabel_pad_pt,
                "axes.prop_cycle": cycler(color=list(self.palette)),
                "axes.spines.top": False,
                "axes.spines.right": False,
                "axes.spines.left": False,
                "axes.spines.bottom": True,
                "axes.edgecolor": self.axis,
                "axes.linewidth": self.spine_width,
                "axes.grid": True,
                "axes.grid.axis": "y",
                "axes.axisbelow": True,
                "grid.color": self.rule,
                "grid.linewidth": self.grid_width,
                "xtick.color": self.muted,
                "ytick.color": self.muted,
                "xtick.labelcolor": self.muted,
                "ytick.labelcolor": self.muted,
                "xtick.labelsize": self.tick_size,
                "ytick.labelsize": self.tick_size,
                "xtick.major.size": self.tick_length,
                "xtick.major.width": self.tick_width,
                "xtick.major.pad": self.xtick_pad,
                "ytick.major.size": 0.0,
                "ytick.major.pad": self.ytick_pad,
                "lines.linewidth": self.line_width,
                "legend.frameon": False,
                "legend.fontsize": self.annotation_size,
                "legend.labelcolor": self.subtle,
                "legend.title_fontsize": self.annotation_size,
                "pdf.fonttype": 42,
                "ps.fonttype": 42,
                "figure.dpi": self.dpi,
                "figure.figsize": list(self.figsize),
            }
        )

    def line_style(
        self,
        *,
        color: str | None = None,
        markers: bool = True,
        **overrides: object,
    ) -> dict[str, Any]:
        """Return keyword arguments for ``ax.plot`` in the house series style."""
        style: dict[str, Any] = {
            "color": self.accent if color is None else color,
            "linewidth": self.line_width,
        }
        if markers:
            style.update(
                {
                    "marker": "o",
                    "markersize": self.marker_size,
                    "markerfacecolor": self.paper,
                    "markeredgecolor": "auto",
                    "markeredgewidth": self.marker_edge_width,
                }
            )
        else:
            style["marker"] = "None"
        style.update(normalize_kwargs(overrides, Line2D))
        return style

    def band_style(
        self,
        *,
        color: str | None = None,
        alpha: float | None = None,
        **overrides: object,
    ) -> dict[str, Any]:
        """Return keyword arguments for ``ax.fill_between`` in the house band style."""
        style: dict[str, Any] = {
            "color": self.accent if color is None else color,
            "alpha": self.band_alpha if alpha is None else alpha,
            "linewidth": 0,
        }
        style.update(normalize_kwargs(overrides, PolyCollection))
        return style


DEFAULT_THEME = Theme()

LANDSCAPE_THEME = DEFAULT_THEME.replace(figsize=(9.0, 6.0), dpi=200)

REPORT_THEME = DEFAULT_THEME.replace(
    margin_pt=18.0,
    title_size=15.0,
    subtitle_size=9.5,
    note_size=7.0,
    unit_size=8.0,
    tick_size=8.0,
    label_size=8.5,
    annotation_size=8.0,
    header_gap_pt=14.0,
    footer_gap_pt=14.0,
    figsize=(6.5, 4.5),
    dpi=300,
)

THEMES: Mapping[str, Theme] = MappingProxyType(
    {
        "social": DEFAULT_THEME,
        "landscape": LANDSCAPE_THEME,
        "report": REPORT_THEME,
    }
)

_ACTIVE_THEME: Theme = DEFAULT_THEME


def active_theme() -> Theme:
    """Return the currently active package theme."""
    return _ACTIVE_THEME


def resolve_theme(theme: Theme | str | None = None) -> Theme:
    """Resolve a :class:`Theme`, a case-insensitive name in :data:`THEMES`, or ``None``."""
    if theme is None:
        return _ACTIVE_THEME
    if isinstance(theme, Theme):
        return theme
    if isinstance(theme, str):
        key = theme.strip().lower()
        if key not in THEMES:
            valid = ", ".join(THEMES)
            raise ValueError(f"Unknown theme {theme!r}. Choose from: {valid}.")
        return THEMES[key]
    raise TypeError(f"theme must be a Theme, str or None, got {type(theme).__name__}.")


def use(theme: Theme | str = DEFAULT_THEME) -> Theme:
    """Apply ``theme`` globally to ``matplotlib.rcParams`` and set it as active.

    Parameters
    ----------
    theme : Theme or str, default :data:`DEFAULT_THEME`
        Theme instance or case-insensitive name from :data:`THEMES`.

    Returns
    -------
    Theme
        The resolved active theme.

    Raises
    ------
    ValueError
        If ``theme`` is an unknown theme name.
    """
    global _ACTIVE_THEME
    resolved = resolve_theme(theme)
    title_resolved = resolved.resolved_title_font()
    text_resolved = resolved.resolved_text_font()
    fallbacks: list[str] = []
    if title_resolved != resolved.title_font:
        fallbacks.append(f"title_font {resolved.title_font!r} -> {title_resolved!r}")
    if text_resolved != resolved.text_font:
        fallbacks.append(f"text_font {resolved.text_font!r} -> {text_resolved!r}")
    if fallbacks:
        warnings.warn(
            f"Preferred font not registered ({'; '.join(fallbacks)}). "
            "Call register_fonts() or ensure_fonts() before use().",
            UserWarning,
            stacklevel=2,
        )
    mpl.rcParams.update(resolved.rc_params())
    _ACTIVE_THEME = resolved
    return resolved


@contextmanager
def theme_context(theme: Theme | str = DEFAULT_THEME) -> Iterator[Theme]:
    """Temporarily apply ``theme`` to ``matplotlib.rcParams`` and the active theme."""
    global _ACTIVE_THEME
    resolved = resolve_theme(theme)
    previous = _ACTIVE_THEME
    with mpl.rc_context(rc=dict(resolved.rc_params())):
        _ACTIVE_THEME = resolved
        try:
            yield resolved
        finally:
            _ACTIVE_THEME = previous
