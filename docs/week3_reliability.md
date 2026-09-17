# Week 2–3 reliability fixes

These changes strengthen the existing agents and discussion runner. They do not rebuild the knowledge base or implement Week 4 analytics.

## 1. A failed search is different from no results

`src/rag/search.py` loads the project's root `.env` explicitly. A nearer `.env` under `src/rag` can no longer divert its file lookup. Existing shell environment variables still take priority.

An ordinary search with zero rows returns `[]`. The search CLI now prints `No passages found` instead of just a question heading.

Missing embedding configuration, database login/connection problems, pgvector initialization problems, and embedding/query failures raise `RetrievalError`. The reusable functions no longer call `sys.exit()`. The CLI catches this error and exits with a failure status; agents pass it to the discussion's partial-history handler. Database connections opened by a search are closed even if embedding or SQL fails. Caller-owned connections remain the caller's responsibility.

The tool registry propagates execution errors instead of returning an error sentence as a successful result. A failed tool stops the current agent turn and the discussion. This deliberate policy prevents an infrastructure failure from being treated as evidence. Code that directly calls the registry must now handle exceptions.

## 2. Evidence and tool activity survive saving

Each attempt records its name, arguments, result, timestamp, status, error, and optional metadata. Initial automatic retrieval is included and marked `mode: automatic_initial`; later model-requested knowledge searches have their own events.

The agent retains document ID, chunk index, title, URL, text, and similarity score through the retrieval-tool path. The initial response includes evidence from both its automatic search and subsequent knowledge-search calls. Duplicate source appearances are retained to preserve the event trail.

The existing discussion JSON shape is extended through its metadata fields:

| JSON location | Meaning |
|---|---|
| `config.metadata.schema_version` | `2` for newly saved records |
| `messages[].metadata.tool_events` | All completed-turn tool/search attempts, including calculator results |
| `messages[].retrieval_events` | Knowledge searches only |
| `messages[].retrieval_events[].metadata.results` | The actual returned evidence |
| `messages[].retrieval_events[].metadata.status` | Success or failure status when supplied |
| `metadata.extra.failed_turns` | Agent, round, error and recorded attempts from turns that did not finish |
| `config.metadata.current_round` | Round reached |
| `config.metadata.last_completed_round` | Last round for which every agent has a saved message; null before any complete round |

Failed turns are not fabricated as normal messages or opinion snapshots. Their events are stored separately. `total_retrieval_events` counts knowledge searches attached to completed messages; failed-turn attempts must be inspected in `failed_turns`. A successful empty search is still a search event, so a positive event count alone does not prove evidence was found or used.

Existing files can still be loaded; missing new metadata stays absent. New records do not retroactively repair old evidence. Source lists record evidence supplied to the agent, not proof that every passage was cited or used correctly. Read the final response to verify actual use.

## 3. Memory uses the chat model

`ConversationMemory` accepts a chat adapter. The full runner supplies its configured adapter; other callers lazily create `OpenAICompatibleLLM`, using the `LLM_*` settings rather than the embedding model.

When the history exceeds its window, the extra old turns are summarized together. Only after a non-empty, valid summary succeeds are those turns removed. If the request fails, both the existing summary and original turns remain. A later successful summary processes the backlog.

The tradeoff is that repeated summary failures allow memory/context to grow. This avoids silent data loss but can increase later input tokens. Summarization is itself a chat request and uses the same retry policy. The current runner is sequential; a shared adapter is not intended for concurrent agent calls.

## 4. Bounded retries and checkpoints

The chat adapter retries rate limits, connection/time-out failures, HTTP 408 and server errors. Other client errors, such as invalid authentication, fail immediately. It prefers `retry-after-ms`, `Retry-After` seconds or HTTP date, then a provider message such as `try again in 13.9s`; otherwise it uses bounded exponential backoff.

- `LLM_MAX_RETRIES`: retries after the first attempt, default 3.
- `LLM_RETRY_MAX_WAIT_SECONDS`: maximum acceptable delay for one retry, default 120 seconds. A larger requested delay stops the turn instead of waiting indefinitely.
- SDK retries are disabled so the adapter and SDK do not multiply retries.
- An explicit `max_retries=0` still disables adapter retries, preserving the older test runner's external retry control.

Only the model request is retried. Already executed tools and completed agent responses are not replayed. The embedding client retains its own existing SDK behavior; this work does not add a resumable embedding batch pipeline or bypass provider quotas.

The full runner atomically saves after each completed agent response, including initial opinions. Thus every completed round is saved as well. Its record status becomes `completed`, `failed_partial`, or `interrupted` when the runner finishes or handles a turn failure/Ctrl+C. A hard process kill leaves the last checkpoint marked `running`; an in-flight response may be lost. Disk errors stop execution; the last successfully replaced file remains intact if the next atomic write fails.

Checkpointing is preservation for inspection, not automatic resumption. A subsequent run starts fresh. The runner rejects an existing discussion ID to prevent an accidental restart overwriting prior history. IDs use letters, digits, underscores and hyphens. The low-level save function intentionally replaces the current run's checkpoint.

The persistence bridge also preserves an explicit temperature of zero and serializes graph wrappers without confusing NetworkX's metadata with the graph itself.

## 5. Verification

From the existing project environment:

```bash
python -m pytest tests -q
```

The regression tests simulate unavailable databases, empty searches, tool failures, memory failures, rate limits, exhausted retries, interruptions and disk-write failure. A full fake six-agent run checks 24 messages, 24 opinions, every checkpoint, source metadata and separate calculator events. Network/database access is blocked in the new regression tests; they spend no API tokens.

The live Week 3 demonstration still requires a populated, consistent knowledge base and working provider credentials. Do not interpret an offline test pass as proof of factual quality or successful live retrieval.

Verified after these changes: **124 tests passed** (the original 88 plus 36 regression cases), using the existing `temporaldev` environment. No live model or database calls were made.
