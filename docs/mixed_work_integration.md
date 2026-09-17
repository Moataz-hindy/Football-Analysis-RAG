# mixed-work integration

**Integration update:** See [sentiment and analytics](sentiment_and_analytics.md) for current behavior and validation. This document records the earlier implementation.

This branch combines Hatem's committed `week3-integrated` at `b41713e` with Moataz's `agent-graph` at `08c4003`. It was prepared in a separate checkout. Neither source branch was changed.

## Included work

- Hatem's typed retrieval errors, initial and dynamic evidence records, tool statuses, model retries, memory retention, per-agent checkpoints, interruption saves, and protection against overwriting an existing discussion ID.
- Moataz's personas, routing graph, discussion prompts, persona-specific search queries, six-result retrieval, tool schemas, history formatting, duplicate-response check, opinion parsing, web fallback, and Week 1 pipeline changes.
- Moataz's provider-specific tool-call metadata preservation. This is chat adapter compatibility; it does not introduce Hatem's local Gemini embedding backend.

No uncommitted files were imported from Hatem's working directory. In particular, `src/rag_gemini`, its SQL schema, Gemini embedding artifacts, and the local uncommitted Week 1 pipeline rewrite are excluded. Existing committed corpus files are inherited; no new embeddings were generated or copied.

## Conflict decisions

The merge conflicted in `src/agent/agent.py`, `src/agent/llm.py`, and `src/rag/search.py`.

- Initial retrieval uses the persona-specific query and records that exact query and its evidence. Tool failures retain their error status and stop the turn; they do not become ordinary source text.
- The chat adapter keeps bounded retries and raises exhausted failures. It does not return the teammate branch's canned opinion after failed requests, silently disable tools, or synthesize tool calls from a rejected provider response. Provider tool metadata is preserved through retries.
- Search retains keyword fallback for embedding connection failures, HTTP 408/429, and server errors. Authentication/configuration failures and database query failures remain visible. Owned database connections close on every path. Keyword results carry `retrieval_mode: keyword` and a null similarity rather than an invented cosine score. That metadata survives agent evidence and evaluation output.
- Web provider failures raise an error. Only web result entries with an HTTP(S) source URL become sources; generated summaries and error messages are not treated as cited documents. Web sources have no fabricated similarity score. The `ddgs` dependency is declared for the teammate's fallback.
- A duplicate-response retry that fails preserves the tool evidence collected before the retry. Existing runner test doubles now produce distinct turn text, so they test checkpoint behavior without unintentionally invoking duplicate retries.

The combined implementation retains strict tool-round limits and explicit errors for empty model answers. Calculators remain tool events rather than retrieval events.

## Validation

The combined suite passed **156 tests** with network connections blocked, using the existing `temporaldev` Python environment. It includes:

- A complete six-agent, three-round scripted discussion (24 messages including initial opinions), evidence persistence, and opinion-history round trips.
- Model failure, keyboard interruption, disk-save failure, and checkpoint protection.
- New integration checks for keyword fallback, database/auth failures, persona query provenance, web error filtering, duplicate-retry evidence preservation, and provider metadata through retries.

These are offline tests. No live embedding API, web provider, or PostgreSQL instance was exercised, and no paid requests were made. A passing suite does not certify that the inherited corpus is fully embedded or the database is populated.

## Using this branch

Install this branch's requirements in the intended environment before using the new web fallback:

```bash
python -m pip install -r requirements.txt
python -m pytest tests -q
```

Use module entry points from the repository root:

```bash
python -m src.rag.process_all
python -m src.rag.ingest
python -m src.rag.search "What is a low block?"
python -m src.discussion.run_discussion --discussion-id mixed-work-demo
```

Configure the provider and database first. No credentials were copied into this integration checkout. Only run live calls with the intended free-provider settings; the integration itself does not impose a new billing policy on existing provider adapters.

## Remaining validation limits

The inherited Week 1 embedder still uses its original file-skipping and document-level saving behavior. The local Gemini backend and local batch-resume/provenance rewrite were deliberately excluded. Keyword fallback searches already-ingested text; it does not complete missing embeddings or reset a daily quota.

The teammate's personas retain their scenario-specific assumptions, including the Egypt/Argentina fan perspective. Check persona suitability when running other match topics. Prompt improvements alone do not establish factual accuracy.

The next live check should audit corpus/database coverage, then run a small discussion and inspect its saved sources and errors. Preserve existing embedding files before any regeneration.
