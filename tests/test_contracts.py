"""Public contracts and edge-case tests for ``dataverse_style``."""

from __future__ import annotations

import gc
import locale
import subprocess
import sys
import weakref
from collections.abc import Callable
from importlib.metadata import version
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.backends.backend_pdf import FigureCanvasPdf
from matplotlib.backends.backend_svg import FigureCanvasSVG
from matplotlib.colors import to_hex, to_rgba
from PIL import Image

import dataverse_style as viz
from dataverse_style import (
    DEFAULT_THEME,
    REPORT_THEME,
    brl_formatter,
    editorial_figure,
    editorial_subplots,
    finish,
    footer,
    format_brl,
    format_number,
    get_theme,
    header,
    number_formatter,
    plot_band,
    plot_line,
    save_figure,
    style_axes,
    theme_context,
)


def test_public_namespace_is_intentional() -> None:
    assert len(viz.__all__) == len(set(viz.__all__))
    assert all(hasattr(viz, name) for name in viz.__all__)
    assert not {
        "editorial_axes",
        "apply_theme",
        "FigurePreset",
        "SOCIAL_PRESET",
        "LANDSCAPE_PRESET",
        "REPORT_PRESET",
        "Layout",
        "PlotBounds",
        "plot_bounds",
        "relayout",
    } & set(viz.__all__)
    assert viz.__name__ == "dataverse_style"
    assert hasattr(viz, "Theme")
    assert viz.__version__ == version("dataverse-style")


@pytest.mark.parametrize("directory", [".", "projects/001-bh-itbi"])
def test_installed_imports_from_project_directories(directory: str) -> None:
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-c", "from dataverse_style import editorial_subplots"],
        cwd=root / directory,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_theme_propagates_with_explicit_operation_overrides(tmp_path: Path) -> None:
    custom = DEFAULT_THEME.replace(paper="#fff0f0", accent="#9a2342", axis="#5e5154", tick_size=13)
    override = custom.replace(
        accent="#123456",
        paper="#eeeeff",
        tick_size=8,
        ink="#57214b",
        axis="#485e74",
        spine_width=0.6,
        zero_spine_width=1.4,
    )
    fig, ax = editorial_subplots(title="Custom theme", theme=custom)
    assert get_theme(fig) is get_theme(ax) is custom
    assert get_theme(ax, theme=override) is override
    (native_line,) = ax.plot([0, 1], [1, 2])
    assert to_hex(native_line.get_color()) == custom.palette[0]
    (line,) = plot_line(ax, [0, 1], [1, 2])
    band = plot_band(ax, [0, 1], [0, 1], [2, 3])
    style_axes(ax)
    assert to_hex(line.get_color()) == custom.accent
    assert to_hex(line.get_markerfacecolor()) == custom.paper
    assert band.get_facecolor()[0] == pytest.approx(to_rgba(custom.accent, custom.band_alpha))
    assert ax.get_yticklabels()[0].get_fontsize() == 13
    (line2,) = plot_line(ax, [0, 1], [2, 3], theme=override)
    assert to_hex(line2.get_color()) == override.accent
    style_axes(ax, theme=override)
    assert ax.get_yticklabels()[0].get_fontsize() == 8
    ax.set_ylim(0, 4)
    finish(fig)
    assert get_theme(ax) is custom
    spine = ax.spines["bottom"]
    assert to_hex(spine.get_edgecolor()) == override.ink
    assert spine.get_linewidth() == pytest.approx(override.zero_spine_width)
    ax.set_ylim(1, 4)
    path = save_figure(fig, tmp_path / "custom.png")
    assert to_hex(spine.get_edgecolor()) == override.axis
    assert spine.get_linewidth() == pytest.approx(override.spine_width)
    assert isinstance(path, Path)
    with Image.open(path) as image:
        assert image.getpixel((0, 0)) == (255, 240, 240, 255)
    path = save_figure(fig, tmp_path / "override.png", theme=override)
    assert isinstance(path, Path)
    with Image.open(path) as image:
        assert image.getpixel((0, 0)) == (238, 238, 255, 255)
    style_axes(ax)
    assert to_hex(spine.get_edgecolor()) == custom.axis


def test_native_styles_and_external_figures(tmp_path: Path) -> None:
    fig, ax = plt.subplots()
    assert get_theme(ax) is DEFAULT_THEME
    (line,) = ax.plot([1, 2], [2, 3], **get_theme(ax).line_style(markers=False, linewidth=4))
    assert line.get_linewidth() == 4
    assert line.get_marker() == "None"
    poly = ax.fill_between([1, 2], [0, 1], [2, 3], **get_theme(ax).band_style(alpha=0.5))
    assert poly.get_alpha() == 0.5
    active = DEFAULT_THEME.replace(axis="#705040")
    with theme_context(active):
        style_axes(ax)
    assert get_theme(fig) is DEFAULT_THEME
    out = save_figure(fig, tmp_path / "external.png")
    assert to_hex(ax.spines["bottom"].get_edgecolor()) == active.axis
    assert isinstance(out, Path)
    assert out.exists()


def test_precedence_and_isolation(tmp_path: Path) -> None:
    before = dict(matplotlib.rcParams)
    custom = DEFAULT_THEME.replace(figsize=(8, 7), dpi=120, tick_size=12)
    fig, ax = editorial_subplots(theme=custom, figsize=(7, 6), dpi=100)
    assert tuple(fig.get_size_inches()) == (7, 6)
    assert fig.dpi == 100
    assert get_theme(ax) is custom
    _, other = editorial_subplots(theme="report")
    assert get_theme(other) is REPORT_THEME
    style_axes(ax, unit="Index")
    plot_line(ax, [1, 2], [3, 4])
    save_figure(fig, tmp_path / "isolation.png")
    assert dict(matplotlib.rcParams) == before


def test_figure_lifetimes() -> None:
    def create() -> tuple[weakref.ReferenceType[plt.Figure], weakref.ReferenceType[plt.Axes]]:
        fig, ax = editorial_subplots(title="Lifetime")
        style_axes(ax, unit="Value")
        for _ in range(3):
            style_axes(ax)
        references = weakref.ref(fig), weakref.ref(ax)
        plt.close(fig)
        return references

    figures, axes = create()
    gc.collect()
    assert figures() is None
    assert axes() is None


def test_repeated_styling_preserves_user_artists_and_replaces_unit() -> None:
    _fig, ax = editorial_subplots()
    user_text = ax.annotate("User annotation", (0.5, 0.5))
    style_axes(ax, unit="First", xlabel="Year")
    style_axes(ax, unit="Second")
    style_axes(ax)
    assert [text.get_text() for text in ax.texts] == ["User annotation", "Second"]
    assert ax.get_xlabel() == "Year"
    style_axes(ax, unit="", xlabel="", grid=False)
    assert list(ax.texts) == [user_text]
    assert ax.get_xlabel() == ""
    assert not any(line.get_visible() for line in ax.get_ygridlines())
    ax.clear()
    style_axes(ax, unit="After clear")
    ax.set_ylim(0, 4)
    style_axes(ax, zero_baseline=True)
    assert to_hex(ax.spines["bottom"].get_edgecolor()) == DEFAULT_THEME.ink


def test_zero_baseline_autoscale_negative_and_explicit_limits() -> None:
    fig, ax = plt.subplots()
    ax.vlines([1, 2], 0, [5, 8])
    style_axes(ax, zero_baseline=True)
    assert ax.get_ylim()[0] == 0
    assert ax.get_autoscaley_on()
    ax.plot([1, 2], [-4, -2])
    ax.relim()
    ax.autoscale_view()
    finish(fig)
    assert ax.get_ylim()[0] < -4
    assert to_hex(ax.spines["bottom"].get_edgecolor()) == DEFAULT_THEME.axis
    ax.set_ylim(1e-10, 10)
    finish(fig)
    assert to_hex(ax.spines["bottom"].get_edgecolor()) == DEFAULT_THEME.axis
    ax.set_ylim(0, 10)
    finish(fig)
    assert to_hex(ax.spines["bottom"].get_edgecolor()) == DEFAULT_THEME.ink
    ax.set_ylim(10, -10)
    finish(fig)
    assert to_hex(ax.spines["bottom"].get_edgecolor()) == DEFAULT_THEME.axis


def test_custom_spine_position_cannot_imply_zero() -> None:
    _fig, ax = editorial_subplots()
    ax.plot([1, 2], [2, 3])
    ax.set_ylim(0, 5)
    ax.spines["bottom"].set_position(("axes", 0.5))
    style_axes(ax, zero_baseline=True)
    assert to_hex(ax.spines["bottom"].get_edgecolor()) == DEFAULT_THEME.axis


@pytest.mark.parametrize("canvas", [FigureCanvasSVG, FigureCanvasPdf])
def test_text_metrics_do_not_replace_vector_canvas(
    canvas: type[FigureCanvasSVG | FigureCanvasPdf],
) -> None:
    fig = plt.figure(figsize=(7.2, 9), dpi=170)
    original = canvas(fig)
    header(fig, "Render with the public metric API", "Explicit\nline breaks remain.")
    footer(fig, "Synthetic", signature="DataVerse")
    assert fig.canvas is original


def test_long_tokens_and_explicit_breaks_are_measured() -> None:
    fig = editorial_figure(title="Propriedades\n" + "área" * 30, figsize=(6, 9))
    fig.canvas.draw()
    title = next(t for t in fig.texts if t.get_gid() == "dataverse:header:title")
    assert title.get_text().startswith("Propriedades\n")
    assert title.get_text().count("\n") > 2
    assert (
        title.get_window_extent().width <= (6 * 72 - 2 * DEFAULT_THEME.margin_pt) * fig.dpi / 72 + 1
    )


def test_footer_stacks_long_signature_without_overlap() -> None:
    fig = plt.figure(figsize=(5, 7))
    footer(
        fig,
        "A source with enough detail to require several lines.",
        "An explicit methodological note.",
        signature="very-long-identifier-" * 6,
    )
    fig.canvas.draw()
    source = next(t for t in fig.texts if t.get_gid() == "dataverse:footer:text")
    signature = next(t for t in fig.texts if t.get_gid() == "dataverse:footer:signature")
    assert not source.get_window_extent().overlaps(signature.get_window_extent())
    assert signature.get_window_extent().x0 >= 0
    assert signature.get_window_extent().x1 <= fig.bbox.width


def test_custom_grid_and_native_raster_remain_accessible() -> None:
    fig = editorial_figure(title="Custom layout", figsize=(10, 7), compress=True)
    gs = fig.add_gridspec(2, 2)
    left = fig.add_subplot(gs[:, 0])
    upper = fig.add_subplot(gs[0, 1])
    lower = fig.add_subplot(gs[1, 1], projection="polar")
    left.imshow(np.arange(16).reshape(4, 4), extent=(0, 4, 0, 4))
    upper.bar([1, 2], [4, 5], color=get_theme(upper).accent)
    assert get_theme(lower) is DEFAULT_THEME
    assert len(fig.axes) == 3
    fig.set_size_inches(11, 8)
    finish(fig)
    fig.canvas.draw()


@pytest.mark.parametrize(
    "options",
    [
        {"figsize": (0, 4)},
        {"dpi": 0},
        {"dpi": float("nan")},
        {"theme": "missing"},
    ],
)
def test_invalid_figure_geometry_does_not_leak_figures(options: dict[str, object]) -> None:
    before = plt.get_fignums()
    with pytest.raises(ValueError):
        editorial_subplots(**options)  # type: ignore[arg-type]
    assert plt.get_fignums() == before


@pytest.mark.parametrize(
    "options",
    [
        {"dpi": 0},
        {"band_alpha": 2},
        {"paper": "no-such-colour"},
        {"title_size": -1},
        {"figsize": (5, float("inf"))},
        {"palette": ()},
        {"palette": ("not-a-colour",)},
    ],
)
def test_theme_validation(options: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        DEFAULT_THEME.replace(**options)


def test_invalid_subplot_native_options_and_bounds() -> None:
    with pytest.raises(ValueError, match="finish"):
        editorial_subplots(gridspec_kw={"left": 0.2})
    with pytest.raises(ValueError):
        editorial_subplots(nrows=0)


def test_native_keyword_aliases_override_defaults() -> None:
    _fig, ax = editorial_subplots()
    (line,) = plot_line(ax, [1, 2], [2, 3], lw=1, c="red", ms=4, mfc="blue", ls="--")
    assert line.get_linewidth() == 1
    assert line.get_color() == "red"
    assert line.get_markersize() == 4
    assert line.get_markerfacecolor() == "blue"
    band = plot_band(ax, [1, 2], [1, 2], [2, 3], fc="red", lw=0.5)
    assert to_hex(band.get_facecolor()[0]) == "#ff0000"
    assert band.get_linewidth()[0] == 0.5


def test_marker_choices_override_global_marker_defaults() -> None:
    with plt.rc_context({"lines.marker": "x", "lines.markeredgecolor": "red"}):
        _fig, ax = editorial_subplots()
        (plain,) = plot_line(ax, [1, 2], [2, 3], markers=False)
        (marked,) = plot_line(ax, [1, 2], [3, 4])
        assert plain.get_marker() == "None"
        assert to_hex(marked.get_markeredgecolor()) == DEFAULT_THEME.accent


def test_localised_footer_handles_other_translation_keys() -> None:
    fig = editorial_figure(source={"es": "Origen", "en_GB": "Chosen source"}, lang="en-GB")
    assert any("Source: Chosen source" in text.get_text() for text in fig.texts)


@pytest.mark.parametrize("formatter", [format_number, format_brl, number_formatter, brl_formatter])
@pytest.mark.parametrize(
    "decimals, exception", [(-1, ValueError), (1.5, TypeError), (True, TypeError)]
)
def test_precision_validation_is_immediate(
    formatter: Callable[..., object], decimals: object, exception: type[Exception]
) -> None:
    args = [] if formatter in {number_formatter, brl_formatter} else [1]
    with pytest.raises(exception, match="integer"):
        formatter(*args, decimals=decimals)


@pytest.mark.parametrize("lang", ["pt", "en"])
def test_rounding_nonfinite_and_exact_integer_digits(lang: str) -> None:
    before = locale.getlocale()
    assert format_number(-0.0, lang) == "0"
    assert format_number(-0.004, lang, 2) in {"0.00", "0,00"}
    assert format_number(2.5, lang) == "2"
    assert format_number(3.5, lang) == "4"
    assert format_number(float("nan"), lang) == "nan"
    assert format_number(float("inf"), lang) == "inf"
    assert format_number(float("-inf"), lang) == "-inf"
    assert format_brl(float("-inf"), lang).startswith("-R$")
    assert format_number(2**54 + 1, "en") == "18,014,398,509,481,985"
    assert locale.getlocale() == before


def test_export_transparency_dpi_bbox_and_lifecycle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fig, ax = editorial_subplots(figsize=(4, 3), title="Export")
    ax.plot([1, 2], [1, 2])
    size = tuple(fig.get_size_inches())
    shown = []
    monkeypatch.setattr(plt, "show", lambda: shown.append(True))
    with plt.rc_context({"savefig.bbox": "tight", "savefig.transparent": True}):
        path = save_figure(
            fig, tmp_path / "nested/canvas.png", dpi=100, transparent=True, show=True
        )
        assert plt.rcParams["savefig.bbox"] == "tight"
    assert isinstance(path, Path)
    with Image.open(path) as image:
        assert image.size == (400, 300)
        assert image.getpixel((0, 0))[3] == 0  # type: ignore[index]
    assert shown == [True]
    assert plt.fignum_exists(fig.number)
    assert tuple(fig.get_size_inches()) == size
    path = save_figure(fig, tmp_path / "opaque", facecolor="#123456", close=True)
    assert isinstance(path, Path)
    assert path.suffix == ".png"
    with Image.open(path) as image:
        assert image.getpixel((0, 0)) == (18, 52, 86, 255)
    assert not plt.fignum_exists(fig.number)


@pytest.mark.parametrize(
    "options",
    [
        {"formats": []},
        {"formats": ["png", ".PNG"]},
        {"formats": ["png", "jpg"]},
        {"dpi": 0},
        {"dpi": float("nan")},
        {"format": "png"},
    ],
)
def test_invalid_export_does_not_create_directories(
    tmp_path: Path, options: dict[str, object]
) -> None:
    fig = plt.figure()
    destination = tmp_path / "new/file.png"
    with pytest.raises(ValueError):
        save_figure(fig, destination, **options)  # type: ignore[arg-type]
    assert not destination.parent.exists()
