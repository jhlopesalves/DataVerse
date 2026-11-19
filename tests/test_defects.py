"""Regression tests for verified rendering and formatting defects."""

from __future__ import annotations

import math
import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import pytest
from matplotlib.colors import to_hex

from dataverse_style import (
    DEFAULT_THEME,
    brl_formatter,
    editorial_figure,
    editorial_subplots,
    finish,
    footer,
    get_theme,
    header,
    number_formatter,
    save_figure,
    style_axes,
    use,
)


def test_d1_ytick_labels_not_clipped(tmp_path: Path) -> None:
    """D1: Long BRL y-tick labels must not be clipped off the left edge of the canvas."""
    fig, ax = editorial_subplots(title="Headline", source="PBH")
    ax.plot([0, 1], [0, 1_000_000])
    ax.yaxis.set_major_formatter(brl_formatter("pt"))
    ax.set_ylim(0, None)
    style_axes(ax, unit="R$")
    save_figure(fig, tmp_path / "d1.png")
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()  # type: ignore[attr-defined]
    scale = 72.0 / float(fig.dpi)
    x0s = [
        float(lbl.get_window_extent(renderer).x0) * scale
        for lbl in ax.get_yticklabels()
        if lbl.get_visible() and lbl.get_text().strip()
    ]
    assert min(x0s) >= DEFAULT_THEME.margin_pt - 0.5


def test_d2_artists_created_after_figure_use_theme() -> None:
    """D2: Native artists created after figure creation must follow the active theme."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        theme = use()
    _fig, ax = editorial_subplots(title="Headline", source="PBH")
    ax.plot([0, 1], [0, 1], label="First")
    (second_line,) = ax.plot([0, 1], [1, 2], label="Second")
    txt = ax.text(0.5, 0.5, "Direct text")
    ann = ax.annotate("Direct annotation", (0.5, 0.5))
    leg = ax.legend()

    resolved_font = theme.resolved_text_font()
    assert txt.get_fontfamily()[0] == resolved_font
    assert ann.get_fontfamily()[0] == resolved_font
    assert leg.get_texts()[0].get_fontfamily()[0] == resolved_font
    assert to_hex(txt.get_color()) == theme.ink
    assert to_hex(ann.get_color()) == theme.ink
    assert not leg.get_frame().get_visible()
    assert to_hex(leg.get_texts()[0].get_color()) == theme.subtle
    assert to_hex(second_line.get_color()) == theme.palette[1]


def test_d3_footer_label_not_duplicated() -> None:
    """D3: Footer must replace a recognised source/note prefix in either language."""
    fig = plt.figure()
    footer(fig, source="Source: PBH", note="Nota: Valores nominais", lang="pt")
    footer_text = next(t for t in fig.texts if t.get_gid() == "dataverse:footer:text").get_text()
    assert "Fonte: PBH" in footer_text
    assert "Fonte: Source:" not in footer_text


@pytest.mark.parametrize("source_prefix", ["Source:", "Fonte:", "source:"])
@pytest.mark.parametrize("note_prefix", ["Note:", "Nota:"])
@pytest.mark.parametrize("lang", ["pt", "en"])
def test_footer_label_combinations(source_prefix: str, note_prefix: str, lang: str) -> None:
    """Test 9: Every combination of recognised source/note prefixes and lang renders one label."""
    fig = plt.figure()
    footer(
        fig,
        source=f"{source_prefix} Municipal records",
        note=f"{note_prefix} Nominal values",
        lang=lang,
    )
    footer_text = next(t for t in fig.texts if t.get_gid() == "dataverse:footer:text").get_text()
    expected_source = "Fonte: Municipal records" if lang == "pt" else "Source: Municipal records"
    expected_note = "Nota: Nominal values" if lang == "pt" else "Note: Nominal values"
    assert footer_text == f"{expected_source}\n{expected_note}"


def test_replaced_header_and_footer_persist_through_resize_and_export(tmp_path: Path) -> None:
    fig = editorial_figure(title="Original title", subtitle="Original subtitle", source="Old")
    override = DEFAULT_THEME.replace(ink="#445566", muted="#705040")
    title = "An updated title that can fit across the wide figure but wraps on the narrow one"
    header(fig, title, "Updated subtitle", accent_bar=False, theme=override)
    footer(
        fig,
        source={"en": "Local records", "pt": "Registros locais"},
        note="Nota: Valores nominais",
        signature="DataVerse",
        lang="pt-BR",
        theme=override,
        rule=False,
    )
    native = fig.text(0.5, 0.5, "Native label")

    finish(fig)
    texts = {t.get_gid(): t for t in fig.texts}
    before = texts["dataverse:header:title"].get_text()
    assert " ".join(before.split()) == title
    assert texts["dataverse:header:subtitle"].get_text() == "Updated subtitle"
    assert (
        texts["dataverse:footer:text"].get_text()
        == "Fonte: Registros locais\nNota: Valores nominais"
    )
    assert texts["dataverse:footer:signature"].get_text() == "DataVerse"
    assert get_theme(fig) is DEFAULT_THEME

    fig.set_size_inches(4, 9)
    out = tmp_path / "updated.svg"
    with plt.rc_context({"svg.fonttype": "path"}):
        save_figure(fig, out)
    texts = {t.get_gid(): t for t in fig.texts}
    after = texts["dataverse:header:title"].get_text()
    assert " ".join(after.split()) == title
    assert after.count("\n") > before.count("\n")
    assert to_hex(texts["dataverse:header:title"].get_color()) == override.ink
    assert to_hex(texts["dataverse:footer:text"].get_color()) == override.muted
    assert native in fig.texts
    assert not fig.artists
    svg = out.read_text()
    assert all(text in svg for text in ("Updated subtitle", "Registros locais", "DataVerse"))
    assert "Original title" not in svg


def test_decorations_can_be_added_or_cleared_on_managed_figures() -> None:
    fig = editorial_figure()
    assert not fig.artists
    header(fig, "")
    footer(fig)
    finish(fig)
    assert {artist.get_gid() for artist in fig.artists} == {
        "dataverse:header:accent",
        "dataverse:footer:rule",
    }

    header(fig, "", accent_bar=False)
    footer(fig, rule=False)
    finish(fig)
    assert not fig.artists
    assert not fig.texts


@pytest.mark.parametrize(
    ("lang", "expected"),
    [
        ("en", ["1.0000m", "1.0001m", "1.0002m"]),
        ("pt", ["1,0000 mi", "1,0001 mi", "1,0002 mi"]),
    ],
)
def test_compact_axis_adds_precision_when_ticks_are_close(lang: str, expected: list[str]) -> None:
    _, ax = plt.subplots()
    ticks = [1_000_000, 1_000_100, 1_000_200]
    ax.set_yticks(ticks)
    formatter = number_formatter(lang, compact=True)
    ax.yaxis.set_major_formatter(formatter)
    assert [label.get_text() for label in ax.get_yticklabels()] == expected
    assert [formatter(value) for value in ticks] == expected


@pytest.mark.parametrize(
    ("lang", "fractional", "unscaled"),
    [
        ("en", ["-0.003", "-0.002", "0.001"], ["-R$1,000,000.01", "-R$1,000,000.00"]),
        ("pt", ["-0,003", "-0,002", "0,001"], ["-R$ 1.000.000,01", "-R$ 1.000.000,00"]),
    ],
)
def test_compact_axis_fractional_and_unscaled_labels(
    lang: str, fractional: list[str], unscaled: list[str]
) -> None:
    assert number_formatter(lang, compact=True).format_ticks([-0.003, -0.002, 0.001]) == fractional
    assert brl_formatter(lang, compact=True).format_ticks([-1_000_000.01, -1_000_000]) == unscaled


@pytest.mark.parametrize("lang", ["pt", "en"])
def test_compact_axis_uses_scientific_notation_for_nearly_equal_tiny_ticks(lang: str) -> None:
    formatter = number_formatter(lang, compact=True)
    base = 1e-10
    ticks = [0.0, base, math.nextafter(base, math.inf)]
    labels = formatter.format_ticks(ticks)
    assert labels[0] == "0"
    assert all("e-10" in label for label in labels[1:])
    assert [float(label.replace(",", ".")) for label in labels] == ticks
    assert [formatter(value) for value in ticks] == labels


def test_zero_baseline_follows_native_draw_and_savefig(tmp_path: Path) -> None:
    fig, ax = plt.subplots()
    ax.bar([1, 2], [6, 9])
    style_axes(ax)
    spine = ax.spines["bottom"]
    spine.set_gid("tested-baseline")
    assert to_hex(spine.get_edgecolor()) == DEFAULT_THEME.ink

    ax.set_ylim(1, 10)
    fig.canvas.draw()
    assert to_hex(spine.get_edgecolor()) == DEFAULT_THEME.axis

    ax.set_ylim(0, 10, emit=False)
    fig.canvas.draw()
    assert to_hex(spine.get_edgecolor()) == DEFAULT_THEME.ink

    ax.set_yscale("symlog")
    fig.canvas.draw()
    assert to_hex(spine.get_edgecolor()) == DEFAULT_THEME.axis
    ax.set_yscale("linear")
    fig.canvas.draw()
    assert to_hex(spine.get_edgecolor()) == DEFAULT_THEME.ink

    spine.set_position(("axes", 0.5))
    path = tmp_path / "native.svg"
    fig.savefig(path)
    svg_spine = path.read_text().split('<g id="tested-baseline">', 1)[1].split("</g>", 1)[0]
    assert f"stroke: {DEFAULT_THEME.axis}" in svg_spine
    assert spine.get_linewidth() == pytest.approx(DEFAULT_THEME.spine_width)


def test_zero_baseline_anchoring_preserves_negative_data_on_shared_axes() -> None:
    fig, (positive, negative) = plt.subplots(1, 2, sharey=True)
    positive.vlines([1, 2], 0, [5, 10])
    negative.plot([1, 2], [-3, -1])
    style_axes(positive, zero_baseline=True)
    finish(fig)
    assert positive.get_ylim() == negative.get_ylim()
    assert positive.get_ylim()[0] < -3
    assert to_hex(positive.spines["bottom"].get_edgecolor()) == DEFAULT_THEME.axis


def test_zero_baseline_reapplied_at_save(tmp_path: Path) -> None:
    """Test 8: Zero baseline covers bars, negatives, post-style set_ylim, False and True."""
    # Bars from 0 -> dark spine
    _fig1, ax1 = editorial_subplots()
    ax1.bar([1, 2, 3], [5, 10, 15])
    style_axes(ax1)
    assert to_hex(ax1.spines["bottom"].get_edgecolor()) == DEFAULT_THEME.ink
    assert ax1.spines["bottom"].get_linewidth() == pytest.approx(DEFAULT_THEME.zero_spine_width)

    # Data including negatives -> neutral spine
    _fig2, ax2 = editorial_subplots()
    ax2.plot([1, 2, 3], [-5, 2, 8])
    style_axes(ax2)
    assert to_hex(ax2.spines["bottom"].get_edgecolor()) == DEFAULT_THEME.axis
    assert ax2.spines["bottom"].get_linewidth() == pytest.approx(DEFAULT_THEME.spine_width)

    # set_ylim(0, None) after style_axes -> dark spine at save
    fig3, ax3 = editorial_subplots()
    ax3.plot([1, 2, 3], [10, 20, 30])
    style_axes(ax3)
    assert to_hex(ax3.spines["bottom"].get_edgecolor()) == DEFAULT_THEME.axis
    ax3.set_ylim(0, None)
    save_figure(fig3, tmp_path / "post_ylim.png")
    assert to_hex(ax3.spines["bottom"].get_edgecolor()) == DEFAULT_THEME.ink
    assert ax3.spines["bottom"].get_linewidth() == pytest.approx(DEFAULT_THEME.zero_spine_width)

    # zero_baseline=False -> always neutral
    _fig4, ax4 = editorial_subplots()
    ax4.bar([1, 2, 3], [5, 10, 15])
    style_axes(ax4, zero_baseline=False)
    assert to_hex(ax4.spines["bottom"].get_edgecolor()) == DEFAULT_THEME.axis

    # zero_baseline=True anchors autoscaled 0-based series and includes later negative observation
    fig5, ax5 = editorial_subplots()
    ax5.vlines([1, 2], 0, [5, 10])
    style_axes(ax5, zero_baseline=True)
    assert ax5.get_ylim()[0] == 0.0
    assert to_hex(ax5.spines["bottom"].get_edgecolor()) == DEFAULT_THEME.ink
    ax5.plot([1, 2], [-3, 4])
    ax5.relim()
    ax5.autoscale_view()
    save_figure(fig5, tmp_path / "neg_obs.png")
    assert ax5.get_ylim()[0] < -3.0
    assert to_hex(ax5.spines["bottom"].get_edgecolor()) == DEFAULT_THEME.axis

    # Explicit set_ylim(-1, 5) is never overridden by zero_baseline=True
    fig6, ax6 = editorial_subplots()
    ax6.vlines([1, 2], 0, [3, 4])
    ax6.set_ylim(-1, 5)
    style_axes(ax6, zero_baseline=True)
    save_figure(fig6, tmp_path / "explicit_ylim.png")
    assert ax6.get_ylim() == (-1.0, 5.0)
    assert to_hex(ax6.spines["bottom"].get_edgecolor()) == DEFAULT_THEME.axis
