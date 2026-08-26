"""Evaluate the football vector retriever against a small labeled benchmark."""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EVALUATION_SET = [
    {
        "id": "rules-offside",
        "query": "When is a player in an offside position, and when is it an offence?",
        "relevant_doc_ids": ["doc_011", "doc_012"],
        "relevance_note": "The IFAB offside law and its deliberate-play clarification are relevant.",
    },
    {
        "id": "analytics-xg",
        "query": "What is expected goals (xG), and how should a value of 0.2 be interpreted?",
        "relevant_doc_ids": ["doc_019", "doc_024", "doc_027"],
        "relevance_note": "The xG explainer is primary; the analytics glossary and metrics guide are supporting sources.",
    },
    {
        "id": "analytics-pressing",
        "query": "What does PPDA measure and how is it used to assess pressing intensity?",
        "relevant_doc_ids": ["doc_028", "doc_027", "doc_024"],
        "relevance_note": "The PPDA explainer is primary; the metrics guide and analytics glossary are supporting sources.",
    },
    {
        "id": "analytics-progression",
        "query": "What is expected threat (xT) and how does it value ball progression?",
        "relevant_doc_ids": ["doc_030", "doc_024", "doc_027"],
        "relevance_note": "The xT chapter is primary; the glossary and metrics guide provide related context.",
    },
    {
        "id": "tactics-formation",
        "query": "How is a 4-3-3 football formation structured, and what are its player lines?",
        "relevant_doc_ids": ["doc_043", "doc_046", "doc_047"],
        "relevance_note": "The 4-3-3 guide is primary; general tactics and formations guides are supporting sources.",
    },
    {
        "id": "tactics-counterattack",
        "query": "What happens during a counter-attack immediately after winning the ball?",
        "relevant_doc_ids": ["doc_060", "doc_061", "doc_053"],
        "relevance_note": "The counter-attacking guide is primary; defensive transitions and counter-pressing are supporting sources.",
    },
    {
        "id": "match-japan-spain",
        "query": "What happened in Japan's 2-1 World Cup win over Spain?",
        "relevant_doc_ids": ["doc_077"],
        "relevance_note": "The match report for Japan 2-1 Spain is the relevant source.",
    },
]


def reciprocal_rank(retrieved_doc_ids: list[str], relevant_doc_ids: set[str]) -> float:
    for rank, doc_id in enumerate(retrieved_doc_ids, start=1):
        if doc_id in relevant_doc_ids:
            return 1.0 / rank
    return 0.0


def score_results(
    retrieved_doc_ids: list[str], relevant_doc_ids: list[str], k: int
) -> dict[str, float | int]:
    """Score source-level retrieval, counting a relevant document once."""
    relevant = set(relevant_doc_ids)
    top_k = retrieved_doc_ids[:k]
    hits = len(set(top_k) & relevant)
    return {
        "retrieved": len(top_k),
        "relevant_hits": hits,
        "precision_at_k": hits / len(top_k) if top_k else 0.0,
        "recall_at_k": hits / len(relevant) if relevant else 0.0,
        "reciprocal_rank": reciprocal_rank(top_k, relevant),
    }


def evaluate(k: int = 5) -> dict[str, Any]:
    if str(Path(__file__).resolve().parent) not in sys.path:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
    from search import search

    results = []
    for case in EVALUATION_SET:
        retrieved = search(case["query"], k=k)
        retrieved_doc_ids = [item["doc_id"] for item in retrieved]
        results.append(
            {
                **case,
                "retrieved": [
                    {
                        "rank": rank,
                        "doc_id": item["doc_id"],
                        "chunk_index": item["chunk_index"],
                        "title": item["title"],
                        "similarity": round(float(item["similarity"]), 6),
                    }
                    for rank, item in enumerate(retrieved, start=1)
                ],
                "metrics": score_results(
                    retrieved_doc_ids, case["relevant_doc_ids"], k
                ),
            }
        )

    metric_names = ("precision_at_k", "recall_at_k", "reciprocal_rank")
    averages = {
        name: sum(item["metrics"][name] for item in results) / len(results)
        for name in metric_names
    }
    return {
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "k": k,
        "metric_definition": {
            "precision_at_k": "unique relevant source documents in the top-k divided by retrieved top-k documents",
            "recall_at_k": "unique relevant source documents in the top-k divided by labeled relevant source documents",
            "reciprocal_rank": "1 divided by the rank of the first relevant source, or 0 if none is retrieved",
        },
        "results": results,
        "macro_average": averages,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-k", type=int, default=5, help="number of chunks to retrieve")
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "docs" / "evaluation_results.json",
    )
    args = parser.parse_args()

    report = evaluate(k=args.k)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["macro_average"], indent=2))
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()