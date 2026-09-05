"""
Evidence guard: proves that what the AI reported is actually in the document.

The model is asked to copy, not to remember. This module checks that it did.

For each extracted result we ask three questions against the text we pulled
out of the file ourselves with pdfplumber:

    1. Does the quoted source snippet exist in the document?
    2. Does the value exist in the document?
    3. Does the reference range exist in the document?   <-- the critical one

A hallucinated reference range would have to be a string that happens to
already be printed in the report. That is very unlikely, which is what makes
this a structural defence rather than a hopeful instruction in a prompt.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Confidence multipliers applied to the model's self-reported confidence.
FACTOR_VERIFIED = 1.0
FACTOR_PARTIAL = 0.6
FACTOR_UNVERIFIABLE = 0.3

NO_TEXT_LAYER = "no_text_layer"


@dataclass(frozen=True)
class EvidenceResult:
    value_found: bool
    range_found: bool
    snippet_found: bool
    score: float  # 0.0 - 1.0, how much of the snippet is in the document
    verified: bool  # value AND range AND snippet all traced
    trust_range: bool  # may the range be used for a status decision?
    reason: str


def normalize(text: str | None) -> str:
    """
    Flatten text so that layout differences do not cause false failures.

    Collapses whitespace, lowercases, and unifies the several dash
    characters labs use, so '12 – 16' and '12-16' compare equal.
    """
    if not text:
        return ""
    lowered = text.lower()
    lowered = re.sub(r"[\u2010\u2011\u2012\u2013\u2014\u2212]", "-", lowered)
    lowered = re.sub(r"\s*-\s*", "-", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def _token_overlap(needle: str, haystack: str) -> float:
    """Fraction of the snippet's tokens that appear in the document."""
    tokens = [t for t in needle.split() if t]
    if not tokens:
        return 0.0
    hits = sum(1 for t in tokens if t in haystack)
    return hits / len(tokens)


def check(
    *,
    raw_text: str | None,
    value_text: str | None,
    reference_range_text: str | None,
    source_snippet: str | None,
) -> EvidenceResult:
    """
    Run the guard for one extracted test result.

    When raw_text is empty - a scanned PDF or a photo, where we have no text
    layer to check against - nothing can be traced. We say so honestly and
    refuse to trust the range, rather than assuming the extraction is fine.
    """
    haystack = normalize(raw_text)

    if not haystack:
        return EvidenceResult(
            value_found=False,
            range_found=False,
            snippet_found=False,
            score=0.0,
            verified=False,
            trust_range=False,
            reason="Scanned or image report: no text layer available to "
                   "trace this value. Manual verification required.",
        )

    value_found = bool(value_text) and normalize(value_text) in haystack

    if reference_range_text:
        range_found = normalize(reference_range_text) in haystack
    else:
        range_found = True  # nothing claimed, nothing to disprove

    snippet_norm = normalize(source_snippet)
    snippet_found = bool(snippet_norm) and snippet_norm in haystack
    score = _token_overlap(snippet_norm, haystack) if snippet_norm else 0.0

    # The range may only be used if it was literally found in the document.
    trust_range = (not reference_range_text) or range_found

    verified = value_found and range_found and snippet_found

    if verified:
        reason = "Value and reference range traced to the source document."
    elif not value_found:
        reason = "The reported value could not be found in the document text."
    elif reference_range_text and not range_found:
        reason = ("The reference range could not be found in the document "
                  "text and has been discarded.")
    else:
        reason = "The quoted source line could not be matched exactly."

    return EvidenceResult(
        value_found=value_found,
        range_found=range_found,
        snippet_found=snippet_found,
        score=round(score, 3),
        verified=verified,
        trust_range=trust_range,
        reason=reason,
    )


def confidence_factor(result: EvidenceResult) -> float:
    """How much of the model's stated confidence survives the guard."""
    if result.verified:
        return FACTOR_VERIFIED
    if result.value_found or result.score >= 0.7:
        return FACTOR_PARTIAL
    return FACTOR_UNVERIFIABLE


def final_confidence(ai_confidence: float | None, result: EvidenceResult) -> float:
    """Confidence shown in the UI. Never higher than the model claimed."""
    base = 0.5 if ai_confidence is None else max(0.0, min(1.0, ai_confidence))
    return round(base * confidence_factor(result), 3)
