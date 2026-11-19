"""Editorial header, footer and constrained-layout composition."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import replace
from typing import Any, Literal

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.font_manager import FontProperties
from matplotlib.layout_engine import ConstrainedLayoutEngine
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
from matplotlib.text import Text
from numpy.typing import NDArray

from ._state import Composition, FigureState, associate, figure_state, get_theme
from ._text import artist_height_pt, measurement_renderer, text_width_pt, wrap_text
from .axes import _reapply_zero_baselines
from .fonts import _resolved_weight
from .formatting import _localized_text, _normalize_lang
from .theme import Theme, _validate_figsize, resolve_theme, theme_context


def _add_text(
    fig: Figure,
    x: float,
    y: float,
    text: str,
    *,
    family: str,
    size: float,
    color: str,
    va: str,
    linespacing: float,
    gid: str,
    weight: str | int = "normal",
    ha: str = "left",
) -> Text:
    return fig.text(
        x,
        y,
        text,
        fontfamily=family,
        fontsize=size,
        fontweight=weight,
        color=color,
        va=va,
        ha=ha,
        linespacing=linespacing,
        usetex=False,
        parse_math=False,
        gid=gid,
    )


def header(
    fig: Figure,
    title: str,
    subtitle: str = "",
    *,
    theme: Theme | str | None = None,
    accent_bar: bool = True,
) -> float:
    """Replace the header and return its bottom as a fraction of the figure height.

    On an editorial figure, the replacement is retained by :func:`finish`.
    Pass empty text and ``accent_bar=False`` to clear the header.
    """
    resolved_theme = get_theme(fig, theme=theme)
    bottom = _draw_header(fig, title, subtitle, resolved_theme, accent_bar=accent_bar)
    state = figure_state(fig)
    if state is not None:
        composition = replace(
            state.composition,
            title=title,
            subtitle=subtitle,
            accent_bar=accent_bar,
            header_theme=resolved_theme if theme is not None else None,
        )
        associate(fig, replace(state, composition=composition))
    return bottom


def _draw_header(
    fig: Figure, title: str, subtitle: str, resolved_theme: Theme, *, accent_bar: bool
) -> float:
    eff_margin_pt = resolved_theme.margin_pt
    width_in, height_in = fig.get_size_inches()
    width_pt, height_pt = float(width_in) * 72.0, float(height_in) * 72.0
    _validate_margin(eff_margin_pt, width_pt, height_pt)
    usable_pt = width_pt - 2.0 * eff_margin_pt
    x = eff_margin_pt / width_pt
    title_font = resolved_theme.resolved_title_font()
    weight = _resolved_weight(title_font, resolved_theme.title_weight)
    wrapped_title = wrap_text(
        fig,
        title,
        usable_pt,
        fontfamily=title_font,
        fontsize=resolved_theme.title_size,
        fontweight=weight,
    )
    text_font = resolved_theme.resolved_text_font()
    wrapped_sub = wrap_text(
        fig, subtitle, usable_pt, fontfamily=text_font, fontsize=resolved_theme.subtitle_size
    )

    _remove_managed(fig, "header")
    y = height_pt - eff_margin_pt
    if accent_bar:
        bar_h, bar_w = resolved_theme.accent_bar_height_pt, resolved_theme.accent_bar_width_pt
        fig.add_artist(
            Rectangle(
                (x, (y - bar_h) / height_pt),
                bar_w / width_pt,
                bar_h / height_pt,
                transform=fig.transFigure,
                color=resolved_theme.accent,
                linewidth=0,
                gid="dataverse:header:accent",
            )
        )
        y -= bar_h + resolved_theme.accent_bar_gap_pt

    if title:
        title_artist = _add_text(
            fig,
            x,
            y / height_pt,
            wrapped_title,
            family=title_font,
            size=resolved_theme.title_size,
            weight=weight,
            color=resolved_theme.ink,
            va="top",
            linespacing=resolved_theme.title_linespacing,
            gid="dataverse:header:title",
        )
        y -= artist_height_pt(fig, title_artist) + (
            resolved_theme.title_gap_pt if subtitle else 0.0
        )

    if subtitle:
        sub_artist = _add_text(
            fig,
            x,
            y / height_pt,
            wrapped_sub,
            family=text_font,
            size=resolved_theme.subtitle_size,
            color=resolved_theme.subtle,
            va="top",
            linespacing=resolved_theme.subtitle_linespacing,
            gid="dataverse:header:subtitle",
        )
        y -= artist_height_pt(fig, sub_artist)

    return float(y / height_pt)


def _remove_managed(fig: Figure, section: str) -> None:
    prefix = f"dataverse:{section}:"
    for artist in (*fig.texts, *fig.artists):
        if (artist.get_gid() or "").startswith(prefix):
            artist.remove()


def _validate_margin(margin: float, width_pt: float, height_pt: float) -> None:
    if not math.isfinite(margin) or margin < 0 or 2 * margin >= min(width_pt, height_pt):
        raise ValueError("margin_pt must be finite, non-negative and leave usable figure space.")


def _format_footer_field(label: str, prefixes: tuple[str, ...], text: str) -> str:
    lower = text.lower()
    for prefix in prefixes:
        if lower.startswith(prefix):
            text = text[len(prefix) :].strip()
            break
    return f"{label}: {text}" if text else f"{label}:"


def footer(
    fig: Figure,
    source: str | Mapping[str, str] = "",
    note: str | Mapping[str, str] = "",
    *,
    signature: str = "",
    lang: str = "en",
    theme: Theme | str | None = None,
    rule: bool = True,
) -> float:
    """Replace the footer and return its top as a fraction of the figure height.

    On an editorial figure, the localised replacement is retained by :func:`finish`.
    Pass empty text and ``rule=False`` to clear the footer.
    """
    resolved_theme = get_theme(fig, theme=theme)
    norm = _normalize_lang(lang)
    source_text = _localized_text(source, norm).strip()
    note_text = _localized_text(note, norm).strip()
    signature = signature.strip()
    top = _draw_footer(fig, source_text, note_text, signature, norm, resolved_theme, rule=rule)
    state = figure_state(fig)
    if state is not None:
        composition = replace(
            state.composition,
            source=source_text,
            note=note_text,
            signature=signature,
            lang=norm,
            footer_rule=rule,
            footer_theme=resolved_theme if theme is not None else None,
        )
        associate(fig, replace(state, composition=composition))
    return top


def _draw_footer(
    fig: Figure,
    source_text: str,
    note_text: str,
    signature: str,
    lang: str,
    resolved_theme: Theme,
    *,
    rule: bool,
) -> float:
    margin = resolved_theme.margin_pt
    width_pt, height_pt = (float(v) * 72 for v in fig.get_size_inches())
    _validate_margin(margin, width_pt, height_pt)
    usable = width_pt - 2 * margin
    family = resolved_theme.resolved_text_font()
    renderer = measurement_renderer(fig)
    sig_weight = _resolved_weight(family, resolved_theme.signature_weight)
    sig_prop = FontProperties(family=family, size=resolved_theme.note_size, weight=sig_weight)
    sig_width = max(
        (text_width_pt(renderer, line, sig_prop) for line in signature.split("\n")), default=0
    )
    clearance = usable - sig_width - resolved_theme.footer_signature_gap_pt
    stacked = bool(signature and (source_text or note_text) and clearance < 60)
    wrap_width = (
        usable
        if stacked or not signature
        else min(resolved_theme.footer_text_width_fraction * usable, clearance)
    )
    labels = ("Fonte", "Nota") if lang == "pt" else ("Source", "Note")
    prefix_pairs = (("source:", "fonte:"), ("note:", "nota:"))
    paragraphs = [
        wrap_text(
            fig,
            _format_footer_field(lbl, prefs, txt),
            wrap_width,
            fontfamily=family,
            fontsize=resolved_theme.note_size,
        )
        for lbl, prefs, txt in zip(labels, prefix_pairs, (source_text, note_text), strict=True)
        if txt
    ]
    wrapped_sig = wrap_text(
        fig,
        signature,
        usable,
        fontfamily=family,
        fontsize=resolved_theme.note_size,
        fontweight=resolved_theme.signature_weight,
    )
    _remove_managed(fig, "footer")
    if not (source_text or note_text or signature or rule):
        return margin / height_pt
    baseline = max(0.0, margin - resolved_theme.footer_bottom_offset_pt)
    x = margin / width_pt
    left_artist = (
        _add_text(
            fig,
            x,
            baseline / height_pt,
            "\n".join(paragraphs),
            family=family,
            size=resolved_theme.note_size,
            color=resolved_theme.muted,
            va="bottom",
            linespacing=resolved_theme.note_linespacing,
            gid="dataverse:footer:text",
        )
        if paragraphs
        else None
    )
    signature_artist = (
        _add_text(
            fig,
            1 - x,
            baseline / height_pt,
            wrapped_sig,
            family=family,
            size=resolved_theme.note_size,
            weight=sig_weight,
            color=resolved_theme.muted,
            va="top",
            ha="right",
            linespacing=resolved_theme.note_linespacing,
            gid="dataverse:footer:signature",
        )
        if wrapped_sig
        else None
    )
    text_height = artist_height_pt(fig, left_artist) if left_artist is not None else 0.0
    sig_height = artist_height_pt(fig, signature_artist) if signature_artist is not None else 0.0
    if stacked:
        text_bottom = baseline + sig_height + resolved_theme.footer_signature_gap_pt
        if left_artist is not None:
            left_artist.set_y(text_bottom / height_pt)
        top = text_bottom + text_height
        if signature_artist is not None:
            signature_artist.set_y((baseline + sig_height) / height_pt)
    else:
        top = baseline + max(text_height, sig_height)
        if signature_artist is not None:
            signature_artist.set_y(top / height_pt)
    if rule:
        top += resolved_theme.footer_rule_gap_pt
        fig.add_artist(
            Line2D(
                [x, 1 - x],
                [top / height_pt] * 2,
                transform=fig.transFigure,
                color=resolved_theme.rule,
                linewidth=resolved_theme.footer_rule_width,
                gid="dataverse:footer:rule",
            )
        )
    return top / height_pt


def finish(fig: Figure, *, compress: bool | None = None) -> None:
    """Redraw header/footer, apply constrained layout and re-evaluate zero baselines.

    Parameters
    ----------
    fig : Figure
        Target figure.
    compress : bool or None, default None
        Whether to enable compressed layout for fixed-aspect axes.

    Raises
    ------
    ValueError
        If the header and footer overlap or leave no plotting area.
    """
    state = figure_state(fig)
    theme = state.theme if state is not None else get_theme(fig)
    width_pt, height_pt = (float(v) * 72.0 for v in fig.get_size_inches())
    margin = theme.margin_pt
    _validate_margin(margin, width_pt, height_pt)
    _reapply_zero_baselines(fig)

    if state is not None:
        comp = state.composition
        if compress is not None and compress != comp.compress:
            comp = replace(comp, compress=compress)
            associate(fig, FigureState(theme, comp))
        if comp.title or comp.subtitle or comp.accent_bar:
            header_theme = comp.header_theme or theme
            h_bot = _draw_header(
                fig, comp.title, comp.subtitle, header_theme, accent_bar=comp.accent_bar
            )
            top = h_bot - header_theme.header_gap_pt / height_pt
        else:
            _remove_managed(fig, "header")
            top = 1.0 - margin / height_pt

        if comp.source or comp.note or comp.signature or comp.footer_rule:
            footer_theme = comp.footer_theme or theme
            f_top = _draw_footer(
                fig,
                comp.source,
                comp.note,
                comp.signature,
                comp.lang,
                footer_theme,
                rule=comp.footer_rule,
            )
            bottom = f_top + footer_theme.footer_gap_pt / height_pt
        else:
            _remove_managed(fig, "footer")
            bottom = margin / height_pt

        eff_compress = comp.compress
        wspace = 0.05 if comp.wspace is None else comp.wspace
        hspace = 0.05 if comp.hspace is None else comp.hspace
    else:
        bottom, top = margin / height_pt, 1.0 - margin / height_pt
        eff_compress = False if compress is None else compress
        wspace = hspace = 0.05

    left, right = margin / width_pt, 1.0 - margin / width_pt
    if not (
        math.isfinite(left)
        and math.isfinite(right)
        and 0.0 <= left < right <= 1.0
        and math.isfinite(bottom)
        and math.isfinite(top)
        and 0.0 <= bottom < top <= 1.0
    ):
        raise ValueError(
            "Header/footer overlap or exceed the canvas; enlarge the figure or reduce text."
        )

    rect = (left, bottom, right - left, top - bottom)
    has_gridspec_axes = any(
        ax.get_subplotspec() is not None and ax.get_in_layout() for ax in fig.axes
    )
    if not fig.axes or has_gridspec_axes:
        engine = ConstrainedLayoutEngine(
            rect=rect, w_pad=0.0, h_pad=0.0, wspace=wspace, hspace=hspace, compress=eff_compress
        )
        fig.set_layout_engine(engine)
        if has_gridspec_axes:
            engine.execute(fig)
            engine.execute(fig)
    else:
        fig.set_layout_engine("none")

    _reapply_zero_baselines(fig)


def editorial_figure(
    *,
    title: str = "",
    subtitle: str = "",
    source: str | Mapping[str, str] = "",
    note: str | Mapping[str, str] = "",
    signature: str = "",
    lang: str = "en",
    theme: Theme | str | None = None,
    figsize: tuple[float, float] | None = None,
    dpi: float | None = None,
    accent_bar: bool = True,
    footer_rule: bool = True,
    compress: bool = False,
) -> Figure:
    """Create a composed editorial :class:`Figure` without axes and return it."""
    effective = resolve_theme(theme)
    size = effective.figsize if figsize is None else figsize
    resolution = effective.dpi if dpi is None else dpi
    _validate_figsize(size)
    if not math.isfinite(resolution) or resolution <= 0:
        raise ValueError("dpi must be finite and positive.")
    norm = _normalize_lang(lang)
    source_text = _localized_text(source, norm).strip()
    note_text = _localized_text(note, norm).strip()
    signature = signature.strip()
    composition = Composition(
        title=title,
        subtitle=subtitle,
        source=source_text,
        note=note_text,
        signature=signature,
        lang=norm,
        accent_bar=accent_bar and bool(title or subtitle),
        footer_rule=footer_rule and bool(source_text or note_text or signature),
        compress=compress,
    )
    with theme_context(effective):
        fig = plt.figure(figsize=size, dpi=resolution, facecolor=effective.paper)
    associate(fig, FigureState(effective, composition))
    try:
        finish(fig)
    except (ValueError, RuntimeError, TypeError, KeyError):
        plt.close(fig)
        raise
    return fig


def editorial_subplots(
    nrows: int = 1,
    ncols: int = 1,
    *,
    title: str = "",
    subtitle: str = "",
    source: str | Mapping[str, str] = "",
    note: str | Mapping[str, str] = "",
    signature: str = "",
    lang: str = "en",
    theme: Theme | str | None = None,
    figsize: tuple[float, float] | None = None,
    dpi: float | None = None,
    accent_bar: bool = True,
    footer_rule: bool = True,
    compress: bool = False,
    sharex: bool | Literal["none", "all", "row", "col"] = False,
    sharey: bool | Literal["none", "all", "row", "col"] = False,
    squeeze: bool = True,
    width_ratios: Sequence[float] | None = None,
    height_ratios: Sequence[float] | None = None,
    subplot_kw: Mapping[str, Any] | None = None,
    gridspec_kw: Mapping[str, Any] | None = None,
) -> tuple[Figure, Axes | NDArray[np.object_]]:
    """Create a composed editorial figure and subplot grid."""
    gs_kw = dict(gridspec_kw or {})
    if {"left", "right", "top", "bottom"} & gs_kw.keys():
        raise ValueError("Subplot bounds are managed by finish(), not gridspec_kw.")
    raw_wspace, raw_hspace = gs_kw.pop("wspace", None), gs_kw.pop("hspace", None)
    wspace = float(raw_wspace) if raw_wspace is not None else None
    hspace = float(raw_hspace) if raw_hspace is not None else None
    if wspace is not None and (not math.isfinite(wspace) or wspace < 0):
        raise ValueError("wspace must be finite and non-negative.")
    if hspace is not None and (not math.isfinite(hspace) or hspace < 0):
        raise ValueError("hspace must be finite and non-negative.")

    fig = editorial_figure(
        title=title,
        subtitle=subtitle,
        source=source,
        note=note,
        signature=signature,
        lang=lang,
        theme=theme,
        figsize=figsize,
        dpi=dpi,
        accent_bar=accent_bar,
        footer_rule=footer_rule,
        compress=compress,
    )
    state = figure_state(fig)
    if state is not None and (wspace is not None or hspace is not None):
        associate(
            fig, FigureState(state.theme, replace(state.composition, wspace=wspace, hspace=hspace))
        )
    try:
        with theme_context(get_theme(fig)):
            axes = fig.subplots(
                nrows,
                ncols,
                sharex=sharex,
                sharey=sharey,
                squeeze=squeeze,
                width_ratios=width_ratios,
                height_ratios=height_ratios,
                subplot_kw=dict(subplot_kw or {}),
                gridspec_kw=gs_kw,
            )
        finish(fig)
    except (ValueError, TypeError, AttributeError):
        plt.close(fig)
        raise
    return fig, axes
