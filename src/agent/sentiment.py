"""Per-message sentiment scoring for agent and discussion messages.

Uses VADER (lexicon-based) rather than an extra LLM call, so every
message gets a sentiment score with no added API cost, latency, or
pressure on the shared output-token budget used by the discussion
tests (see ``src/discussion/check_six_agents_without_week1.py``).
"""

import re

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

_analyzer = SentimentIntensityAnalyzer()

POSITIVE_THRESHOLD = 0.05
NEGATIVE_THRESHOLD = -0.05


def score_sentiment(text: str) -> tuple[float, str]:
    """Return ``(compound_score, label)`` for a single message.

    ``compound_score`` is in ``[-1.0, 1.0]``.
    ``label`` is one of ``"positive"``, ``"negative"``, ``"neutral"``.
    Empty or non-string input is treated as neutral.
    """
    if not isinstance(text, str) or not text.strip():
        return 0.0, "neutral"

    response_text = re.split(r"(?im)^\s*(?:\*\*)?SOURCES USED\s*:", text, maxsplit=1)[0]
    compound = _analyzer.polarity_scores(response_text)["compound"]

    if compound >= POSITIVE_THRESHOLD:
        label = "positive"
    elif compound <= NEGATIVE_THRESHOLD:
        label = "negative"
    else:
        label = "neutral"

    return compound, label
