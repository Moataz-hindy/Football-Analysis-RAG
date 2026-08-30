# Retrieval Evaluation

## What is being evaluated

The current system is a **dense vector RAG retriever**: it embeds a question with the configured OpenRouter embedding model, then uses PostgreSQL `pgvector` cosine distance to return the nearest fixed-size text chunks. It is not GraphRAG. The repository has no entity extraction, graph store, relationship traversal, or multi-hop retrieval path, so switching to GraphRAG would add infrastructure without evidence of a graph-shaped retrieval failure. This benchmark evaluates the existing retriever first.

The benchmark contains seven representative football questions covering laws, football analytics, tactics, and a match report. Each case labels relevant source documents by their existing `doc_id`; a retrieved chunk is relevant when its source document is in that label set. Labels are intentionally source-level because the ingestion pipeline does not persist human-authored chunk relevance judgments.

## Metrics

At `k=5`, the evaluator records these metrics for every query:

- **Precision@5**: unique relevant source documents in the top five divided by five retrieved chunks.
- **Recall@5**: unique relevant source documents found in the top five divided by the labeled relevant source documents.
- **MRR**: reciprocal rank of the first relevant source. This measures whether useful evidence appears near the top.

Run the live evaluation from the project root after PostgreSQL is populated and `.env` contains valid embedding settings:

```powershell
python src/rag/evaluate.py
```

The command writes the per-query retrievals and metrics to `docs/evaluation_results.json`. The result file is generated output and should be regenerated whenever the embedding model, chunking, or database contents change.

## Evaluation set

| Query | Relevant sources |
|---|---|
| Offside position and offence | `doc_011`, `doc_012` |
| Meaning of xG and a 0.2 value | `doc_019`, `doc_024`, `doc_027` |
| PPDA and pressing intensity | `doc_028`, `doc_027`, `doc_024` |
| xT and ball progression | `doc_030`, `doc_024`, `doc_027` |
| Structure of a 4-3-3 | `doc_043`, `doc_046`, `doc_047` |
| Counter-attack after winning the ball | `doc_060`, `doc_061`, `doc_053` |
| Japan's 2-1 win over Spain | `doc_077` |

## Recorded run and interpretation

No live scores are recorded yet in this workspace. The run is currently blocked before retrieval because this shell has no Docker executable and the project has no `.env` file, so PostgreSQL and the embedding API cannot be reached. Recording fabricated rankings would invalidate the evaluation. Once the command runs, this section should report the macro-average values from `evaluation_results.json` and identify the lowest-scoring query families.

Interpretation rules:

- Low MRR with reasonable recall means the right source is present but ranked too low; consider reranking or better chunk boundaries.
- Low recall for one topic suggests missing or poorly labeled corpus coverage.
- Low precision with high recall suggests duplicate or overly broad chunks; reduce overlap or add a reranker.
- Consistently low scores across all families indicate an embedding/model, query embedding, or database/index configuration problem.