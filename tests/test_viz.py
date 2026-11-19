"""Unit and geometry tests for ``dataverse_style``."""

from __future__ import annotations

import dataclasses
import locale
import subprocess
import sys
import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.colors import to_hex, to_rgb, to_rgba
from PIL import Image

from dataverse_style import (
    DEFAULT_THEME,
    LANDSCAPE_THEME,
    REPORT_THEME,
    THEMES,
    Theme,
    brl_formatter,
    editorial_subplots,
    ensure_fonts,
    finish,
    format_brl,
    format_number,
    number_formatter,
    plot_band,
    plot_line,
    register_fonts,
    resolve_font_family,
    save_figure,
    style_axes,
    theme_context,
    use,
)

PAPER, INK, SUBTLE, MUTED = "#fbfaf7", "#1f1f1f", "#4a4a48", "#6b6b6b"
RULE, AXIS, GREY, ACCENT = "#dcd8cf", "#8f8b83", "#b4b0a8", "#0f766e"
POST_SIZE, POST_DPI = (7.2, 9.0), 150
LANDSCAPE_SIZE, LANDSCAPE_DPI = (9.0, 6.0), 200
REPORT_SIZE, REPORT_DPI = (6.5, 4.5), 300


def _relative_luminance(colour: str) -> float:
    """Compute WCAG 2.1 relative luminance for a Matplotlib colour."""
    r, g, b = to_rgb(colour)

    def _channel(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)


def _contrast_ratio(c1: str, c2: str) -> float:
    """Compute WCAG 2.1 contrast ratio between two colours."""
    l1, l2 = _relative_luminance(c1), _relative_luminance(c2)
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def test_import_has_no_side_effects(tmp_path: Path) -> None:
    """Importing ``dataverse_style`` must not touch rcParams, disk or network."""
    code = """
import os
import sys
import socket
import urllib.request
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

def _forbid_network(*args, **kwargs):
    raise AssertionError("Network access attempted during import!")

urllib.request.urlretrieve = _forbid_network
urllib.request.urlopen = _forbid_network
socket.create_connection = _forbid_network
socket.socket.connect = _forbid_network
before_rc = dict(plt.rcParams)
sys.dont_write_bytecode = True

def forbid_writes(event, args):
    if event == "open" and args[2] & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC):
        raise AssertionError("File write attempted during import")
    if event in {"os.mkdir", "os.remove", "os.rename"}:
        raise AssertionError("Filesystem mutation attempted during import")

sys.addaudithook(forbid_writes)

import dataverse_style

after_rc = dict(plt.rcParams)
assert before_rc == after_rc, "rcParams mutated on import"
"""
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, f"Subprocess failed: {proc.stderr}"
    assert list(tmp_path.iterdir()) == []


def test_default_theme_is_immutable() -> None:
    """Attempting to mutate ``DEFAULT_THEME`` must raise ``FrozenInstanceError``."""
    with pytest.raises(dataclasses.FrozenInstanceError):
        DEFAULT_THEME.accent = "#ff0000"  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        DEFAULT_THEME.margin_pt = 40.0  # type: ignore[misc]


def test_theme_defaults_match_house_palette() -> None:
    """Default theme constants must match the DataVerse specification."""
    assert DEFAULT_THEME.paper == PAPER == "#fbfaf7"
    assert DEFAULT_THEME.ink == INK == "#1f1f1f"
    assert DEFAULT_THEME.subtle == SUBTLE == "#4a4a48"
    assert DEFAULT_THEME.muted == MUTED == "#6b6b6b"
    assert DEFAULT_THEME.rule == RULE == "#dcd8cf"
    assert DEFAULT_THEME.axis == AXIS == "#8f8b83"
    assert DEFAULT_THEME.context == GREY == "#b4b0a8"
    assert DEFAULT_THEME.accent == ACCENT == "#0f766e"
    assert DEFAULT_THEME.title_font == "IBM Plex Serif"
    assert DEFAULT_THEME.text_font == "IBM Plex Sans"
    assert THEMES["social"] is DEFAULT_THEME
    assert THEMES["landscape"] is LANDSCAPE_THEME
    assert THEMES["report"] is REPORT_THEME


def test_palette_and_wcag_contrast() -> None:
    """Palette starts with accent and every entry has >= 3:1 contrast against paper."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        theme = use()
    cycle_colors = plt.rcParams["axes.prop_cycle"].by_key()["color"]
    assert cycle_colors[0] == theme.palette[0] == theme.accent
    assert tuple(cycle_colors) == theme.palette
    for colour in theme.palette:
        assert _contrast_ratio(colour, theme.paper) >= 3.0


def test_theme_replace_is_independent() -> None:
    """Theme.replace produces an independent Theme instance."""
    custom = DEFAULT_THEME.replace(accent="#b91c1c", title_size=24.0, context="#999999")
    assert custom.accent == "#b91c1c"
    assert custom.title_size == 24.0
    assert custom.context == "#999999"
    assert DEFAULT_THEME.accent == "#0f766e"
    assert DEFAULT_THEME.title_size == 20.0
    assert DEFAULT_THEME.context == "#b4b0a8"
    with pytest.raises(TypeError):
        custom.replace(grey="#777777")


def test_theme_context_and_use_manage_rcparams() -> None:
    """``theme_context`` and ``use`` must manage ``rcParams`` and active theme predictably."""
    original_facecolor = plt.rcParams["figure.facecolor"]
    custom = Theme(paper="#123456")
    with theme_context(custom) as active:
        assert active is custom
        assert plt.rcParams["figure.facecolor"] == "#123456"
        assert plt.rcParams["axes.facecolor"] == "#123456"
    assert plt.rcParams["figure.facecolor"] == original_facecolor

    with plt.rc_context(), warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        returned = use("report")
        assert returned is REPORT_THEME
        assert plt.rcParams["axes.labelsize"] == REPORT_THEME.label_size


def test_format_number_pt_and_en() -> None:
    """``format_number`` must format integers and decimals in PT and EN without locale changes."""
    loc_before = locale.getlocale()

    assert format_number(5000, "pt") == "5.000"
    assert format_number(5000, "en") == "5,000"
    assert format_number(1234567.89, "pt", decimals=2) == "1.234.567,89"
    assert format_number(1234567.89, "en", decimals=2) == "1,234,567.89"
    assert format_number(-42000, "pt") == "-42.000"
    assert format_number(-42000, "en") == "-42,000"
    assert format_number(-0.0001, "pt", decimals=0) == "0"
    assert format_number(1000, "pt-BR") == "1.000"
    assert format_number(1000, "en_US") == "1,000"

    assert locale.getlocale() == loc_before


def test_format_brl_pt_and_en() -> None:
    """``format_brl`` must respect the Portuguese space convention after ``R$``."""
    assert format_brl(5000, "pt") == "R$ 5.000"
    assert format_brl(5000, "en") == "R$5,000"
    assert format_brl(2900.5, "pt", decimals=2) == "R$ 2.900,50"
    assert format_brl(2900.5, "en", decimals=2) == "R$2,900.50"
    assert format_brl(-1500, "pt") == "-R$ 1.500"
    assert format_brl(-1500, "en") == "-R$1,500"
    assert format_brl(-0.0001, "pt") == "R$ 0"


def test_format_validation_errors() -> None:
    """Invalid language codes or negative decimals must raise ``ValueError``."""
    with pytest.raises(ValueError, match="Unsupported language"):
        format_number(100, "es")
    with pytest.raises(ValueError, match="non-negative"):
        format_number(100, "en", decimals=-1)


def test_tick_formatters_on_axes() -> None:
    """``number_formatter`` and ``brl_formatter`` must work as Matplotlib tick formatters."""
    _fig, ax = plt.subplots()
    y_fmt = number_formatter("pt", decimals=0)
    x_fmt = brl_formatter("en", decimals=0)
    ax.yaxis.set_major_formatter(y_fmt)
    ax.xaxis.set_major_formatter(x_fmt)

    assert y_fmt(35000, 0) == "35.000"
    assert x_fmt(4100, 0) == "R$4,100"


@pytest.mark.parametrize(
    ("lang", "currency", "ticks", "expected"),
    [
        (
            "pt",
            True,
            [0, 200_000, 400_000, 600_000, 800_000],
            ["R$ 0", "R$ 200 mil", "R$ 400 mil", "R$ 600 mil", "R$ 800 mil"],
        ),
        (
            "pt",
            True,
            [0, 200_000, 400_000, 600_000, 800_000, 1_000_000],
            ["R$ 0", "R$ 0,2 mi", "R$ 0,4 mi", "R$ 0,6 mi", "R$ 0,8 mi", "R$ 1,0 mi"],
        ),
        (
            "pt",
            True,
            [1.0e6, 1.2e6, 1.4e6],
            ["R$ 1,0 mi", "R$ 1,2 mi", "R$ 1,4 mi"],
        ),
        (
            "en",
            True,
            [1.0e6, 1.2e6, 1.4e6],
            ["R$1.0m", "R$1.2m", "R$1.4m"],
        ),
        (
            "en",
            True,
            [0, 800_000],
            ["R$0", "R$800k"],
        ),
        (
            "pt",
            True,
            [-1_200_000_000, -1_000_000_000, 0, 3_000_000_000],
            ["-R$ 1,2 bi", "-R$ 1,0 bi", "R$ 0", "R$ 3,0 bi"],
        ),
        (
            "en",
            True,
            [-1_200_000_000, -1_000_000_000, 0, 3_000_000_000],
            ["-R$1.2bn", "-R$1.0bn", "R$0", "R$3.0bn"],
        ),
        (
            "pt",
            True,
            [0, 3_000_000_000],
            ["R$ 0", "R$ 3 bi"],
        ),
        (
            "en",
            True,
            [0, 3_000_000_000],
            ["R$0", "R$3bn"],
        ),
        (
            "pt",
            False,
            [1_000_000, 1_050_000, 1_100_000],
            ["1,00 mi", "1,05 mi", "1,10 mi"],
        ),
        (
            "en",
            False,
            [0, 100, 200],
            ["0", "100", "200"],
        ),
    ],
)
def test_compact_formatters_table(
    lang: str,
    currency: bool,
    ticks: list[float],
    expected: list[str],
) -> None:
    """Test 10: Compact formatters choose one scale per axis and uniform minimal decimals."""
    from matplotlib.ticker import Formatter, FuncFormatter

    fmt = brl_formatter(lang, compact=True) if currency else number_formatter(lang, compact=True)
    assert isinstance(fmt, Formatter)
    assert not isinstance(fmt, FuncFormatter)
    actual = fmt.format_ticks(ticks)
    assert actual == expected
    assert len(set(actual)) == len(set(ticks))


def test_compact_formatter_single_value_call() -> None:
    """Single-value cursor readout uses standalone scale or last format_ticks scale."""
    fmt_pt = brl_formatter("pt", compact=True)
    assert fmt_pt(800_000, 0) == "R$ 800 mil"
    assert fmt_pt(1_200_000, 0) == "R$ 1,2 mi"
    assert fmt_pt(3_000_000_000, 0) == "R$ 3 bi"
    assert fmt_pt(-500_000, 0) == "-R$ 500 mil"
    assert fmt_pt(0, 0) == "R$ 0"

    # After format_ticks chooses the million scale with 1 decimal place:
    fmt_pt.format_ticks([0, 200_000, 400_000, 600_000, 800_000, 1_000_000])
    assert fmt_pt(500_000, 0) == "R$ 0,5 mi"


def test_missing_font_fallback_and_use_warning() -> None:
    """``use()`` warns once when preferred fonts are missing; rendering emits no findfont logs."""
    resolved = resolve_font_family("NonExistentDataVerseFontXYZ", ("DejaVu Sans", "sans-serif"))
    assert resolved in {"DejaVu Sans", "sans-serif"}

    missing_theme = DEFAULT_THEME.replace(
        title_font="MissingTitleSerifXYZ",
        text_font="MissingBodySansXYZ",
    )
    with pytest.warns(UserWarning, match="register_fonts"):
        use(missing_theme)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        fig, ax = editorial_subplots(
            title="Headline with missing font",
            subtitle="Subtitle with missing font",
            source="Test source",
            note="Test note",
            signature="example.org",
            theme=missing_theme,
        )
        ax.plot([0, 1], [10, 20])
        style_axes(ax, "Units", theme=missing_theme)
        fig.canvas.draw()

    findfont_warnings = [w for w in caught if "findfont" in str(w.message)]
    assert findfont_warnings == []


def test_register_and_ensure_fonts_local_only(tmp_path: Path) -> None:
    """``register_fonts`` and ``ensure_fonts(download=False)`` must not fail on missing dirs."""
    missing_dir = tmp_path / "does_not_exist"
    assert register_fonts(missing_dir) == []
    assert ensure_fonts(missing_dir, download=False) == []
    assert not missing_dir.exists()


@pytest.mark.parametrize(
    ("theme_name", "expected_size", "expected_dpi", "expected_px"),
    [
        ("social", POST_SIZE, POST_DPI, (1080, 1350)),
        ("landscape", LANDSCAPE_SIZE, LANDSCAPE_DPI, (1800, 1200)),
        ("report", REPORT_SIZE, REPORT_DPI, (1950, 1350)),
    ],
)
def test_named_themes_and_exact_pixel_sizes(
    theme_name: str,
    expected_size: tuple[float, float],
    expected_dpi: int,
    expected_px: tuple[int, int],
    tmp_path: Path,
) -> None:
    """Named themes configure size and DPI and export exact rounded pixel dimensions."""
    fig, ax = editorial_subplots(
        title="Theme layout verification",
        subtitle="Checking dimensions and plot bounds across publication themes.",
        source="Synthetic test data.",
        note="Methodological note for layout testing.",
        signature="DataVerse",
        theme=theme_name,
    )
    ax.plot([0, 1], [0, 10])
    style_axes(ax, "Units")
    assert tuple(fig.get_size_inches()) == pytest.approx(expected_size)
    assert fig.dpi == expected_dpi
    out = save_figure(fig, tmp_path / f"{theme_name}.png")
    assert isinstance(out, Path)
    with Image.open(out) as img:
        assert img.size == expected_px


@pytest.mark.parametrize("theme_name", ["social", "landscape", "report"])
@pytest.mark.parametrize(("nrows", "ncols"), [(1, 1), (1, 2), (2, 2)])
@pytest.mark.parametrize("fmt_mode", ["plain", "brl", "brl_compact"])
@pytest.mark.parametrize("has_xlabel", [False, True])
def test_nothing_leaves_page_box_and_header_footer_separation(
    theme_name: str,
    nrows: int,
    ncols: int,
    fmt_mode: str,
    has_xlabel: bool,
    tmp_path: Path,
) -> None:
    """Tests 1 & 2: Every visible text and axes tight bbox stays in the page and plot region."""
    theme = THEMES[theme_name]
    fig, axes = editorial_subplots(
        nrows,
        ncols,
        title="Headline finding that wraps cleanly inside the page margin",
        subtitle="Context line detailing the unit, scope and period from 2016 to 2025.",
        source="Prefeitura Municipal.",
        note="Methodological note explaining the series.",
        signature="DataVerse",
        lang="pt",
        theme=theme,
        squeeze=False,
    )
    for idx, ax in enumerate(axes.flat):
        ax.plot([2020, 2022, 2025], [0, 600_000, 1_200_000])
        if fmt_mode == "brl":
            ax.yaxis.set_major_formatter(brl_formatter("pt"))
        elif fmt_mode == "brl_compact":
            ax.yaxis.set_major_formatter(brl_formatter("pt", compact=True))
        style_axes(
            ax,
            unit=f"R$ ({idx + 1})",
            xlabel="Ano" if has_xlabel and idx >= (nrows - 1) * ncols else None,
        )

    save_figure(fig, tmp_path / "bound_check.png", pil_kwargs={"compress_level": 1})
    renderer = fig.canvas.get_renderer()  # type: ignore[attr-defined]
    scale = 72.0 / float(fig.dpi)
    width_pt, height_pt = (float(v) * 72.0 for v in fig.get_size_inches())

    # Measure header bottom and footer top from the managed artists.
    subtitle_artist = next(t for t in fig.texts if t.get_gid() == "dataverse:header:subtitle")
    h_bottom_pt = float(subtitle_artist.get_window_extent(renderer).y0) * scale
    footer_rule = next(a for a in fig.artists if a.get_gid() == "dataverse:footer:rule")
    f_top_pt = float(footer_rule.get_window_extent(renderer).y1) * scale

    for text in fig.texts:
        if not text.get_visible() or not text.get_text().strip():
            continue
        ext = text.get_window_extent(renderer)
        assert float(ext.x0) * scale >= theme.margin_pt - 0.5
        assert float(ext.x1) * scale <= width_pt - theme.margin_pt + 0.5
        assert float(ext.y0) * scale >= 0.0
        assert float(ext.y1) * scale <= height_pt

    for ax in axes.flat:
        tb = ax.get_tightbbox(renderer)
        assert tb is not None
        assert float(tb.x0) * scale >= theme.margin_pt - 0.5
        assert float(tb.x1) * scale <= width_pt - theme.margin_pt + 0.5
        assert float(tb.y1) * scale <= h_bottom_pt - theme.header_gap_pt + 0.5
        assert float(tb.y0) * scale >= f_top_pt + theme.footer_gap_pt - 0.5


def test_finish_idempotence() -> None:
    """Test 6: Two consecutive finish() calls yield identical axes positions and artist counts."""
    fig, axes = editorial_subplots(
        1,
        2,
        title="Idempotence check",
        subtitle="Two panels with different tick widths.",
        source="Synthetic",
        signature="DataVerse",
    )
    axes[0].plot([0, 1], [0, 1_200_000])
    axes[0].yaxis.set_major_formatter(brl_formatter("pt"))
    style_axes(axes[0], "R$")
    axes[1].plot([0, 1], [0, 50])
    style_axes(axes[1], "Share")

    finish(fig)
    pos1 = [ax.get_position().bounds for ax in axes]
    count1 = len(fig.texts) + len(fig.artists)

    finish(fig)
    pos2 = [ax.get_position().bounds for ax in axes]
    count2 = len(fig.texts) + len(fig.artists)

    assert count1 == count2
    width_pt, height_pt = (float(v) * 72.0 for v in fig.get_size_inches())
    for b1, b2 in zip(pos1, pos2, strict=True):
        assert abs(b1[0] - b2[0]) * width_pt <= 0.01
        assert abs(b1[1] - b2[1]) * height_pt <= 0.01
        assert abs(b1[2] - b2[2]) * width_pt <= 0.01
        assert abs(b1[3] - b2[3]) * height_pt <= 0.01


def test_resize_rewraps_and_stays_in_bounds(tmp_path: Path) -> None:
    """Test 7: Resizing followed by save_figure rewraps header text and keeps all bounds valid."""
    long_title = (
        "A deliberately long editorial headline that wraps differently when the figure "
        "width changes from portrait to landscape dimensions"
    )
    fig, ax = editorial_subplots(
        title=long_title,
        subtitle="Supporting subtitle text for the resize test.",
        source="Synthetic source.",
        note="Methodological note.",
        signature="DataVerse",
    )
    ax.plot([0, 1, 2], [0, 500_000, 1_000_000])
    ax.yaxis.set_major_formatter(brl_formatter("pt"))
    style_axes(ax, unit="R$", xlabel="Ano")

    title_before = next(t for t in fig.texts if t.get_gid() == "dataverse:header:title").get_text()
    fig.set_size_inches(9, 6)
    save_figure(fig, tmp_path / "resized.png")
    fig.canvas.draw()
    title_after = next(t for t in fig.texts if t.get_gid() == "dataverse:header:title").get_text()
    assert title_after.count("\n") <= title_before.count("\n")

    renderer = fig.canvas.get_renderer()  # type: ignore[attr-defined]
    scale = 72.0 / float(fig.dpi)
    width_pt, height_pt = (float(v) * 72.0 for v in fig.get_size_inches())
    tb = ax.get_tightbbox(renderer)
    assert tb is not None
    assert float(tb.x0) * scale >= DEFAULT_THEME.margin_pt - 0.5
    assert float(tb.x1) * scale <= width_pt - DEFAULT_THEME.margin_pt + 0.5
    assert 0.0 <= float(tb.y0) * scale < float(tb.y1) * scale <= height_pt


def test_unit_labels_align_with_tick_columns_in_both_columns() -> None:
    """Unit labels align with the left edge of their own axes' y tick labels in a 1x2 grid."""
    fig, (ax_left, ax_right) = editorial_subplots(
        1, 2, gridspec_kw={"wspace": 0.08}, title="Side by side"
    )
    ax_left.plot([0, 1], [0, 1_000_000])
    ax_left.yaxis.set_major_formatter(brl_formatter("pt"))
    ax_right.plot([0, 1], [0, 500])
    style_axes(ax_left, "Left unit")
    style_axes(ax_right, "Right unit")
    finish(fig)
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()  # type: ignore[attr-defined]
    scale = 72.0 / float(fig.dpi)

    for ax in (ax_left, ax_right):
        ytb = ax.yaxis.get_tightbbox(renderer)
        assert ytb is not None
        unit_artist = next(t for t in ax.texts if t.get_gid() == "dataverse:axes:unit")
        u_x0 = float(unit_artist.get_window_extent(renderer).x0) * scale
        y_x0 = float(ytb.x0) * scale
        assert u_x0 == pytest.approx(y_x0, abs=0.5)


def test_zero_baseline_strict_enforcement() -> None:
    """Dark baseline must only appear when the y-axis actually starts at zero."""
    _fig, ax = plt.subplots()
    ax.bar([1, 2, 3], [5, 10, 15])
    style_axes(ax, "Units", zero_baseline=True)
    assert to_hex(ax.spines["bottom"].get_edgecolor()) == INK
    assert ax.spines["bottom"].get_linewidth() == pytest.approx(1.0)

    _fig2, ax2 = plt.subplots()
    ax2.plot([1, 2, 3], [80, 90, 95])
    ax2.set_ylim(75, 100)
    style_axes(ax2, "Index", zero_baseline=True)
    assert to_hex(ax2.spines["bottom"].get_edgecolor()) == AXIS
    assert ax2.spines["bottom"].get_linewidth() == pytest.approx(0.8)

    _fig3, ax3 = plt.subplots()
    ax3.set_ylim(0, 100)
    style_axes(ax3, zero_baseline=False)
    assert to_hex(ax3.spines["bottom"].get_edgecolor()) == AXIS
    assert ax3.spines["bottom"].get_linewidth() == pytest.approx(0.8)


def test_plot_line_and_plot_band_styles() -> None:
    """``plot_line`` and ``plot_band`` must apply house defaults and accept overrides."""
    _fig, ax = plt.subplots()
    x = [1, 2, 3]
    poly = plot_band(ax, x, [8, 18, 28], [12, 22, 32])
    lines = plot_line(ax, x, [10, 20, 30])

    assert len(lines) == 1
    line = lines[0]
    assert to_hex(line.get_color()) == ACCENT
    assert line.get_linewidth() == pytest.approx(DEFAULT_THEME.line_width)
    assert line.get_marker() == "o"
    assert to_hex(line.get_markerfacecolor()) == PAPER

    fc = poly.get_facecolor()[0]
    assert fc == pytest.approx(to_rgba(ACCENT, DEFAULT_THEME.band_alpha))


def test_save_figure_exact_dimensions_and_formats(tmp_path: Path) -> None:
    """``save_figure`` must preserve exact pixel dimensions and export PNG, SVG and PDF."""
    fig, ax = editorial_subplots(
        title="Export test",
        subtitle="Checking exact pixel dimensions for social media portrait theme.",
        source="Test suite.",
        theme="social",
    )
    plot_line(ax, [0, 1, 2], [2, 5, 3])
    style_axes(ax, "Value")

    png_path = save_figure(fig, tmp_path / "social_chart.png")
    assert isinstance(png_path, Path)
    assert png_path.exists()

    with Image.open(png_path) as img:
        assert img.size == (1080, 1350)
        r, g, b = img.convert("RGB").getpixel((5, 5))  # type: ignore[misc]
        assert to_hex((r / 255, g / 255, b / 255)) == PAPER

    multi_paths = save_figure(
        fig,
        tmp_path / "multi_export",
        formats=("png", "svg", "pdf"),
        close=True,
    )
    assert isinstance(multi_paths, list)
    assert [p.suffix for p in multi_paths] == [".png", ".svg", ".pdf"]
    for p in multi_paths:
        assert p.exists()
        assert p.stat().st_size > 0


def test_visual_determinism_across_renders(tmp_path: Path) -> None:
    """Rendering the same editorial figure twice must produce identical pixel arrays."""

    def _render(path: Path) -> np.ndarray:
        fig, ax = editorial_subplots(
            title="Deterministic visual check",
            subtitle="Comparing rendered pixel arrays across runs.",
            source="DataVerse test suite.",
            note="Synthetic series with uncertainty band.",
            signature="DataVerse",
            lang="en",
        )
        x = np.arange(0, 10)
        y = 100 + 5 * x
        plot_band(ax, x, y - 4, y + 4)
        plot_line(ax, x, y)
        style_axes(ax, "Index (2016 = 100)", xlabel="Year")
        ax.yaxis.set_major_formatter(number_formatter("en"))
        save_figure(fig, path, close=True)
        with Image.open(path) as im:
            return np.asarray(im)

    img1 = _render(tmp_path / "render_1.png")
    img2 = _render(tmp_path / "render_2.png")
    assert img1.shape == (1350, 1080, 4)
    assert np.array_equal(img1, img2)
