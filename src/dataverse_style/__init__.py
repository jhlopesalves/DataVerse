"""Editorial Matplotlib house style for DataVerse.

Apply the house theme once per session with :func:`use`, build figures with
:func:`editorial_subplots` or :func:`editorial_figure`, style axes with
:func:`style_axes`, and export with :func:`save_figure`.
"""

from ._state import get_theme as get_theme
from .axes import plot_band as plot_band
from .axes import plot_line as plot_line
from .axes import style_axes as style_axes
from .export import save_figure as save_figure
from .fonts import ensure_fonts as ensure_fonts
from .fonts import register_fonts as register_fonts
from .fonts import resolve_font_family as resolve_font_family
from .formatting import brl_formatter as brl_formatter
from .formatting import format_brl as format_brl
from .formatting import format_number as format_number
from .formatting import number_formatter as number_formatter
from .layout import editorial_figure as editorial_figure
from .layout import editorial_subplots as editorial_subplots
from .layout import finish as finish
from .layout import footer as footer
from .layout import header as header
from .theme import DEFAULT_THEME as DEFAULT_THEME
from .theme import LANDSCAPE_THEME as LANDSCAPE_THEME
from .theme import REPORT_THEME as REPORT_THEME
from .theme import THEMES as THEMES
from .theme import Theme as Theme
from .theme import theme_context as theme_context
from .theme import use as use

__version__ = "0.3.0"

__all__ = [
    "DEFAULT_THEME",
    "LANDSCAPE_THEME",
    "REPORT_THEME",
    "THEMES",
    "Theme",
    "brl_formatter",
    "editorial_figure",
    "editorial_subplots",
    "ensure_fonts",
    "finish",
    "footer",
    "format_brl",
    "format_number",
    "get_theme",
    "header",
    "number_formatter",
    "plot_band",
    "plot_line",
    "register_fonts",
    "resolve_font_family",
    "save_figure",
    "style_axes",
    "theme_context",
    "use",
]
