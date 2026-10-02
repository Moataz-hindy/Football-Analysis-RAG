# Documentation

Reference documentation for the Football Analysis RAG platform. Start with the
[project README](../README.md) for setup and running; the pages below go deeper.

## How it works

| Page | Covers |
|---|---|
| [Discussion engine](discussion-engine.md) | How a debate runs, the saved JSON record, run IDs and reproducibility |
| [Agent graph and routing](agent-graph-and-routing.md) | Who talks to whom: the three graph types and the router |
| [Agent memory and retrieval](agent-memory-and-retrieval.md) | Summarised memory window, pgvector retrieval, keyword and web fallbacks |
| [Prompt design](prompt-design.md) | How persona, memory, sources and tool results reach the model |
| [Reliability and checkpointing](reliability-and-checkpointing.md) | Failure handling, retries, evidence records and per-turn checkpoints |
| [Analytics](analytics.md) | Stance scoring, agreement, influence, sentiment, charts, reports and CLI |

## Using and operating it

| Page | Covers |
|---|---|
| [API reference](api-reference.md) | Every REST endpoint, request fields, auth and queue behaviour |
| [LLM providers](llm-providers.md) | Choosing a chat provider, all `LLM_*` settings, embeddings |
| [Retrieval evaluation](retrieval-evaluation.md) | The labelled retrieval benchmark and how to read it |
| [Manual testing](manual-testing.md) | Live checks: agent console, resumable embedding, offline viewer |
| [Deployment](../DEPLOYMENT.md) | Docker Compose deployment |
| [Frontend](../frontend/README.md) | The React web app: pages, components, development |

## History

[`history/`](history/) holds dated integration notes and an early design draft.
They record what was true on that date and are kept for traceability; the
pages above describe the current code.

| Note | Summary |
|---|---|
| [2026-09-14 · mixed-work integration](history/2026-09-14-mixed-work-integration.md) | Merging the reliability and agent-graph branches |
| [2026-09-14 · Week 4 analytics design draft](history/2026-09-14-week4-analytics-design-draft.md) | Original analytics design, superseded by [analytics](analytics.md) |
| [2026-09-15 · sentiment and analytics integration](history/2026-09-15-sentiment-and-analytics-integration.md) | VADER sentiment and the first analytics package |
| [2026-09-16 · main merge](history/2026-09-16-main-merge.md) | Bringing the trajectory visualisation into mixed-work |

## Conventions

- File names are lowercase `kebab-case.md`; dated notes start with `YYYY-MM-DD-`.
- Document current behaviour and link to code paths. When behaviour changes,
  update the page rather than appending a changelog paragraph.
- Never record estimated results as measured ones; mark missing results as missing.
