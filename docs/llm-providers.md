# LLM Providers and Configuration

The agents, memory summaries, persona generation and the optional analytics
extras all use one adapter, `OpenAICompatibleLLM` (`src/agent/llm.py`). It
talks to **any OpenAI-compatible chat-completions endpoint**, so switching
provider means changing three variables in `.env`. Nothing else changes.

Embeddings for the knowledge base are configured separately (section 4).

---

## 1. Required settings

```ini
LLM_API_KEY=your_key
LLM_BASE_URL=https://provider.example/v1
LLM_MODEL=model-name
```

If any of the three is missing, the adapter raises a `RuntimeError` on the
first request. The model must support **tool/function calling**, because
agents call `knowledge_search`, `web_search` and `calculator`.

## 2. Provider values

All of these use the same adapter. Free-tier limits change often; check the
provider's page before relying on them (last reviewed 2026-09-01).

| Provider | `LLM_BASE_URL` | Example `LLM_MODEL` | Notes |
|---|---|---|---|
| Google Gemini | `https://generativelanguage.googleapis.com/v1beta/openai/` | `gemini-2.5-flash` | Strong quality; free-tier limits not fully published |
| Groq | `https://api.groq.com/openai/v1` | `openai/gpt-oss-120b` | Published free limits (about 30 RPM, 1,000 req/day, 8K TPM); very fast |
| Alibaba Model Studio (Qwen) | `https://dashscope-intl.aliyuncs.com/compatible-mode/v1` | `qwen-plus` | 1M free tokens per model for 90 days; no streaming together with tools |
| OpenRouter | `https://openrouter.ai/api/v1` | `openai/gpt-oss-120b:free` | `:free` models: about 20 RPM and 50 req/day (1,000/day after a $10 top-up); a negative balance returns 402 |
| Mistral | `https://api.mistral.ai/v1` | `mistral-small-latest` | Usable backup |
| Ollama (local) | `http://localhost:11434/v1` | `qwen3:8b` | No quota; needs roughly 6 GB of VRAM. Any non-empty `LLM_API_KEY` works |
| Cerebras | `https://api.cerebras.ai/v1` | provider's current model | Very fast, but a paid tier with a card-backed trial, not a free tier |

Cohere's native API is not OpenAI-compatible, and this repository has no
adapter for it.

## 3. Optional tuning

| Variable | Default | Effect |
|---|---|---|
| `LLM_TEMPERATURE` | `0.2` | Sampling temperature (recorded in every discussion). Use `0` for the most stable runs |
| `LLM_SEED` | unset | Recorded in the discussion metadata when set |
| `LLM_MAX_TOKENS` | `1024` | Maximum tokens per reply |
| `LLM_TIMEOUT_SECONDS` | `60` | Per-request timeout |
| `LLM_MAX_RETRIES` | `3` | Retries after the first attempt for rate limits, connection errors, 408 and 5xx |
| `LLM_RETRY_MAX_WAIT_SECONDS` | `120` | Longest single wait the adapter accepts. If the provider asks for longer, the turn fails instead of stalling |
| `LLM_PACE_WAITS` | `3,8,15` | Extra paced attempts (seconds between them) after the retry budget is used up on a transient error |
| `LLM_PACER_MAX_PER_MINUTE` | `0` (off) | Client-side cap on requests per minute, shared by the whole process |
| `LLM_PACER_MAX_PER_HOUR` | `0` (off) | Client-side cap on requests per hour |

Set the pacer caps a little below your provider's published limits. A 6-agent,
3-round debate makes at least 24 agent turns, plus tool rounds and memory
summaries, so it can use up a small hourly quota in one run.

Retry behaviour is described in
[reliability and checkpointing](reliability-and-checkpointing.md#4-bounded-retries-and-checkpoints).

## 4. Embeddings: keep them unchanged

The knowledge base is embedded at **1024 dimensions** with
`liquid/lfm-2.5-embedding-350m:free` on OpenRouter, and `sql/init_db.sql`
declares `vector(1024)` with an IVFFlat cosine index. Queries must be embedded
with the **same model**, or similarity scores are meaningless.

```ini
OPENAI_API_KEY=your_openrouter_key          # used only for embeddings
OPENROUTER_MODEL=liquid/lfm-2.5-embedding-350m:free
```

These are independent of the chat provider, so you can use Gemini or Groq
for chat and OpenRouter for embeddings at the same time.

Changing the embedding model means re-embedding the whole corpus
(`python -m src.rag.process_all`, then `python -m src.rag.ingest`) and editing
`vector(N)` in `sql/init_db.sql`.

## 5. Checking that it works

1. Put the three `LLM_*` values in `.env`.
2. Start the API: `python -m uvicorn src.api.main:app --port 8000`.
3. Run a short debate, either from the web app or with:

   ```bash
   python -m src.discussion.run_discussion --agents 2 --rounds 1 --discussion-id provider-check
   ```

A configuration error fails on the first turn with a clear message. Rate-limit
problems show up as retries in the log and, if they persist, as a
`failed_partial` discussion record with the failing turn in
`metadata.extra.failed_turns`.

For an interactive check of individual personas and their tools, use
`python scripts/test_agents.py --repo .` (see [manual testing](manual-testing.md)).
