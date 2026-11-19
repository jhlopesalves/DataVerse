"""Point-based text wrapping and height measurement via the Agg renderer."""

from __future__ import annotations

from matplotlib.backends.backend_agg import RendererAgg
from matplotlib.figure import Figure
from matplotlib.font_manager import FontProperties
from matplotlib.text import Text

from .fonts import _resolved_weight


def text_width_pt(renderer: RendererAgg, text: str, prop: FontProperties) -> float:
    """Measure a single line of literal text in typographical points."""
    width, _, _ = renderer.get_text_width_height_descent(text, prop, ismath=False)  # type: ignore[no-untyped-call]  # RendererAgg is untyped in Matplotlib
    return float(width) / float(renderer.points_to_pixels(1))  # type: ignore[no-untyped-call]  # RendererAgg is untyped in Matplotlib


def measurement_renderer(fig: Figure) -> RendererAgg:
    """Return a 1x1 Agg renderer at ``fig.dpi`` for glyph measurements."""
    return RendererAgg(1, 1, fig.dpi)  # type: ignore[no-untyped-call]  # RendererAgg is untyped in Matplotlib


def wrap_text(
    fig: Figure,
    text: str,
    max_width_pt: float,
    *,
    fontfamily: str,
    fontsize: float,
    fontweight: str | int = "normal",
) -> str:
    """Wrap literal text to ``max_width_pt`` by glyph width, preserving newlines."""
    if not text:
        return text
    if max_width_pt <= 0:
        raise ValueError("Text has no usable width; reduce the margins or enlarge the figure.")
    renderer = measurement_renderer(fig)
    prop = FontProperties(
        family=fontfamily, size=fontsize, weight=_resolved_weight(fontfamily, fontweight)
    )
    paragraphs: list[str] = []
    for paragraph in text.split("\n"):
        lines: list[str] = []
        current = ""
        for word in paragraph.split():
            candidate = f"{current} {word}" if current else word
            if text_width_pt(renderer, candidate, prop) <= max_width_pt:
                current = candidate
                continue
            if current:
                lines.append(current)
            while text_width_pt(renderer, word, prop) > max_width_pt:
                low, high = 0, len(word)
                while low < high:
                    middle = (low + high + 1) // 2
                    if text_width_pt(renderer, word[:middle], prop) <= max_width_pt:
                        low = middle
                    else:
                        high = middle - 1
                if low == 0:
                    raise ValueError("A glyph exceeds the text width; enlarge the figure.")
                lines.append(word[:low])
                word = word[low:]
            current = word
        lines.append(current)
        paragraphs.append("\n".join(lines))
    return "\n".join(paragraphs)


def artist_height_pt(fig: Figure, artist: Text) -> float:
    """Measure the bounding-box height of ``artist`` in typographical points."""
    renderer = measurement_renderer(fig)
    return float(artist.get_window_extent(renderer).height) / float(renderer.points_to_pixels(1))  # type: ignore[no-untyped-call]  # RendererAgg is untyped in Matplotlib
