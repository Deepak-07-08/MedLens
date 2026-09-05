"""
Tests for the safety core.

These run without a database, without a network, and without the AI.
If any of these fail, MedLens is not safe to demo.
"""

from decimal import Decimal

import pytest

from app.services import evidence_guard as guard
from app.services import range_evaluator as ev
from app.services import value_parser as vp

D = Decimal


# ─────────────────────────── value parsing ───────────────────────────

@pytest.mark.parametrize(
    "raw, numeric, comparator, is_numeric",
    [
        ("10.2", D("10.2"), None, True),
        ("  13.5  ", D("13.5"), None, True),
        ("<0.01", D("0.01"), "<", True),
        ("< 0.01", D("0.01"), "<", True),
        ("<=5", D("5"), "<", True),
        (">200", D("200"), ">", True),
        ("> 200", D("200"), ">", True),
        ("10.2 g/dL", D("10.2"), None, True),
        ("1,234", D("1234"), None, True),
        ("10,5", D("10.5"), None, True),
        ("-2.4", D("-2.4"), None, True),
        ("Negative", None, None, False),
        ("Positive", None, None, False),
        ("Trace", None, None, False),
        ("", None, None, False),
        (None, None, None, False),
    ],
)
def test_parse_value(raw, numeric, comparator, is_numeric):
    result = vp.parse_value(raw)
    assert result.numeric == numeric
    assert result.comparator == comparator
    assert result.is_numeric is is_numeric


@pytest.mark.parametrize(
    "raw, low, high, parsed",
    [
        ("12 - 16", D("12"), D("16"), True),
        ("12-16", D("12"), D("16"), True),
        ("12.0 – 16.0", D("12.0"), D("16.0"), True),   # en dash
        ("12 to 16", D("12"), D("16"), True),
        ("Reference Range: 13.0 - 17.0", D("13.0"), D("17.0"), True),
        ("16 - 12", D("12"), D("16"), True),           # printed backwards
        ("< 200", None, D("200"), True),
        ("Up to 5.0", None, D("5.0"), True),
        ("> 40", D("40"), None, True),
        ("at least 40", D("40"), None, True),
        ("Negative", None, None, False),
        ("See comment", None, None, False),
        ("", None, None, False),
        (None, None, None, False),
    ],
)
def test_parse_reference_range(raw, low, high, parsed):
    result = vp.parse_reference_range(raw)
    assert result.low == low
    assert result.high == high
    assert result.parsed is parsed


def test_normalize_test_name():
    assert vp.normalize_test_name("Hemoglobin (Hb)") == "hemoglobin hb"
    assert vp.normalize_test_name("  WBC  Count ") == "wbc count"
    assert vp.normalize_test_name(None) == ""


# ─────────────────────── the core safety guarantee ───────────────────────

def test_no_range_means_unknown_never_a_guess():
    """The whole project rests on this test."""
    result = ev.evaluate(value_numeric=D("10.2"), ref_source=ev.REF_SOURCE_NONE)
    assert result.status == ev.UNKNOWN
    assert result.reason == ev.NO_RANGE_MESSAGE


def test_range_from_anywhere_other_than_the_report_is_refused():
    """Even with bounds supplied, a non-report source is not trusted."""
    result = ev.evaluate(
        value_numeric=D("10.2"),
        ref_low=D("12"), ref_high=D("16"),
        ref_source="model_knowledge",
    )
    assert result.status == ev.UNKNOWN


def test_report_source_with_no_bounds_is_still_unknown():
    result = ev.evaluate(
        value_numeric=D("10.2"),
        ref_low=None, ref_high=None,
        ref_source=ev.REF_SOURCE_REPORT,
    )
    assert result.status == ev.UNKNOWN


def test_no_standard_reference_table_exists_in_the_module():
    """Guards against anyone adding a fallback range dictionary later."""
    import inspect
    source = inspect.getsource(ev)
    for banned in ("hemoglobin", "glucose", "cholesterol", "12.0, 16.0"):
        assert banned not in source.lower()


# ─────────────────────────── status decisions ───────────────────────────

@pytest.mark.parametrize(
    "value, low, high, expected",
    [
        (D("10.2"), D("12"), D("16"), ev.LOW),
        (D("14.0"), D("12"), D("16"), ev.NORMAL),
        (D("18.0"), D("12"), D("16"), ev.HIGH),
        (D("12"), D("12"), D("16"), ev.NORMAL),      # on the low boundary
        (D("16"), D("12"), D("16"), ev.NORMAL),      # on the high boundary
        (D("250"), None, D("200"), ev.HIGH),         # upper bound only
        (D("150"), None, D("200"), ev.NORMAL),
        (D("30"), D("40"), None, ev.LOW),            # lower bound only
        (D("50"), D("40"), None, ev.NORMAL),
    ],
)
def test_status_from_report_range(value, low, high, expected):
    result = ev.evaluate(
        value_numeric=value, ref_low=low, ref_high=high,
        ref_source=ev.REF_SOURCE_REPORT,
    )
    assert result.status == expected


def test_non_numeric_value_is_reported_not_classified():
    result = ev.evaluate(
        value_numeric=None, ref_low=D("12"), ref_high=D("16"),
        ref_source=ev.REF_SOURCE_REPORT,
    )
    assert result.status == ev.NON_NUMERIC


def test_less_than_is_only_low_when_conclusive():
    conclusive = ev.evaluate(
        value_numeric=D("0.01"), comparator="<",
        ref_low=D("0.5"), ref_high=D("5.0"),
        ref_source=ev.REF_SOURCE_REPORT,
    )
    assert conclusive.status == ev.LOW

    ambiguous = ev.evaluate(
        value_numeric=D("10"), comparator="<",
        ref_low=D("2"), ref_high=D("20"),
        ref_source=ev.REF_SOURCE_REPORT,
    )
    assert ambiguous.status == ev.UNKNOWN


def test_greater_than_is_only_high_when_conclusive():
    conclusive = ev.evaluate(
        value_numeric=D("200"), comparator=">",
        ref_low=D("10"), ref_high=D("100"),
        ref_source=ev.REF_SOURCE_REPORT,
    )
    assert conclusive.status == ev.HIGH

    ambiguous = ev.evaluate(
        value_numeric=D("50"), comparator=">",
        ref_low=D("10"), ref_high=D("100"),
        ref_source=ev.REF_SOURCE_REPORT,
    )
    assert ambiguous.status == ev.UNKNOWN


def test_units_match():
    assert ev.units_match("g/dL", "12 - 16 g/dL") is True
    assert ev.units_match("g/dL", "12 - 16") is True        # no unit stated
    assert ev.units_match(None, "12 - 16 g/dL") is True
    assert ev.units_match("mg/dL", "3.9 - 5.5 mmol/L") is False


# ─────────────────────────── evidence guard ───────────────────────────

REPORT_TEXT = """
    CITY DIAGNOSTICS - COMPLETE BLOOD COUNT
    Collected: 14 Aug 2026

    HEMOGLOBIN        10.2 g/dL     Reference Range 12 - 16 g/dL
    WBC COUNT          7.4 10^3/uL   Reference Range 4.0 - 11.0
    PLATELETS          210 10^3/uL
"""


def test_evidence_verified_when_everything_traces():
    result = guard.check(
        raw_text=REPORT_TEXT,
        value_text="10.2",
        reference_range_text="12 - 16",
        source_snippet="HEMOGLOBIN 10.2 g/dL Reference Range 12 - 16 g/dL",
    )
    assert result.verified is True
    assert result.trust_range is True


def test_hallucinated_range_is_caught_and_discarded():
    """Platelets has no printed range. An invented one must not survive."""
    result = guard.check(
        raw_text=REPORT_TEXT,
        value_text="210",
        reference_range_text="150 - 450",   # not in the document
        source_snippet="PLATELETS 210 10^3/uL",
    )
    assert result.range_found is False
    assert result.trust_range is False
    assert result.verified is False

    # And the evaluator therefore refuses to produce a status.
    ref_source = (ev.REF_SOURCE_REPORT if result.trust_range
                  else ev.REF_SOURCE_NONE)
    decision = ev.evaluate(value_numeric=D("210"), ref_source=ref_source)
    assert decision.status == ev.UNKNOWN


def test_hallucinated_value_is_caught():
    result = guard.check(
        raw_text=REPORT_TEXT,
        value_text="99.9",
        reference_range_text=None,
        source_snippet="HEMOGLOBIN 99.9 g/dL",
    )
    assert result.value_found is False
    assert result.verified is False


def test_dash_and_spacing_differences_do_not_cause_false_failures():
    result = guard.check(
        raw_text=REPORT_TEXT,
        value_text="10.2",
        reference_range_text="12–16",   # en dash, no spaces
        source_snippet="HEMOGLOBIN   10.2   g/dL",
    )
    assert result.range_found is True


def test_no_text_layer_is_honest_about_it():
    result = guard.check(
        raw_text="",
        value_text="10.2",
        reference_range_text="12 - 16",
        source_snippet="HEMOGLOBIN 10.2",
    )
    assert result.verified is False
    assert result.trust_range is False
    assert "scanned" in result.reason.lower()


def test_confidence_is_reduced_when_evidence_is_weak():
    strong = guard.check(
        raw_text=REPORT_TEXT, value_text="10.2",
        reference_range_text="12 - 16",
        source_snippet="HEMOGLOBIN 10.2 g/dL Reference Range 12 - 16 g/dL",
    )
    weak = guard.check(
        raw_text=REPORT_TEXT, value_text="99.9",
        reference_range_text=None, source_snippet="TOTALLY UNRELATED LINE",
    )
    assert guard.final_confidence(0.95, strong) == 0.95
    assert guard.final_confidence(0.95, weak) < 0.4


def test_confidence_never_exceeds_what_the_model_claimed():
    strong = guard.check(
        raw_text=REPORT_TEXT, value_text="10.2",
        reference_range_text="12 - 16",
        source_snippet="HEMOGLOBIN 10.2 g/dL Reference Range 12 - 16 g/dL",
    )
    assert guard.final_confidence(0.60, strong) <= 0.60
