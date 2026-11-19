"""Axes styling and house line and uncertainty-band helpers."""

from __future__ import annotations

from matplotlib.artist import Artist
from matplotlib.axes import Axes
from matplotlib.backend_bases import RendererBase
from matplotlib.collections import PolyCollection
from matplotlib.colors import to_rgba
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.text import Annotation
from matplotlib.transforms import Bbox
from numpy.typing import ArrayLike

from ._state import get_theme
from ._text import measurement_renderer
from .theme import Theme


class _UnitAnnotation(Annotation):
    """Unit label above an axes that aligns its left edge with the y-tick labels."""

    def _align_to_yaxis(self, renderer: RendererBase) -> None:
        ax = self.axes
        if ax is None:
            return
        fig = ax.get_figure()
        if not isinstance(fig, Figure):
            return
        ytb = ax.yaxis.get_tightbbox(renderer)
        scale = 72.0 / float(fig.dpi)
        dx_pt = min(0.0, float(ytb.x0 - ax.bbox.x0) * scale) if ytb is not None else 0.0
        _, dy_pt = self.xyann
        if self.xyann != (dx_pt, dy_pt):
            self.xyann = (dx_pt, dy_pt)

    def get_window_extent(self, renderer: RendererBase | None = None) -> Bbox:  # type: ignore[override]  # Annotation.get_window_extent omits Text's optional dpi parameter
        if renderer is not None:
            self._align_to_yaxis(renderer)
        return super().get_window_extent(renderer=renderer)

    def draw(self, renderer: RendererBase) -> None:
        self._align_to_yaxis(renderer)
        super().draw(renderer)


class _BaselineStyle(Artist):
    """Reconcile the native bottom spine before it is drawn."""

    def __init__(self, preference: bool | None, theme: Theme) -> None:
        super().__init__()
        self.preference = preference
        self.theme = theme
        self.set_zorder(float("-inf"))
        self.set_in_layout(False)

    def apply(self, *, anchor: bool = False) -> None:
        ax = self.axes
        if ax is None:
            return
        ymin, ymax = ax.get_ylim()
        linear = ax.get_yscale() == "linear"
        if (
            anchor
            and self.preference is True
            and linear
            and ax.get_autoscaley_on()
            and ax.has_data()
            and ymin < 0 < ymax
            and ax.dataLim.y0 == 0
            and all(
                not sibling.has_data() or sibling.dataLim.y0 >= 0
                for sibling in ax.get_shared_y_axes().get_siblings(ax)
            )
        ):
            ax.set_ylim(bottom=0.0, auto=None)
            ymin = 0.0
        spine = ax.spines["bottom"]
        at_lower_edge = spine.get_position() in {("outward", 0), ("axes", 0), ("data", 0), "zero"}
        dark = (
            self.preference is not False
            and ymin == 0.0
            and linear
            and at_lower_edge
            and (self.preference is True or ax.has_data())
        )
        color = self.theme.ink if dark else self.theme.axis
        width = self.theme.zero_spine_width if dark else self.theme.spine_width
        if spine.get_edgecolor() != to_rgba(color, spine.get_alpha()):
            spine.set_color(color)
        if spine.get_linewidth() != width:
            spine.set_linewidth(width)

    def draw(self, renderer: RendererBase) -> None:
        # Draws also cover changes made without limit notifications. Leave limit
        # anchoring to style_axes and finish, before shared axes are rendered.
        self.apply()
        self.stale = False


def _baseline_style(ax: Axes) -> _BaselineStyle | None:
    return next((artist for artist in ax.artists if isinstance(artist, _BaselineStyle)), None)


def _reapply_zero_baselines(fig: Figure) -> None:
    for ax in fig.axes:
        baseline = _baseline_style(ax)
        if baseline is not None:
            baseline.apply(anchor=True)


def style_axes(
    ax: Axes,
    unit: str | None = None,
    zero_baseline: bool | None = None,
    *,
    xlabel: str | None = None,
    theme: Theme | str | None = None,
    grid: bool = True,
) -> Axes:
    """Apply editorial house styling to ``ax`` and return it.

    Parameters
    ----------
    ax : Axes
        Target axes.
    unit : str or None, default None
        Unit label above the axes. ``None`` keeps an existing label; ``""`` removes it.
    zero_baseline : bool or None, default None
        ``None`` emphasises a zero lower limit when data exist; ``False`` uses a
        neutral spine; ``True`` also anchors autoscaled 0-based series during
        styling and finalisation. The spine's appearance is updated on redraw.
    xlabel : str or None, default None
        X-axis label. ``None`` keeps the existing label; ``""`` clears it.
    theme : Theme, str or None, default None
        Explicit theme override, or ``None`` for figure/active resolution. The
        resolved theme remains in effect for the managed bottom spine.
    grid : bool, default ``True``
        Whether to show horizontal y-axis major gridlines.

    Returns
    -------
    Axes
        The styled axes.
    """
    resolved_theme = get_theme(ax, theme=theme)
    family = resolved_theme.resolved_text_font()
    ax.set_facecolor(resolved_theme.paper)
    ax.set_axisbelow(True)
    for side in ("top", "left", "right"):
        ax.spines[side].set_visible(False)
    baseline = _baseline_style(ax)
    if baseline is None:
        baseline = _BaselineStyle(zero_baseline, resolved_theme)
        ax.add_artist(baseline)
    else:
        baseline.preference = zero_baseline
        baseline.theme = resolved_theme
    baseline.apply(anchor=True)
    ax.tick_params(
        axis="y",
        length=0,
        labelsize=resolved_theme.tick_size,
        pad=resolved_theme.ytick_pad,
        labelcolor=resolved_theme.muted,
    )
    ax.tick_params(
        axis="x",
        length=resolved_theme.tick_length,
        width=resolved_theme.tick_width,
        color=resolved_theme.axis,
        labelsize=resolved_theme.tick_size,
        pad=resolved_theme.xtick_pad,
        labelcolor=resolved_theme.muted,
    )
    for label in (*ax.get_xticklabels(), *ax.get_yticklabels()):
        label.set_fontfamily(family)
    ax.grid(False, axis="x")
    if grid:
        ax.grid(True, axis="y", color=resolved_theme.rule, linewidth=resolved_theme.grid_width)
    else:
        ax.grid(False, axis="y")
    if xlabel is not None:
        ax.set_xlabel(xlabel)
    for label in (ax.xaxis.label, ax.yaxis.label):
        label.set_fontfamily(family)
        label.set_fontsize(resolved_theme.label_size)
        label.set_color(resolved_theme.muted)
    ax.xaxis.labelpad = resolved_theme.xlabel_pad_pt

    managed = [text for text in ax.texts if text.get_gid() == "dataverse:axes:unit"]
    label_text = unit if unit is not None else managed[0].get_text() if managed else ""
    for text in managed:
        text.remove()
    if label_text:
        unit_artist = _UnitAnnotation(
            label_text,
            (0.0, 1.0),
            xycoords=ax.transAxes,
            xytext=(0.0, resolved_theme.unit_offset_pt),
            textcoords="offset points",
            ha="left",
            va="bottom",
            fontfamily=family,
            fontsize=resolved_theme.unit_size,
            color=resolved_theme.muted,
            gid="dataverse:axes:unit",
            annotation_clip=False,
        )
        ax._add_text(unit_artist)  # type: ignore[attr-defined]  # Matplotlib internal text registration
        fig = ax.get_figure()
        if isinstance(fig, Figure):
            unit_artist._align_to_yaxis(measurement_renderer(fig))
    return ax


def plot_line(
    ax: Axes,
    x: ArrayLike,
    y: ArrayLike,
    *,
    color: str | None = None,
    markers: bool = True,
    theme: Theme | str | None = None,
    **kwargs: object,
) -> list[Line2D]:
    """Plot a line series on ``ax`` using the resolved theme's line style."""
    return ax.plot(
        x, y, **get_theme(ax, theme=theme).line_style(color=color, markers=markers, **kwargs)
    )


def plot_band(
    ax: Axes,
    x: ArrayLike,
    lower: ArrayLike,
    upper: ArrayLike,
    *,
    color: str | None = None,
    alpha: float | None = None,
    theme: Theme | str | None = None,
    **kwargs: object,
) -> PolyCollection:
    """Plot a shaded band between ``lower`` and ``upper`` on ``ax``."""
    return ax.fill_between(
        x, lower, upper, **get_theme(ax, theme=theme).band_style(color=color, alpha=alpha, **kwargs)
    )
