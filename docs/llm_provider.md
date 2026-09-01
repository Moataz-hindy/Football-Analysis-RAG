# Free LLM Providers — Integration Guide

Every provider here has a **free API tier** you can call from Python. No paid plans, no CLI
tools — just API keys you can get today and use from `src/agent/`.

Verified 2026-09-01 against commit `e0026e3`.

---

## Quick answer

| Provider | What's free | OpenAI-compatible? | Tools? | Verdict |
|---|---|---|---|---|
| **Groq** | 30 RPM · 1,000 req/day · 8K TPM | Yes | Yes | **Start here.** Real numbers, no card |
| **Alibaba (Qwen)** | 1M tokens **per model**, 90 days | Yes | Yes | Best token budget |
| **OpenRouter** | 20 RPM · 50 req/day (1,000 after $10) | Yes | Yes | Already wired for embeddings |
| **Google Gemini** | Free tier, limits unpublished | Yes | Yes | Strongest model, vaguest limits |
| **Mistral** | "Free mode" default, limits unpublished | Yes | Yes | Fine backup |
| **Ollama** | Unlimited, local | Yes | Yes | Needs ~6 GB VRAM |
| **Cohere** | 1,000 calls/month · 20 RPM | **No** | Yes | Needs its own adapter |
| ~~Cerebras~~ | ~~$5 credits, card required, 30-day expiry~~ | Yes | Yes | **Not free — excluded** |

---

## 1. Why this is easier than it looks

**Six of the seven use the OpenAI wire format.** So you write **one** adapter class and switch
providers by changing three environment variables. No per-provider code.

This works because `Agent._parse_result()` in `src/agent/agent.py` already reads the OpenAI
response shape — `result.choices[0].message.content` and
`.tool_calls[].function.name` / `.arguments`. Return the SDK response object untouched and the
agent's tool loop needs zero changes.

```python
#              same class, three different strings
OpenAI(api_key=KEY, base_url=BASE_URL)   # → chat.completions.create(model=MODEL, ...)
```

Only **Cohere** breaks the pattern (its own `/v2/chat` shape) — §4.7 has a separate adapter.

---

## 2. Two fixes the code needs first

Both are provider-independent. 2.2 is a hard blocker — memory is broken until it is done. 2.1
the adapter degrades around, so it is a quality fix rather than a blocker.

### 2.1 Tools have no JSON schema

`ToolInterface` (`src/agent/interfaces.py`) exposes only `name`, `description`, `run()`. Every
provider's function calling needs a `parameters` JSON Schema. Add one:


```python
# src/agent/interfaces.py — inside ToolInterface (additive, breaks nothing)
@property
def parameters(self) -> dict[str, Any]:
    return {"type": "object", "properties": {}, "additionalProperties": True}
```

```python
# src/tools/knowledge_search.py — override with the real schema
@property
def parameters(self) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search topic or question."}
        },
        "required": ["query"],
    }
```

Do the same for `src/tools/calculator.py`. Without it the adapter falls back to an open schema
and the model has to guess argument names, which costs accuracy. (Hard-coding a
`{"query": string}` schema inside the adapter instead would break the moment a second tool
takes different arguments — and there already is one.)

### 2.2 `memory.py` sends chat requests to an embedding model

`src/agent/memory.py` imports `get_client` from `src/rag/search.py`, so its
`chat.completions.create(model=model, ...)` call uses `OPENROUTER_MODEL` — which is
`liquid/lfm-2.5-embedding-350m:free`, an **embedding** model. That cannot work.

Fix: pass the LLM in instead of reaching into the RAG layer.

```python
class ConversationMemory(MemoryInterface):
    def __init__(self, llm: LLMInterface, max_turns: int = 5):
        self._llm = llm      # was: get_client() from src.rag.search
```

---

## 3. The shared adapter — already written

`src/agent/llm.py` holds it: `OpenAICompatibleLLM`, one class covering Groq, Alibaba,
OpenRouter, Gemini, Mistral, and Ollama. You never edit it to change provider — that is three
environment variables (§4).

Read the file for the rest; three things in it are not obvious.

**It builds tool schemas defensively.** `to_tool_schema()` reads `tool.parameters` via
`getattr(..., DEFAULT_PARAMETERS)`, so the adapter works before §2.1 lands.

**It repairs the message history.** `Agent.run()` appends the assistant turn with no
`tool_calls` and each tool turn with no `tool_call_id` (`src/agent/agent.py:43`, `:51`). The
OpenAI wire format requires both, so round 2 of a tool loop would 400.
`_repair_tool_messages()` rebuilds them from the calls the adapter emitted, paired by position
— reliable because `Agent.run()` appends exactly one tool message per call, in call order. It
copies rather than mutating the list it is given. Fixing `agent.py` directly would be cleaner;
the adapter does it so that shared file stays untouched.

**It returns a dict, not the SDK response object.** `{"content": ..., "tool_calls": [...]}`.
`Agent._parse_result()` accepts that shape (`agent.py:120`) and coerces content with `str()`,
so handing it OpenAI's `content=None` would write the literal string `"None"` into the
transcript. `message.content or ""` avoids that. The raw response stays on
`llm.last_response` if you want `usage` or `finish_reason`.

Wire it up:

```python
from src.agent.llm import OpenAICompatibleLLM
from src.agent.memory import ConversationMemory
from src.agent.retrieval import RAGRetrieval
from src.agent.tool_registery import ToolRegistry
from src.tools.knowledge_search import KnowledgeSearchTool

llm = OpenAICompatibleLLM()                    # reads LLM_* env vars
config = AgentConfig(
    persona=persona,
    memory=ConversationMemory(llm=llm),
    tools=ToolRegistry([KnowledgeSearchTool()]),
    retrieval=RAGRetrieval(k=3),
    llm=llm,
)
```

Settings that matter, whichever provider you pick. The first four are the adapter's defaults;
override them with a constructor argument or the environment variable in brackets.

| Setting | Default | Why |
|---|---|---|
| `temperature` [`LLM_TEMPERATURE`] | `0.2` | `parse_opinion()` needs the exact `STANCE:` / `REASONING:` / `SOURCES USED:` shape |
| `max_tokens` [`LLM_MAX_TOKENS`] | `1024` | An opinion is 300–800 tokens; the cap stops runaway generations eating your quota |
| `timeout` [`LLM_TIMEOUT_SECONDS`] | `60` | Free endpoints stall; a hung request blocks the whole tool loop |
| `max_retries` [`LLM_MAX_RETRIES`] | `3` | Free tiers return 429s constantly — the SDK backs off for you |
| `max_tool_rounds` | `5` | Not an adapter setting — it is `Agent(config, max_tool_rounds=...)`. Each round is another request against your daily cap, so pass `3` |

**Free-tier budgeting:** one agent task = 2–3 chat requests (search → answer) + 1 embedding
call. Groq's 1,000 req/day is ~300 agent runs. OpenRouter's 50/day is ~15.

---

## 4. Provider guides

Each one: get the key, set three variables, done. Model IDs move — check the provider's model
list before a demo.

### 4.1 Groq — best free numbers

Sign up at `console.groq.com`, create a key. No credit card.

```dotenv
LLM_API_KEY=gsk_...
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=openai/gpt-oss-120b
```

Free plan, per model: **30 RPM · 1,000 req/day · 8K TPM · 200K tokens/day.** Same for
`qwen/qwen3.8-27b`. Cached tokens don't count toward limits.

**Gotchas.** 8K tokens/minute is the real ceiling, not the request count — at ~3–4K tokens per
agent request that's roughly two calls per minute, so add a small sleep between runs. Limits are
per *organization*, not per user, so teammates sharing an org share the budget. Fastest latency
of anything here.

### 4.2 Alibaba Model Studio (Qwen) — biggest token budget

Sign up at Alibaba Cloud, activate Model Studio, create a key in the console.

```dotenv
LLM_API_KEY=sk-...
LLM_BASE_URL=https://dashscope-intl.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen-plus
```

Free: **1,000,000 tokens per model**, valid **90 days** from activation. Input and output share
the pool. Each model has its own separate million, and a dated snapshot counts as a different
model from the `-latest` alias — so `qwen-plus` and `qwen-turbo` are 2M tokens between them.
Their embedding models get 1M free tokens each too.

**Gotchas.**
- **`tools` cannot be combined with `stream=True`.** Don't stream in the agent loop.
- Function calling is documented for `qwen-turbo`, `qwen-plus`, `qwen-max`. `n` is forced to 1
  once tools are present.
- **Keys are region-bound.** A Beijing key on the Singapore endpoint returns 401
  `invalid_api_key` — that's a region mismatch, not a bad key.
- The docs contradict themselves on whether the free quota covers Singapore or Beijing only.
  Check the console before relying on it.
- Real-time inference only (no batch), and re-registering does not get you a second grant.
- Newer workspace-scoped hosts exist
  (`https://{WorkspaceId}.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1`) and Alibaba
  prefers them; the host above still works and needs no workspace ID.

### 4.3 OpenRouter — already in the project

The project already uses this for embeddings, so you may already have a key.

```dotenv
LLM_API_KEY=sk-or-v1-...
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=openai/gpt-oss-120b:free
```

Free (`:free` models): **20 RPM · 50 req/day**, rising to **1,000/day** once you've bought $10
of credit *ever* (lifetime purchases, not current balance).

**Gotchas.**
- 50/day is ~15 agent runs. Tight for development.
- Limits are global per account — extra keys or accounts don't help.
- A **negative balance triggers 402 even on free models.** Top up above zero.
- The `:free` catalogue churns hard (14 zero-cost IDs in Aug 2026, down from 20 weeks earlier).
  Verify with `GET /api/v1/models` before a demo.
- `openrouter/free` is an auto-router that picks a free model at random and filters for the
  features your request needs, including tool calling — useful when a specific slug disappears.
- Bonus: automatic fallback routing retries other upstream providers on a 429 before erroring.

### 4.4 Google Gemini — strongest model, vaguest limits

Get a key from Google AI Studio (`aistudio.google.com`). Use the OpenAI compatibility layer so
the shared adapter works unchanged.

```dotenv
LLM_API_KEY=AIza...
LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
LLM_MODEL=gemini-2.5-flash
```

Free tier is real and needs no card. Function calling with `tool_choice="auto"` works through
the compat layer, and so does `client.embeddings.create`.

**Gotchas.**
- **Google no longer publishes free-tier RPM/TPM/RPD numbers.** They're per-project and only
  visible in AI Studio, so you cannot plan capacity from the docs. Limits are tracked on three
  axes (requests/min, input tokens/min, requests/day) and breaching any one errors. Daily quotas
  reset at midnight Pacific.
- **Free-tier content may be used to improve Google's products.** Worth a sentence in the report
  — the data here is public football articles, so the exposure is low, but say so rather than
  discover it later.
- The compatibility layer is officially beta; Gemini-only features need `extra_body`.
- Preview/experimental models get tighter caps than stable ones.

### 4.5 Mistral — fine as a backup

Key from `console.mistral.ai`. "Free mode" is the default tier — no card needed.

```dotenv
LLM_API_KEY=...
LLM_BASE_URL=https://api.mistral.ai/v1
LLM_MODEL=mistral-small-latest
```

**Gotchas.** Mistral doesn't publish the free-tier numbers either — they're per-account at
`admin.mistral.ai/plateforme/limits`, described only as "the lowest limits, intended for
evaluation and prototyping." Limits are per *model*, so switching models changes them, and
they're capped on three axes (requests/second, tokens/minute, tokens/month). Adding prepaid
credits does **not** raise limits — only billed consumption does.

### 4.6 Ollama — free forever, runs on your machine

```bash
# install from ollama.com, then:
ollama pull qwen3:8b
ollama serve
```

```dotenv
LLM_API_KEY=ollama
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=qwen3:8b
```

The key is ignored but the OpenAI SDK requires a non-empty string.

**Hardware.** Ollama's own floor is 8 GB RAM, ~10 GB disk, 64-bit AVX2 CPU. Per model at
Q4_K_M: 7–8B ≈ 6 GB VRAM, 13–14B ≈ 11 GB, 32B ≈ 24 GB, 70B ≈ 42 GB. `qwen3:8b` is ~5 GB of
weights. CPU-only works but is slow enough to make a 3-round tool loop painful.

**Gotchas.** Ollama's tool-calling docs demo `qwen3` exclusively and don't claim library-wide
support — pick a model tagged with the `tools` capability. Small local models drop or malform
tool calls more often than hosted ones, which surfaces as a `RuntimeError` after
`max_tool_rounds`. Good for offline dev and CI; risky as the demo path.

### 4.7 Cohere — needs its own adapter

Free **trial keys** from `dashboard.cohere.com`: **1,000 API calls/month**, 20 requests/minute
on the Chat endpoint. Embed on a trial key gets 2,000 inputs/minute — the same as production.

Cohere is **not** OpenAI-shaped, so the shared adapter won't work. Its `/v2/chat` returns
`message.tool_plan` (stated reasoning) and `message.tool_calls`, and tool results go back as a
`role: "tool"` message carrying `{"type": "document", ...}`. The cheapest way to keep `Agent`
untouched is to translate the response into the shape `_parse_result()` expects:

```python
# src/agent/llm_cohere.py
import os
from types import SimpleNamespace

import cohere                      # pip install cohere

from .interfaces import LLMInterface
from .llm import to_tool_schema    # same schema format works for Cohere


class CohereLLM(LLMInterface):
    def __init__(self, model="command-a-plus-05-2026", temperature=0.2, max_tokens=1024):
        self._co = cohere.ClientV2(api_key=os.environ["COHERE_API_KEY"])
        self._model, self._temperature, self._max_tokens = model, temperature, max_tokens

    def generate(self, messages, tools=None):
        resp = self._co.chat(
            model=self._model,
            messages=messages,
            tools=[to_tool_schema(t) for t in tools] if tools else None,
            temperature=self._temperature,
            max_tokens=self._max_tokens,
        )
        # Repackage into the OpenAI shape Agent._parse_result() reads.
        text = "".join(c.text for c in (resp.message.content or []) if c.type == "text")
        calls = [
            SimpleNamespace(
                id=tc.id,
                function=SimpleNamespace(name=tc.function.name,
                                         arguments=tc.function.arguments),
            )
            for tc in (resp.message.tool_calls or [])
        ]
        msg = SimpleNamespace(content=text, tool_calls=calls or None)
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)])
```

**Worth knowing.** Cohere returns native **citations** with `start`/`end` spans pointing at the
source document — that maps unusually well onto this project's `SOURCES USED:` requirement and
the "do not invent sources" instruction. If you want that, don't discard `resp.message.citations`
in the shim. Against it: 1,000 calls/month is ~300 agent runs *total*, and this is the only
provider needing extra code plus an extra dependency.

### 4.8 Cerebras — excluded, not actually free

Listed because it looks free and isn't. The "Free Trial" is **$5 in credits that require a
verified payment method** and **expire 30 days** after they're granted; without a card on file,
API access stays inactive. Trial limits are 5 RPM / 30K TPM / 1M tokens per day on
`gpt-oss-120b` and `gemma-4-31b`. It's a paid tier with a trial, not a free tier.

---

## 5. Embeddings — leave this alone

The 81 documents are already embedded at **1024 dimensions**, and the IVFFlat index in
`sql/init_db.sql` was built at that width with `vector_cosine_ops`. Query embeddings must come
from the **same model** or similarity scores are meaningless.

So keep `liquid/lfm-2.5-embedding-350m:free` on OpenRouter for embeddings, **independently of
which provider you choose for chat.** Two providers is fine — the embedding key and the chat key
are separate variables.

Changing the embedding model means re-running the whole Week 1 pipeline and editing `vector(N)`
in `sql/init_db.sql`. If you ever do: Gemini (`gemini-embedding-001`), Alibaba (1M free tokens
per embedding model), and Cohere (2,000 inputs/min on a trial key) all have free embeddings.

---

## 6. Recommended setup

**Primary: Groq** (`openai/gpt-oss-120b`). It's the only provider publishing real free numbers
you can plan against, needs no card, and is the fastest. 1,000 requests/day is ~300 agent runs.

**Fallback order** if Groq's 8K TPM gets in your way:
1. **Alibaba Qwen** (`qwen-plus`) — 1M tokens is a bigger budget than Groq's per-minute cap
   allows you to spend anyway. Remember: no streaming with tools.
2. **Google Gemini** (`gemini-2.5-flash`) — best model quality of the free options.
3. **OpenRouter** — you already have the key; 50/day is demo-only until you spend $10.
4. **Ollama** (`qwen3:8b`) — offline dev and CI, if the machine has ~6 GB VRAM.

Because all four are the same adapter, "falling back" is editing three lines of `.env`.

---

## 7. `.env.example`

Placeholders only — **never commit a real key.** `.env` is already in `.gitignore:3`; keep it
there.

```dotenv
# --- Postgres ---------------------------------------------------------
DB_HOST=localhost
DB_PORT=5432
DB_NAME=football_intelligence
DB_USER=postgres
DB_PASSWORD=

# --- Chat LLM (see docs/llm_provider.md §4 for per-provider values) ---
LLM_API_KEY=
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=openai/gpt-oss-120b
LLM_TEMPERATURE=0.2
LLM_MAX_TOKENS=1024
LLM_TIMEOUT_SECONDS=60
LLM_MAX_RETRIES=3
# tool rounds are not an env var — pass Agent(config, max_tool_rounds=3)

# --- Embeddings: frozen, do not change (see §5) -----------------------
OPENROUTER_API_KEY=
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_EMBEDDING_MODEL=liquid/lfm-2.5-embedding-350m:free
```

Two things to fix in the current `.env.example`:

1. **Line 6 reads `OPENAI_API_KEY = your key here #hatem key`** — spaces around `=`, a committed
   comment naming a teammate's key, and a name that misdescribes an OpenRouter credential.
   Replace it with an empty `OPENROUTER_API_KEY=`.
2. **There is no chat-model variable at all** — the omission behind §2.2.

Renaming touches two call sites: `get_client()` in `src/rag/search.py:30` and the duplicate in
`src/rag/process_all.py:20`. To avoid breaking teammates' existing `.env` files mid-week, read
the new name and fall back to the old one:

```python
api_key = (os.environ.get("OPENROUTER_API_KEY")
           or os.environ.get("OPENAI_API_KEY", "")).strip()
```

Worth doing once as due diligence, not because there's evidence of a leak: scan history with
`git log -p -S 'sk-or-'` (or a secret scanner). If a live key was ever committed, rotate it on
the provider dashboard — deleting the line from the current tree does not remove it from history.

---

## 8. Check that it works

`tests/test_llm.py` already covers the adapter offline — mocked client, no key, no database:

```bash
python -m pytest tests/test_llm.py -q      # 11 passed
```

It asserts that `generate()` forwards model/temperature/max_tokens, that tools serialise to the
right schema, that a canned tool-call response survives `Agent._parse_result()`, and that the
`tool_call_id` repair pairs correctly across rounds and parallel calls.

That leaves one thing only a real key can prove — that the provider accepts your key and model:

```python
# scripts/smoke_llm.py
from dotenv import load_dotenv
from src.agent.llm import OpenAICompatibleLLM
from src.tools.knowledge_search import KnowledgeSearchTool

load_dotenv()
llm = OpenAICompatibleLLM()
result = llm.generate(
    messages=[{"role": "user", "content": "Search for Arsenal's pressing structure."}],
    tools=[KnowledgeSearchTool()],
)
print("content:   ", result["content"])
print("tool_calls:", result["tool_calls"])
print("usage:     ", llm.last_response.usage)
```

A tool call in the output means the provider, the key, and your schema from §2.1 are all correct.
If `tool_calls` is empty but you got prose, the model chose not to search — try a more explicit
prompt before assuming the schema is broken. Keep this the only test that needs a key, so CI
never does.

**Also worth fixing while you're in there:** `Agent.run()` loops
`for _ in range(self.max_tool_rounds + 1)` with a `for...else` that raises
`RuntimeError("LLM exceeded the maximum number of tool rounds")`. The `else` fires on any
completion without `break`, so a run that uses every iteration and *succeeds* still raises. And
`ToolRegistery.execute()` catches every exception and returns the message as a string, so a
broken tool looks to the model like a successful result containing the word "Error".

---

## 9. Report block for `week2.md` §11

> **Provider:** Groq (free tier, OpenAI-compatible endpoint `https://api.groq.com/openai/v1`).
> Embeddings stay on OpenRouter — the pgvector index is bound to the Week 1 embedding model.
>
> **Model:** `openai/gpt-oss-120b` for chat and tool calling. Swappable by environment variable
> to `qwen-plus` (Alibaba), `gemini-2.5-flash` (Google), or `qwen3:8b` (local Ollama) without
> code changes.
>
> **Reason for selection:** free with no credit card; the only free provider that publishes
> concrete, plannable limits (30 RPM · 1,000 req/day · 8K TPM · 200K tokens/day); fastest latency
> of the free options; OpenAI-compatible, so `Agent._parse_result()` needs no modification;
> supports function calling, which the whole tool loop depends on; and no hardware requirement,
> unlike a local model on machines with no guaranteed GPU.
>
> **Important configuration:** `temperature=0.2` (the opinion parser depends on a fixed output
> shape), `max_tokens=1024`, `timeout=60s`, `max_retries=3` for free-tier 429s,
> `max_tool_rounds=3`, `tool_choice="auto"`, and tool schemas generated from
> `ToolInterface.parameters`. Credentials come from environment variables via `python-dotenv`;
> `.env` is gitignored and no key appears in the repository.
>
> **Required environment variables:** `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`,
> `LLM_TEMPERATURE`, `LLM_MAX_TOKENS`, `LLM_TIMEOUT_SECONDS`, `LLM_MAX_RETRIES`,
> `AGENT_MAX_TOOL_ROUNDS`, `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL`,
> `OPENROUTER_EMBEDDING_MODEL`, plus `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`.

---

## 10. Sources

Official docs:
- [Groq — rate limits](https://console.groq.com/docs/rate-limits)
- [Alibaba Model Studio — OpenAI-compatible API](https://help.aliyun.com/en/model-studio/compatibility-of-openai-with-dashscope)
- [Alibaba Model Studio — free quota for new users](https://help.aliyun.com/en/model-studio/new-free-quota)
- [OpenRouter — limits](https://openrouter.ai/docs/api_reference/limits) · [free router](https://openrouter.ai/docs/guides/routing/routers/free-router) · [free models](https://openrouter.ai/collections/free-models)
- [Gemini — OpenAI compatibility](https://ai.google.dev/gemini-api/docs/openai) · [rate limits](https://ai.google.dev/gemini-api/docs/rate-limits)
- [Mistral — API rate limits](https://help.mistral.ai/en/articles/698531-why-am-i-hitting-api-rate-limits-and-how-do-i-increase-them)
- [Cohere — rate limits](https://docs.cohere.com/docs/rate-limits) · [tool use](https://docs.cohere.com/docs/tool-use-overview)
- [Cerebras — rate limits](https://inference-docs.cerebras.ai/support/rate-limits)
- [Ollama — tool calling](https://docs.ollama.com/capabilities/tool-calling)

Secondary (cross-checked, treat as approximate):
- Ollama VRAM sizing — [computingforgeeks](https://computingforgeeks.com/how-much-vram-to-run-llm/), [localaimaster](https://localaimaster.com/blog/ollama-system-requirements), [localllm.in](https://localllm.in/blog/ollama-vram-requirements-for-local-llms)
- Mistral free-tier token estimate (~1B/month) — [pricepertoken](https://pricepertoken.com/endpoints/mistral/free)
- OpenRouter free-model churn — [teamday.ai](https://www.teamday.ai/blog/best-free-ai-models-openrouter-2026)

Google and Mistral free-tier numbers are unpublished by design — check your own dashboard.

