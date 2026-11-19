"""Figure export preserving canvas dimensions and finalising layout."""

from __future__ import annotations

import math
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import matplotlib as mpl
from matplotlib.figure import Figure

from ._state import get_theme
from .layout import finish as finish_figure
from .theme import Theme

_FORMATS = frozenset({"png", "svg", "pdf"})


def save_figure(
    fig: Figure,
    path: str | Path,
    *,
    dpi: float | None = None,
    formats: Sequence[str] | None = None,
    transparent: bool = False,
    theme: Theme | str | None = None,
    finish: bool = True,
    show: bool = False,
    close: bool = False,
    **savefig_kwargs: object,
) -> Path | list[Path]:
    """Finalise layout and save ``fig`` to PNG, SVG or PDF.

    Parameters
    ----------
    fig : Figure
        Figure to export.
    path : str or Path
        Destination path (defaults to ``.png`` when no suffix is given).
    dpi : float or None, default None
        Export resolution in dots per inch. Defaults to ``fig.dpi``.
    formats : Sequence[str] or None, default None
        Formats from ``{"png", "svg", "pdf"}``, replacing the suffix of ``path``.
    transparent : bool, default ``False``
        Whether to export with a transparent background.
    theme : Theme, str or None, default None
        Explicit theme override supplying the paper background colour.
    finish : bool, default ``True``
        Whether to call :func:`finish` on ``fig`` before saving.
    show, close : bool, default ``False``
        Whether to display or close ``fig`` after saving.
    **savefig_kwargs : object
        Additional keyword arguments forwarded to :meth:`Figure.savefig`.

    Returns
    -------
    Path or list[Path]
        Written file path, or list of paths when ``formats`` is provided.
    """
    base = Path(path)
    resolution = float(fig.dpi) if dpi is None else float(dpi)
    if not math.isfinite(resolution) or resolution <= 0:
        raise ValueError("dpi must be finite and positive.")
    if "format" in savefig_kwargs:
        raise ValueError("Choose format with the path suffix or formats=, not format=.")
    if isinstance(formats, str):
        raise TypeError("formats must be a sequence such as ('png', 'svg'), not a string.")
    names = (
        [base.suffix.lstrip(".").lower() or "png"]
        if formats is None
        else [fmt.lstrip(".").lower() for fmt in formats]
    )
    if not names or len(set(names)) != len(names) or any(fmt not in _FORMATS for fmt in names):
        raise ValueError("formats must contain unique choices from png, svg, pdf.")
    targets = (
        [base if base.suffix else base.with_suffix(".png")]
        if formats is None
        else [base.with_suffix(f".{fmt}") for fmt in names]
    )
    resolved_theme = get_theme(fig, theme=theme)
    if finish:
        finish_figure(fig)
    kwargs: dict[str, Any] = dict(savefig_kwargs)
    kwargs.setdefault("bbox_inches", None)
    kwargs.setdefault("facecolor", "none" if transparent else resolved_theme.paper)
    kwargs["transparent"] = transparent
    base.parent.mkdir(parents=True, exist_ok=True)
    with mpl.rc_context({"savefig.bbox": None}):
        for target, fmt in zip(targets, names, strict=True):
            fig.savefig(target, dpi=resolution, format=fmt, **kwargs)
    if show or close:
        import matplotlib.pyplot as plt

        if show:
            plt.show()
        if close:
            plt.close(fig)
    return targets[0] if formats is None else targets
