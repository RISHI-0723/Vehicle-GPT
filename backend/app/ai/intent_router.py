"""Deterministic intent classification for the Ask endpoint.

This is plain keyword/regex matching -- no LLM call is involved in
classification. It must stay fast, typed, and independently testable.
Rule order matters: more specific phrasing is checked before broader
phrasing (e.g. "what if ... normally" must win over the bare word "why").
"""
import re

from app.ai.schemas import Intent

_RULES: list[tuple[Intent, re.Pattern[str]]] = [
    (Intent.WHAT_IF, re.compile(r"\bwhat if\b|\bnormally\b")),
    (Intent.RANGE_DROP, re.compile(r"\bwhy\b|range\s+(dropped|drop|lower|low|changed|change)")),
    (Intent.COST, re.compile(r"\bcost\b|\bspend\b|\bspent\b|\bprice\b|\bmoney\b|\bpay\b|₹")),
    (Intent.BATTERY_STRESS, re.compile(r"\bstress")),
    (Intent.ANOMALY, re.compile(r"anomal|abnormal|unusual")),
    (Intent.RECOMMENDATIONS, re.compile(r"should i (change|do)|\brecommend|what should i")),
    (Intent.DRIVE_COMPARISON, re.compile(r"worse than|better than|\bcompare|comparison")),
    (Intent.ENERGY_EFFICIENCY, re.compile(r"efficien|\benergy\b|\bkwh\b|\bconsum")),
    (
        Intent.GENERAL_VEHICLE,
        re.compile(r"what vehicle|which vehicle|vehicle is this|about (this|my) vehicle|vehicle (info|details)"),
    ),
]


def classify_intent(question: str) -> Intent:
    """Classify a driver's question into a supported intent.

    Returns Intent.UNKNOWN when confidence is insufficient (no rule
    matched) rather than guessing.
    """
    text = question.strip().lower()
    if not text:
        return Intent.UNKNOWN
    for intent, pattern in _RULES:
        if pattern.search(text):
            return intent
    return Intent.UNKNOWN
