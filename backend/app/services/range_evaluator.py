"""
The ONLY place in MedLens where a Low / Normal / High status is produced.

Rules that must never be broken:

  1. A status is calculated only from a reference range that came from the
     uploaded report itself (ref_source == 'report').
  2. If there is no such range, the status is UNKNOWN. We do not fall back
     to textbook values, training data, or any built-in table.
  3. No AI model is involved. This is deterministic arithmetic.

There is deliberately no dictionary of standard reference ranges anywhere
in this file or this project. It cannot leak in because it does not exist.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

# Status values
LOW = "low"
NORMAL = "normal"
HIGH = "high"
UNKNOWN = "unknown"
NON_NUMERIC = "non_numeric"

# Where a reference range is allowed to come from
REF_SOURCE_REPORT = "report"
REF_SOURCE_NONE = "none"

NO_RANGE_MESSAGE = "No reference range provided in source report."


@dataclass(frozen=True)
class Evaluation:
    status: str
    reason: str


def evaluate(
    *,
    value_numeric: Decimal | None,
    comparator: str | None = None,
    ref_low: Decimal | None = None,
    ref_high: Decimal | None = None,
    ref_source: str = REF_SOURCE_NONE,
) -> Evaluation:
    """
    Decide the status of one test result.

    Called only after the evidence guard has confirmed the reference range
    appears verbatim in the source document. If that check failed, the
    caller passes ref_source='none' and this returns UNKNOWN.
    """

    # Gate 1: no trustworthy range means no judgement, ever.
    if ref_source != REF_SOURCE_REPORT:
        return Evaluation(UNKNOWN, NO_RANGE_MESSAGE)

    if ref_low is None and ref_high is None:
        return Evaluation(UNKNOWN, NO_RANGE_MESSAGE)

    # Gate 2: values like 'Negative' or 'Trace' are reported, not classified.
    if value_numeric is None:
        return Evaluation(
            NON_NUMERIC,
            "Result is not a numeric value, so it cannot be compared to a range.",
        )

    # Gate 3: a comparator makes the true value uncertain in one direction.
    # '<0.01' is only conclusive if 0.01 is already at or below the low bound.
    if comparator == "<":
        if ref_low is not None and value_numeric <= ref_low:
            return Evaluation(
                LOW,
                f"Reported as below {value_numeric}, which is at or under the "
                f"range stated in the report (low: {ref_low}).",
            )
        return Evaluation(
            UNKNOWN,
            f"Value reported as '<{value_numeric}'. The exact value is not "
            f"stated, so it cannot be placed against the report's range.",
        )

    if comparator == ">":
        if ref_high is not None and value_numeric >= ref_high:
            return Evaluation(
                HIGH,
                f"Reported as above {value_numeric}, which is at or over the "
                f"range stated in the report (high: {ref_high}).",
            )
        return Evaluation(
            UNKNOWN,
            f"Value reported as '>{value_numeric}'. The exact value is not "
            f"stated, so it cannot be placed against the report's range.",
        )

    # Plain numeric comparison against the report's own bounds.
    if ref_low is not None and value_numeric < ref_low:
        return Evaluation(
            LOW, f"Below the range stated in the report (low: {ref_low})."
        )

    if ref_high is not None and value_numeric > ref_high:
        return Evaluation(
            HIGH, f"Above the range stated in the report (high: {ref_high})."
        )

    return Evaluation(NORMAL, "Within the range stated in the report.")


def units_match(value_unit: str | None, range_text: str | None) -> bool:
    """
    True unless the range text names a unit that clearly differs from the
    value's unit. A mismatch means the comparison would be meaningless, so
    the caller drops the range and records a conflict instead.
    """
    if not value_unit or not range_text:
        return True

    unit = value_unit.strip().lower().replace(" ", "")
    text = range_text.strip().lower().replace(" ", "")

    if unit in text:
        return True

    # Any other unit-looking token present while ours is absent = mismatch.
    import re

    tokens = re.findall(r"[a-z]+(?:/[a-z]+)?", text)
    ignore = {"to", "up", "less", "than", "greater", "more", "at", "least",
              "above", "below", "normal", "ref", "reference", "range"}
    other_units = [t for t in tokens if t not in ignore]
    return not other_units
