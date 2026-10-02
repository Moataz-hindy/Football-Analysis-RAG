# Agent Memory and Knowledge Retrieval

How an agent remembers earlier turns (`src/agent/memory.py`) and how it pulls
evidence from the football knowledge base (`src/agent/retrieval.py`,
`src/rag/search.py`).

---

## 1. Conversation memory

`ConversationMemory` is a **summarised sliding window**.

1. **Recent turns, verbatim.** The last `max_turns` interactions (default 5)
   are kept word for word, so the agent can quote the immediate back-and-forth
   exactly.
2. **Older turns, summarised.** When the window overflows, the extra old turns
   are sent to the chat LLM together with the current running summary, and a
   new summary replaces it. Turns are deleted **only after** a valid, non-empty
   summary comes back.
3. **Reading memory.** The agent gets the running summary followed by the
   verbatim recent turns. The prompt labels memory as prior context, "not
   evidence", so the agent does not treat its own earlier guesses as facts (see
   [prompt design](prompt-design.md)).

The summary uses the same chat model and retry policy as the agent (`LLM_*`
settings), not the embedding model.

### Limitations

- **Detail loss.** Exact numbers or niche terms from early turns can be
  abstracted away by the summary.
- **Growth on failure.** If summarisation fails (for example a rate limit), no
  turns are dropped. Nothing is lost, but the prompt grows until a later
  summary succeeds.
- **In-process only.** Discussion memory lives in the Python process. The
  saved discussion JSON keeps the full transcript, but a restarted run starts
  with empty memory.
- **Sequential use.** A shared LLM adapter is not meant for concurrent agent
  calls; the runner is sequential.

The platform's per-user memory (`/profile/memory`, `src/platform/memory.py`) is
a separate, persisted feature for users, not agent context.

---

## 2. Knowledge retrieval

`RAGRetrieval` (`src/agent/retrieval.py`) connects agents to the knowledge base
built by the ingestion pipeline: 1,200-character chunks with 200-character
overlap, embedded as 1024-dimensional vectors and stored in PostgreSQL +
pgvector (IVFFlat cosine index, table `football_chunks`).

1. The agent asks a question; `search()` in `src/rag/search.py` embeds it with
   the configured embedding model (`OPENAI_API_KEY` + `OPENROUTER_MODEL`).
2. pgvector returns the nearest chunks by cosine distance. Agents request 6
   results by default.
3. Results become typed `RetrievedSource` objects carrying `doc_id`,
   chunk index, title, URL, text and similarity score.

Agents use retrieval twice: automatically at the start of a turn with a
persona-specific query, and again whenever the model calls the
`knowledge_search` tool.

### When something fails

| Situation | Result |
|---|---|
| Search succeeds with no rows | `[]`: a normal empty result |
| Embedding provider times out, is rate-limited (408/429) or has a 5xx error | Falls back to a **keyword search** over already-ingested text. Results are labelled `retrieval_mode: keyword` with `similarity: null`, never an invented score. |
| Missing embedding key/model, database unreachable, pgvector not set up, other SQL errors | `search()` raises `RetrievalError` |
| Any failure inside `RAGRetrieval.retrieve()` | Logged as a warning; the agent gets no sources and continues with its persona knowledge and `web_search` |

So a stopped PostgreSQL container degrades a debate (fewer or no sources) but
does not crash it. Every retrieval attempt is still recorded in the saved
discussion (`retrieval_events`), see
[reliability and checkpointing](reliability-and-checkpointing.md).

### Web search

The `web_search` tool (`src/tools/web_search.py`) uses Tavily when
`TAVILY_API_KEY` is set, and otherwise DuckDuckGo (`ddgs`). Only results with
an HTTP(S) URL count as sources.

### Checking retrieval by hand

```bash
python -m src.rag.search "What is a low block?"
```

Retrieval quality is measured by the benchmark in
[retrieval evaluation](retrieval-evaluation.md).
