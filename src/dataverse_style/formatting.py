"""Portuguese and English number and BRL formatting."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from numbers import Integral
from typing import Literal

from matplotlib.ticker import Formatter, FuncFormatter

_SCALES: tuple[tuple[float, str, str], ...] = (
    (1_000_000_000.0, " bi", "bn"),
    (1_000_000.0, " mi", "m"),
    (1_000.0, " mil", "k"),
)


def _normalize_lang(lang: str) -> Literal["pt", "en"]:
    cleaned = lang.strip().lower().replace("_", "-")
    if cleaned in {"pt", "pt-br"}:
        return "pt"
    if cleaned in {"en", "en-us", "en-gb"}:
        return "en"
    raise ValueError(f"Unsupported language {lang!r}. Expected 'pt' or 'en'.")


def _localized_text(value: str | Mapping[str, str], lang: str) -> str:
    norm = _normalize_lang(lang)
    if isinstance(value, str):
        return value
    if norm in value:
        return value[norm]
    for key, text in value.items():
        try:
            candidate = _normalize_lang(key)
        except ValueError:
            continue
        if candidate == norm:
            return text
    raise KeyError(f"Language {norm!r} not found in text mapping {list(value)!r}.")


def _validate_decimals(decimals: int) -> int:
    if isinstance(decimals, bool) or not isinstance(decimals, Integral):
        raise TypeError("decimals must be a non-negative integer.")
    if decimals < 0:
        raise ValueError("decimals must be a non-negative integer.")
    return int(decimals)


def format_number(value: float, lang: str = "en", decimals: int = 0) -> str:
    """Format a scalar with PT/EN separators and round-to-even rounding."""
    precision = _validate_decimals(decimals)
    norm = _normalize_lang(lang)
    if isinstance(value, Integral):
        text = f"{int(value):,}" + ("." + "0" * precision if precision else "")
    else:
        number = float(value)
        if not math.isfinite(number):
            return str(number)
        rounded = round(number, precision)
        if rounded == 0:
            rounded = 0.0
        text = f"{rounded:,.{precision}f}"
    return text.replace(",", "_").replace(".", ",").replace("_", ".") if norm == "pt" else text


def format_brl(value: float, lang: str = "en", decimals: int = 0) -> str:
    """Format Brazilian reais with ``-`` before ``R$`` and a space in Portuguese."""
    norm = _normalize_lang(lang)
    return _with_brl_prefix(format_number(value, norm, decimals), norm)


def _with_brl_prefix(text: str, lang: Literal["pt", "en"]) -> str:
    negative = text.startswith("-")
    if negative:
        text = text[1:]
    return f"{'-' if negative else ''}R${' ' if lang == 'pt' else ''}{text}"


def _choose_scale(max_abs: float, lang: Literal["pt", "en"]) -> tuple[float, str]:
    for threshold, pt_suffix, en_suffix in _SCALES:
        if max_abs >= threshold:
            return threshold, (pt_suffix if lang == "pt" else en_suffix)
    return 1.0, ""


class _CompactFormatter(Formatter):
    """Axis-wide compact number or BRL tick formatter."""

    def __init__(self, lang: Literal["pt", "en"], *, currency: bool) -> None:
        super().__init__()
        self._lang: Literal["pt", "en"] = lang
        self._currency: bool = currency
        self._last_scale: tuple[float | None, str, int] | None = None

    def _format_one(self, value: float, divisor: float | None, suffix: str, decimals: int) -> str:
        if not math.isfinite(value):
            text = str(value)
        elif divisor is None:
            text = f"{value:.{decimals}e}" if value else "0"
            if self._lang == "pt":
                text = text.replace(".", ",")
        else:
            scaled = value / divisor
            text = (
                f"{format_number(scaled, self._lang, decimals)}{suffix}"
                if round(scaled, decimals) != 0
                else "0"
            )
        return _with_brl_prefix(text, self._lang) if self._currency else text

    def _choose_format(self, values: Sequence[float]) -> tuple[float | None, str, int]:
        distinct = {value for value in values if math.isfinite(value)}
        divisor, suffix = _choose_scale(max(map(abs, distinct), default=0.0), self._lang)
        if len(distinct) <= 1:
            scaled = next(iter(distinct), 0.0) / divisor
            rounded = round(scaled, 2)
            if scaled == 0 or rounded != 0:
                decimals = next(p for p in range(3) if round(scaled, p) == rounded)
                return divisor, suffix, decimals

        # Include zero in the check so a non-zero tick cannot look like zero.
        distinct.add(0.0)
        candidates: list[tuple[float | None, str, range]] = []
        if suffix:
            candidates.append((divisor, suffix, range(5)))
        candidates.extend([(1.0, "", range(7)), (None, "", range(16))])
        for scale, unit, precisions in candidates:
            for precision in precisions:
                labels = {self._format_one(v, scale, unit, precision) for v in distinct}
                if len(labels) == len(distinct):
                    return scale, unit, precision
        # Seventeen significant digits distinguish all distinct finite floats.
        return None, "", 16

    def format_ticks(self, values: Sequence[float]) -> list[str]:
        ticks = [float(value) for value in values]
        self._last_scale = self._choose_format(ticks)
        return [self._format_one(value, *self._last_scale) for value in ticks]

    def __call__(self, x: float, pos: int | None = None) -> str:
        value = float(x)
        return self._format_one(value, *(self._last_scale or self._choose_format((value,))))


def number_formatter(lang: str = "en", decimals: int = 0, compact: bool = False) -> Formatter:
    """Return a numeric tick formatter with optional axis-wide compact notation.

    Compact mode chooses a common scale and precision, falling back to ordinary
    decimal or scientific notation when the compact labels would repeat.
    """
    norm = _normalize_lang(lang)
    precision = _validate_decimals(decimals)
    if compact:
        return _CompactFormatter(norm, currency=False)
    return FuncFormatter(lambda value, _pos: format_number(value, norm, precision))


def brl_formatter(lang: str = "en", decimals: int = 0, compact: bool = False) -> Formatter:
    """Return a BRL tick formatter with the same compact policy as :func:`number_formatter`."""
    norm = _normalize_lang(lang)
    precision = _validate_decimals(decimals)
    if compact:
        return _CompactFormatter(norm, currency=True)
    return FuncFormatter(lambda value, _pos: format_brl(value, norm, precision))
