"""
Parses raw text from lab reports into numbers.

This module is PURE PYTHON. No AI, no database, no network.
It never guesses medical meaning - it only converts text to numbers
where that conversion is unambiguous.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

# Dashes labs actually use: hyphen, en dash, em dash, minus sign
DASHES = r"\-\u2010\u2011\u2012\u2013\u2014\u2212"

_NUMBER = r"[+-]?\d+(?:[.,]\d+)?(?:[eE][+-]?\d+)?"


@dataclass(frozen=True)
class ParsedValue:
    """Result of parsing a single test value."""

    numeric: Decimal | None  # None when the value is not a number
    comparator: str | None  # '<' or '>' when the report used one
    is_numeric: bool
    raw: str


@dataclass(frozen=True)
class ParsedRange:
    """Result of parsing a reference range string."""

    low: Decimal | None
    high: Decimal | None
    parsed: bool  # False = we could not understand it; treat as no range


def _to_decimal(text: str) -> Decimal | None:
    """'1,234.5' -> Decimal('1234.5'). Returns None if not a number."""
    cleaned = text.strip()
    # Thousands separator: 1,234 or 1,234.56
    if re.fullmatch(r"[+-]?\d{1,3}(?:,\d{3})+(?:\.\d+)?", cleaned):
        cleaned = cleaned.replace(",", "")
    else:
        # Decimal comma: 10,5 -> 10.5
        cleaned = re.sub(r"(?<=\d),(?=\d)", ".", cleaned)
    try:
        return Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return None


def parse_value(raw: str | None) -> ParsedValue:
    """
    Turn a reported value into a number when possible.

        '10.2'      -> 10.2
        '<0.01'     -> 0.01 with comparator '<'
        '> 200'     -> 200 with comparator '>'
        '10.2 g/dL' -> 10.2 (trailing unit ignored)
        'Negative'  -> not numeric
        ''          -> not numeric

    A non-numeric result is NOT an error. It is stored as-is and the
    evaluator reports status 'non_numeric' rather than inventing meaning.
    """
    if raw is None:
        return ParsedValue(None, None, False, "")

    text = raw.strip()
    if not text:
        return ParsedValue(None, None, False, raw)

    comparator: str | None = None
    body = text

    # Leading comparator, with or without a space, including <= and >=
    m = re.match(r"^\s*(<=|>=|<|>|\u2264|\u2265)\s*(.+)$", body)
    if m:
        symbol = m.group(1)
        comparator = "<" if symbol in ("<", "<=", "\u2264") else ">"
        body = m.group(2)

    # First number in what is left; a trailing unit is ignored
    num_match = re.match(rf"^\s*({_NUMBER})", body)
    if not num_match:
        return ParsedValue(None, comparator, False, raw)

    numeric = _to_decimal(num_match.group(1))
    if numeric is None:
        return ParsedValue(None, comparator, False, raw)

    return ParsedValue(numeric, comparator, True, raw)


def parse_reference_range(raw: str | None) -> ParsedRange:
    """
    Turn a reference range printed on the report into low/high bounds.

        '12 - 16'      -> low 12,   high 16
        '12.0-16.0'    -> low 12,   high 16
        '12 to 16'     -> low 12,   high 16
        '< 200'        -> low None, high 200
        '> 40'         -> low 40,   high None
        'Up to 5.0'    -> low None, high 5
        'Negative'     -> not parsed
        None           -> not parsed

    parsed=False means we could not understand the text. The caller MUST
    then treat the result as having no reference range. We never fall back
    to a default range.
    """
    if raw is None:
        return ParsedRange(None, None, False)

    text = raw.strip()
    if not text:
        return ParsedRange(None, None, False)

    # Strip a leading label such as 'Reference Range:' or 'Ref:'
    text = re.sub(r"^\s*(reference\s*range|ref\.?\s*range|ref|normal)\s*[:\-]?\s*",
                  "", text, flags=re.IGNORECASE)

    # Two-sided: '12 - 16', '12 to 16', '12–16'
    two_sided = re.search(
        rf"({_NUMBER})\s*(?:[{DASHES}]|to)\s*({_NUMBER})", text, flags=re.IGNORECASE
    )
    if two_sided:
        low = _to_decimal(two_sided.group(1))
        high = _to_decimal(two_sided.group(2))
        if low is not None and high is not None:
            if low > high:  # printed backwards; swap rather than reject
                low, high = high, low
            return ParsedRange(low, high, True)

    # Upper bound only: '< 200', 'up to 5.0', 'less than 10'
    upper = re.search(
        rf"(?:<=?|\u2264|up\s+to|less\s+than|below)\s*({_NUMBER})",
        text, flags=re.IGNORECASE,
    )
    if upper:
        high = _to_decimal(upper.group(1))
        if high is not None:
            return ParsedRange(None, high, True)

    # Lower bound only: '> 40', 'greater than 40', 'at least 40'
    lower = re.search(
        rf"(?:>=?|\u2265|greater\s+than|more\s+than|at\s+least|above)\s*({_NUMBER})",
        text, flags=re.IGNORECASE,
    )
    if lower:
        low = _to_decimal(lower.group(1))
        if low is not None:
            return ParsedRange(low, None, True)

    return ParsedRange(None, None, False)


def normalize_test_name(name: str | None) -> str:
    """
    Canonical form used ONLY to match the same test across reports.
    Never shown to the user - the verbatim name is always displayed.

        'Hemoglobin (Hb)' -> 'hemoglobin hb'
    """
    if not name:
        return ""
    lowered = name.lower()
    lowered = re.sub(r"[^a-z0-9\s]", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()
