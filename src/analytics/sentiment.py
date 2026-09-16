"""Per-message sentiment using the existing local VADER scorer."""

from collections import Counter

from src.agent.sentiment import score_sentiment


def compute_discussion_sentiment(data):
    results = []
    counts = Counter()

    for index, message in enumerate(data["messages"]):
        text = message["content"]
        available = bool(text.strip())
        score, label = score_sentiment(text) if available else (None, None)

        if label is not None:
            counts[label] += 1

        results.append({
            # Stable reference within this saved discussion's message list.
            "message_index": index,
            "agent_id": message["sender_id"],
            "round_num": message["round_num"],
            "score": score,
            "label": label,
            "status": "scored" if available else "missing_text",
        })

    scores = [row["score"] for row in results if row["score"] is not None]
    return {
        "method": "vader_compound",
        "range": [-1, 1],
        "messages": results,
        "summary": {
            "message_count": len(results),
            "scored_messages": len(scores),
            "mean_score": round(sum(scores) / len(scores), 4) if scores else None,
            "label_counts": {
                label: counts[label]
                for label in ("positive", "neutral", "negative")
            },
        },
        "limitations": [
            "Sentiment measures tone, not stance or factual correctness.",
            "Sarcasm, quotations, and football terminology can affect accuracy.",
            "The existing scorer excludes the trailing SOURCES USED section.",
        ],
    }