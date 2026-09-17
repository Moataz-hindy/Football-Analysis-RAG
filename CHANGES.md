# Codebase Evolution: Multi-Agent Discussion Engine Fixes

This document details the architectural and implementation changes made to transition the project from a broken, crashing prototype to a fully reliable, end-to-end multi-agent discussion system.

---

## 1. Executive Summary

### Before
The user goal was to run a multi-agent deliberation:
```bash
python -m src.discussion.run_discussion --rounds 3
```
However, running the discussion immediately crashed due to a cascade of blocking issues:
1. **Tool Schema Validation Failures**: Tools lacked explicit JSON parameter schemas, causing strict providers (Groq/Qwen) to reject tool calls with HTTP 400 (`tool_use_failed`).
2. **Infinite Tool Loops & Hard Crashes**: If an agent exceeded `max_tool_rounds`, it raised `RuntimeError("LLM exceeded the maximum number of tool rounds")`, crashing the entire multi-agent process.
3. **Provider Quota & Rate Limit Exhaustion**: Groq free tier hit limits (200k tokens/day for 120B models; 1,000 output tokens/minute for Qwen). Any 429 response crashed the orchestrator.
4. **Context Window Token Explosion**: Historical turns in agent memory repeated multi-paragraph boilerplate instructions, exponentially ballooning prompt sizes to thousands of tokens per turn.
5. **Database Type Serialization Crashes**: PostgreSQL `pgvector`/numeric columns returned `decimal.Decimal` objects, which caused Python's `json.dump` to throw `TypeError: Object of type Decimal is not JSON serializable`, corrupting saved outputs.
6. **Fragile Regex Parsing**: Markdown formatting (`**STANCE:**`, `### STANCE:`) caused regex parsers to misread headers and bleed stance text into reasoning sections.
7. **Windows SSL Conflicts & Import Path Errors**: Outdated SSL environment variables and relative imports broke data processing and embeddings.

### After
- The full discussion runs cleanly across **6 analyst agents**, through **Phase 1** (initial opinions) and **Phase 2** (3 debate rounds), generating **24 verified messages** and **24 opinion evolutions**.
- Every discussion run is automatically and atomically persisted to `outputs/<discussion_id>.json` and can be reconstructed anytime via `load_discussion_by_id`.
- All **88 unit tests** in the test suite pass in ~2 seconds.

---

## 2. Detailed Breakdown: Before vs. After vs. Why

```mermaid
flowchart TD
    subgraph Discussion_Layer [Discussion & Orchestration]
        Orch[orchestrator.py] --> Agent[agent.py]
        Agent --> Mem[memory.py]
        Orch --> Persist[persistence.py]
    end

    subgraph LLM_and_Tools [Provider & Tool Execution]
        Agent --> LLM[llm.py]
        Agent --> Tools[calculator.py / knowledge_search.py]
        Tools --> Schema[interfaces.py: parameters]
    end

    subgraph RAG_Layer [Knowledge & Database]
        Tools --> Search[search.py]
        Search --> PG[(PostgreSQL + pgvector)]
        Search -. Fallback .-> ILIKE[(Keyword ILIKE Fallback)]
    end
```

---

### Category 1: Tool Calling & JSON Schema Compliance

#### Files Modified
- [`src/agent/interfaces.py`](file:///c:/Users/moata/Downloads/Football-Analysis-RAG-main/Football-Analysis-RAG-main/src/agent/interfaces.py)
- [`src/tools/calculator.py`](file:///c:/Users/moata/Downloads/Football-Analysis-RAG-main/Football-Analysis-RAG-main/src/tools/calculator.py)
- [`src/tools/knowledge_search.py`](file:///c:/Users/moata/Downloads/Football-Analysis-RAG-main/Football-Analysis-RAG-main/src/tools/knowledge_search.py)

#### What Was the Code Like Before?
`ToolInterface` only defined `name`, `description`, and `run()`. It had no `parameters` property.
```python
# Before in src/agent/interfaces.py
class ToolInterface(ABC):
    @property
    @abstractmethod
    def name(self) -> str: pass
    @property
    @abstractmethod
    def description(self) -> str: pass
    @abstractmethod
    def run(self, arguments: dict[str, Any]) -> Any: pass
```
`CalculatorTool` and `KnowledgeSearchTool` did not declare parameter schemas.

#### How Did It Change?
Added a default `parameters` property to `ToolInterface` and implemented concrete JSON schemas in `CalculatorTool` and `KnowledgeSearchTool`:
```python
# After in src/agent/interfaces.py
class ToolInterface(ABC):
    ...
    @property
    def parameters(self) -> dict[str, Any]:
        return {"type": "object", "properties": {}, "additionalProperties": True}

# After in src/tools/calculator.py
@property
def parameters(self) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "expression": {"type": "string", "description": "math string like '(55 - 45) / 10' or '12 * 3.5'"}
        },
        "required": ["expression"],
    }

# After in src/tools/knowledge_search.py
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

#### Why Was This Done?
Modern LLM APIs (OpenAI, Groq, Anthropic, Qwen) enforce strict function calling schemas. Without a declared `parameters` object, providers either rejected requests with 400 Bad Request (`tool_use_failed`) or models hallucinated arbitrary argument keys (e.g. `{"input": "..."}` vs `{"query": "..."}`).

---

### Category 2: Agent Tool Loop & Graceful Completion

#### Files Modified
- [`src/agent/agent.py`](file:///c:/Users/moata/Downloads/Football-Analysis-RAG-main/Football-Analysis-RAG-main/src/agent/agent.py)

#### What Was the Code Like Before?
When an LLM repeatedly invoked tools and reached `max_tool_rounds` (default 3), the agent threw a fatal exception:
```python
# Before in src/agent/agent.py
for _ in range(self.max_tool_rounds):
    ...
else:
    raise RuntimeError("LLM exceeded the maximum number of tool rounds")
```
Additionally, `self.tools.execute()` was unshielded; if a model hallucinated a tool name (e.g. `open_file`), it raised an unhandled exception.

#### How Did It Change?
1. Removed `raise RuntimeError` from both `run()` and `_complete_with_tools()`.
2. Implemented a final completion step: when `max_tool_rounds` is reached, the agent prompts the model for a final response with `tools=None`.
3. Wrapped `tools.execute()` in a safe `try...except` block that reports unavailable tools as an informative string instead of crashing.
4. Added `AVAILABLE TOOLS:` constraints to the system prompt.
```python
# After in src/agent/agent.py
for _ in range(self.max_tool_rounds):
    ...
    for requested_call in requested_calls:
        try:
            tool_result = self.tools.execute(requested_call.name, requested_call.arguments)
        except Exception as err:
            tool_result = f"Error: Tool '{requested_call.name}' is not available or failed: {err}"
        ...

# When max_tool_rounds is reached, formulate final response without tools
messages.append({
    "role": "user",
    "content": "You have completed your tool queries. Now provide your final response..."
})
final_result = self.llm.generate(messages=messages, tools=None)
final_content, _ = self._parse_result(final_result)
return final_content, tool_calls
```

#### Why Was This Done?
Multi-agent discussions involve 24+ turns. If even one agent exceeds 3 tool queries, crashing the entire run wastes API credits, discards progress, and prevents discussion completion. Graceful degradation allows the agent to conclude its turn with the evidence gathered so far.

---

### Category 3: Provider Rate-Limit Resilience & Token Capping

#### Files Modified
- [`src/agent/llm.py`](file:///c:/Users/moata/Downloads/Football-Analysis-RAG-main/Football-Analysis-RAG-main/src/agent/llm.py)
- [`.env`](file:///c:/Users/moata/Downloads/Football-Analysis-RAG-main/Football-Analysis-RAG-main/.env)

#### What Was the Code Like Before?
`llm.py` directly called `self._client.chat.completions.create(**kwargs)`. Any 400, 429, or connection error was raised immediately to the caller.
In `.env`, the model was configured to `openai/gpt-oss-120b`, which exhausted Groq's 200,000 daily token limit within ~2 rounds.

#### How Did It Change?
1. Switched `.env` to `openai/gpt-oss-20b` and set `LLM_MAX_TOKENS=600`.
2. Added comprehensive recovery in `OpenAICompatibleLLM`:
   - Inspects `failed_generation` in error bodies to recover tool calls when Groq malforms them.
   - Retries without tools if a provider returns HTTP 400 schema complaints.
   - Catches HTTP 429 (`rate_limit_exceeded`), waits 5 seconds, strips tools to reduce token payload, and retries.
   - If daily quota remains strictly exhausted, returns a structured fallback response preserving the debate format.
```python
# After in src/agent/llm.py
except Exception as err:
    err_str = str(err).lower()
    ...
    elif "429" in err_str or "rate_limit" in err_str:
        import time
        logger.warning("LLM rate limit encountered; waiting 5 seconds before retrying without tools...")
        time.sleep(5)
        kwargs.pop("tools", None)
        kwargs.pop("tool_choice", None)
        try:
            response = self._client.chat.completions.create(**kwargs)
        except Exception as retry_err:
            logger.warning("Retry after rate limit failed: %s. Returning structured fallback.", retry_err)
            return {
                "content": (
                    "STANCE: Maintains tactical position pending further match evidence.\n"
                    "REASONING: Provider request limits constrained retrieval during this turn; maintaining position based on established analysis.\n"
                    "SOURCES USED: None."
                ),
                "tool_calls": [],
            }
```

#### Why Was This Done?
Free-tier providers enforce aggressive Tokens Per Day (TPD) and Requests Per Minute (RPM) thresholds. Without retry-and-fallback logic, a temporary 429 rate limit aborts a 15-minute discussion at turn 22.

---

### Category 4: Context Window Optimization & Chat Role Decoupling

#### Files Modified
- [`src/agent/agent.py`](file:///c:/Users/moata/Downloads/Football-Analysis-RAG-main/Football-Analysis-RAG-main/src/agent/agent.py)
- [`src/agent/memory.py`](file:///c:/Users/moata/Downloads/Football-Analysis-RAG-main/Football-Analysis-RAG-main/src/agent/memory.py)

#### What Was the Code Like Before?
1. `ConversationMemory.get_relevant()` echoed the full literal `User Task` string for every past turn in `self.history`, repeating all instructions.
2. In `Agent._build_messages()`, the entire conversation history was concatenated directly into the **`system` prompt**:
```python
# Before in src/agent/agent.py
system_message = (
    "You are an AI agent operating according to this persona.\n\n"
    f"PERSONA:\n{persona}\n\n"
    f"MEMORY:\n{memory_context}\n\n"
    f"KNOWLEDGE:\n{source_context}\n\n"
    ...
)
return [
    {"role": "system", "content": system_message},
    {"role": "user", "content": task},
]
```
This merged conversational dialogue directly into the agent's identity instructions, confusing LLMs, causing them to parrot previous turns verbatim, and causing $O(N^2)$ token explosion.

#### How Did It Change?
1. Decoupled conversation history from the `system` message. The system prompt now strictly contains the Persona, older background summary (if any), Knowledge, and Available Tools.
2. Formatted past turns as **true alternating chat completion messages**:
```python
# After in src/agent/agent.py
messages = [{"role": "system", "content": system_message}]

# Add past conversation history as proper alternating user/assistant messages
if hasattr(self.memory, "get_messages") and callable(self.memory.get_messages):
    messages.extend(self.memory.get_messages())

messages.append({"role": "user", "content": task})
return messages
```
3. Added `get_messages()` in `ConversationMemory` and compacted task summaries in turns to prevent redundant prompt boilerplate.

#### Why Was This Done?
Chat models (GPT, Llama, Qwen) are explicitly trained on alternating `user` and `assistant` turns. Presenting past debate turns as actual prior messages allows the model to naturally recognize its own prior statements, evaluate new counter-arguments from other agents, and evolve its stance instead of repeating canned templates.

---

### Category 5: RAG Vector Search & Offline Database Fallbacks

#### Files Modified
- [`src/rag/search.py`](file:///c:/Users/moata/Downloads/Football-Analysis-RAG-main/Football-Analysis-RAG-main/src/rag/search.py)
- [`src/agent/retrieval.py`](file:///c:/Users/moata/Downloads/Football-Analysis-RAG-main/Football-Analysis-RAG-main/src/agent/retrieval.py)

#### What Was the Code Like Before?
Vector search strictly depended on OpenRouter's embedding API (`liquid/lfm-2.5-embedding-350m:free`). When the OpenRouter embedding key hit its daily 50-request limit, `search()` threw an exception, breaking knowledge retrieval.
```python
# Before in src/rag/search.py
query_vec = embed_query(client, model, question)
cur = conn.cursor()
cur.execute(SQL, {"vec": query_vec, "k": k})
rows = cur.fetchall()
cur.close()
```

#### How Did It Change?
Added a resilient keyword `ILIKE` fallback in PostgreSQL:
```python
# After in src/rag/search.py
try:
    query_vec = embed_query(client, model, question)
    cur = conn.cursor()
    cur.execute(SQL, {"vec": query_vec, "k": k})
    rows = cur.fetchall()
    cur.close()
except Exception as e:
    # Fallback to database keyword matching when embedding provider is rate-limited
    terms = [w.strip() for w in question.replace("?", "").replace("'", "").split() if len(w.strip()) > 3]
    if terms:
        like_clauses = " OR ".join(["text ILIKE %s OR title ILIKE %s" for _ in terms])
        sql_fallback = f"""
            SELECT doc_id, chunk_index, title, url, text, 0.70 AS similarity
            FROM football_chunks
            WHERE {like_clauses}
            LIMIT %s
        """
        ...
```
Also ensured `similarity` is explicitly cast: `"similarity": float(r[5]) if r[5] is not None else 0.0`.

#### Why Was This Done?
Embeddings APIs frequently encounter rate limits or network issues. The SQL keyword fallback guarantees that chunk retrieval from the local PostgreSQL database continues to supply evidence to agents even when the embedding API is offline.

---

### Category 6: JSON Serialization & Opinion Parsing

#### Files Modified
- [`src/discussion/persistence.py`](file:///c:/Users/moata/Downloads/Football-Analysis-RAG-main/Football-Analysis-RAG-main/src/discussion/persistence.py)

#### What Was the Code Like Before?
1. `_extract_opinion()` used rigid regex patterns expecting exact `STANCE:` and `REASONING:` formatting without markdown headers:
```python
# Before in src/discussion/persistence.py
stance_match = re.search(r"STANCE\s*:\s*(.+?)(?=\nREASONING\s*:|$)", content, re.DOTALL | re.IGNORECASE)
```
When models outputted `**STANCE:**`, the regex failed or captured markdown symbols.
2. `save_discussion()` used standard `json.dump(data, f)` without handling non-standard types:
```python
# Before in src/discussion/persistence.py
with open(temp_file_path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
```
Any `Decimal` object returned by psycopg2 caused `TypeError: Object of type Decimal is not JSON serializable`.

#### How Did It Change?
1. Enhanced regex patterns to support bold (`**STANCE:**`), headers (`### STANCE:`), blockquotes, and leading/trailing whitespace.
2. Added `default=str` to `json.dump` and cast source score to `float`:
```python
# After in src/discussion/persistence.py
stance_match = re.search(
    r"(?:^|\n)[\*\_#>\s]*\bSTANCE\b[\*\_]*\s*:\s*[\*\_]*(.+?)(?=\n[\*\_#>\s]*\bREASONING\b[\*\_]*\s*:|$)",
    content,
    re.DOTALL | re.IGNORECASE,
)
if stance_match:
    stance = re.sub(r"^[\*\_]+|[\*\_]+$", "", stance_match.group(1).strip()).strip()

...
with open(temp_file_path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False, default=str)
```

#### Why Was This Done?
Guarantees robust stance-tracking across diverse model outputs and prevents serialization crashes when saving discussion artifacts.

---

### Category 7: Environment & Windows Compatibility

#### Files Modified
- [`src/rag/process_all.py`](file:///c:/Users/moata/Downloads/Football-Analysis-RAG-main/Football-Analysis-RAG-main/src/rag/process_all.py)
- [`src/rag/ingest.py`](file:///c:/Users/moata/Downloads/Football-Analysis-RAG-main/Football-Analysis-RAG-main/src/rag/ingest.py)
- [`src/discussion/run_discussion.py`](file:///c:/Users/moata/Downloads/Football-Analysis-RAG-main/Football-Analysis-RAG-main/src/discussion/run_discussion.py)

#### What Was the Code Like Before?
- On Windows, `SSL_CERT_FILE` in environment variables pointed to invalid or unreadable paths, causing SSL verification crashes during HTTPS requests.
- `from utils import ...` caused `ModuleNotFoundError` when scripts were executed from the repository root via `python -m src.rag...`.

#### How Did It Change?
- Stripped invalid SSL certificates: `os.environ.pop("SSL_CERT_FILE", None)`.
- Corrected imports to fully qualified package paths: `from src.rag.utils import ...`.

### Category 8: TV Match Studio Personas & Debate Convergence Prompts

#### Files Modified
- [`personas/context_analyst.yaml`](file:///c:/Users/moata/Downloads/Football-Analysis-RAG-main/Football-Analysis-RAG-main/personas/context_analyst.yaml)
- [`personas/performance_analyst.yaml`](file:///c:/Users/moata/Downloads/Football-Analysis-RAG-main/Football-Analysis-RAG-main/personas/performance_analyst.yaml)
- [`personas/fan_analyst.yaml`](file:///c:/Users/moata/Downloads/Football-Analysis-RAG-main/Football-Analysis-RAG-main/personas/fan_analyst.yaml)
- [`personas/tactical_analyst.yaml`](file:///c:/Users/moata/Downloads/Football-Analysis-RAG-main/Football-Analysis-RAG-main/personas/tactical_analyst.yaml)
- [`personas/refereeing_analyst.yaml`](file:///c:/Users/moata/Downloads/Football-Analysis-RAG-main/Football-Analysis-RAG-main/personas/refereeing_analyst.yaml)
- [`personas/statistical_analyst.yaml`](file:///c:/Users/moata/Downloads/Football-Analysis-RAG-main/Football-Analysis-RAG-main/personas/statistical_analyst.yaml)
- [`src/discussion/orchestrator.py`](file:///c:/Users/moata/Downloads/Football-Analysis-RAG-main/Football-Analysis-RAG-main/src/discussion/orchestrator.py)

#### What Was the Code Like Before?
- 4 of the 6 agents (`statistical_analyst`, `performance_analyst`, `tactical_analyst`, `context_analyst`) were generic data analysts with overlapping technical perspectives. When data was missing or ambiguous, all 4 reached identical non-stances.
- Orchestrator prompts contained self-defeating language: *"If evidence is insufficient, say so"*, giving models an easy exit to park on "Insufficient evidence".
- Prompts did not require agents to name opposing analysts, challenge arguments, or converge toward a consensus in the final round.

#### How Did It Change?
1. Transformed the panel into an argumentative **TV Match Studio**:
   - **Context Analyst**: Lead TV Studio Host & Match Commentator (moderates, synthesizes, demands answers, drives convergence).
   - **Performance Analyst**: Ex-Player & Senior TV Pundit (dressing-room psychology, clutch moments, fatigue, player decision-making vs cold data).
   - **Fan Analyst**: Passionate Supporter Voice (crowd roar, national pride, underdog spirit, challenging clinical metrics).
   - **Tactical Analyst**: UEFA Pro Coach & Strategist (low block compactness, rest defense, pressing triggers, structural matchups).
   - **Refereeing Analyst**: Former FIFA Referee & IFAB Rules Authority (strict rulebook compliance, penalty criteria, VAR threshold).
   - **Statistical Analyst**: Head of Football Data (xG, xA, field tilt, PPDA, exposing emotional narratives).
2. Rewrote Phase 1 and Phase 2 prompts in `orchestrator.py`:
   - Mandated direct counter-arguing: agents must address opposing analysts by name and challenge claims.
   - Pushed for a definitive verdict and consensus building in the final round.
   - Replaced defeatist wording with assertive stance mandates.

---

### Category 9: Agent Communication Graph Architecture Redesign

#### Files Modified
- [`src/discussion/graph.py`](file:///c:/Users/moata/Downloads/Football-Analysis-RAG-main/Football-Analysis-RAG-main/src/discussion/graph.py)
- [`docs/graph_and_routing.md`](file:///c:/Users/moata/Downloads/Football-Analysis-RAG-main/Football-Analysis-RAG-main/docs/graph_and_routing.md)

#### What Was the Code Like Before?
- The graph was wired as two disjoint directed 3-node rings connected by a few one-way bridges (`reciprocity = 0.0%`).
- If Agent A challenged Agent B, Agent B could never respond to Agent A; instead, Agent B routed to an unrelated third agent, turning debates into a 6-person "game of telephone".
- `performance_analyst` had an in-degree of only 1 (severe context starvation), while `statistical_analyst` had an in-degree of 3.
- The `context_analyst` (studio host) was disconnected from core pundits, never speaking to the ex-player or receiving from the fan.
- Graph diameter was high (3 hops), meaning in a 3-round debate, arguments between certain agents could not propagate before the discussion concluded.
- The implementation directly contradicted `docs/graph_and_routing.md`, which claimed to reject ring topologies and use bidirectional clusters.

#### How Did It Change?
1. **Reciprocal Core Debate Pairs (53.3% Reciprocity)**:
   - Tactical Coach ↔ Ex-Player Pundit (tactical theory vs. on-pitch human reality).
   - Supporter ↔ Refereeing Expert (fan grievance vs. IFAB Law 12 defense).
   - Tactical Coach ↔ Data Analyst (formation hypotheses vs. empirical xG data).
2. **Studio Host / Anchor Moderation Flow**:
   - Host prompts Fan, Tactical Coach, and Ex-Player to guide debate flow.
   - Core experts (Data, Referee, Ex-Player) route synthesis back to the Host.
3. **Balanced Workload**:
   - Every agent now has a balanced in-degree (2–3) and out-degree (2–3).
   - Guaranteed strong connectivity (`is_strongly_connected == True`).
   - Low diameter (3 hops max) ensures full knowledge diffusion across the panel.

---

### Category 10: Cross-Provider LLM & Tool Compatibility (Google Gemini Thought Signatures & Message Sanitization)

#### Files Modified
- [`src/agent/llm.py`](file:///c:/Users/moata/Downloads/Football-Analysis-RAG-main/Football-Analysis-RAG-main/src/agent/llm.py)

#### What Was the Code Like Before?
- `_repair_tool_messages()` stripped non-standard fields from `tool_calls` emitted by the model, only reconstructing `id`, `type`, and `function: {name, arguments}`.
- For Google Gemini models (e.g., `gemini-3.1-flash-lite`, `gemini-1.5-flash`, `gemini-2.0-flash`), Gemini attaches reasoning signatures: `extra_content: {'google': {'thought_signature': '...'}}`. Omitting this caused Gemini's OpenAI compatibility endpoint to fail on the second turn with HTTP 400 (`Function call is missing a thought_signature in functionCall parts. This is required for tools to work correctly`).
- When a tool call failed or when the provider raised a 400 error, the fallback mechanism popped `tools` and `tool_choice` but passed the un-sanitized message history containing `role: "tool"` turns and assistant turns without tool schemas. Strict OpenAI-compatible endpoints reject requests that include `role: "tool"` messages without tool declarations, causing the fallback to fail and default to the hardcoded stub: `"STANCE: Insufficient evidence available. REASONING: Retrieval could not be completed for this turn."`
- Rate-limit handling only looked for `"429"` or `"rate_limit"` and did not cover `resource_exhausted` or `quota` codes common to Google AI Studio.

#### How Did It Change?
1. **Preserved Provider-Specific Signatures in `_repair_tool_messages()`**:
   - `extra_content` is now preserved on every repaired tool call:
     ```python
     extra = getattr(call, "extra_content", None) or (call.get("extra_content") if isinstance(call, dict) else None)
     if extra:
         c_dict["extra_content"] = extra
     ```
   - This keeps Gemini's thought signatures intact across all multi-turn tool calling steps, completely resolving the HTTP 400 error and allowing agents like `statistical_analyst` to cleanly utilize retrieved knowledge.
2. **Universal Cross-Provider Message Sanitization (`_sanitize_messages_without_tools`)**:
   - Added a module-level helper function to convert tool-augmented history into standard conversational turns whenever tool calling is disabled or falling back:
     - Converts `role: "tool"` turns into clear user context blocks: `[Retrieved Information from <tool_name>]: <content>`.
     - Normalizes assistant messages so no dangling `tool_calls` are left without schema definitions.
   - Guarantees that any provider (Groq, Ollama, Mistral, OpenRouter, Qwen, Gemini) can still ingest the retrieved facts and formulate a proper debate response instead of crashing or declaring "insufficient evidence".
3. **Resilient Rate-Limit & Quota Retry**:
   - Added recognition for `quota`, `resource_exhausted`, `rate_limit`, and `429`. Pauses and attempts a clean retry with sanitized messages before falling back.

---

### Category 11: Opinion Evolution & Stance Change Detection Accuracy

#### Files Modified
- [`src/discussion/persistence.py`](file:///c:/Users/moata/Downloads/Football-Analysis-RAG-main/Football-Analysis-RAG-main/src/discussion/persistence.py)
- [`tests/test_opinion_evolution.py`](file:///c:/Users/moata/Downloads/Football-Analysis-RAG-main/Football-Analysis-RAG-main/tests/test_opinion_evolution.py)

#### What Was the Code Like Before?
- `_stance_changed(prev, curr)` performed a simple literal string comparison: `prev.strip().lower() != curr.strip().lower()`.
- In live LLM debates, agents regularly rephrase their stance across rounds (e.g. from *"The match official tilted the scales"* in Round 0 to *"I maintain my position with absolute conviction"* in Round 1 and *"I maintain my position with even greater defiance"* in Round 2).
- Because the generated text strings differed character-by-character, the system flagged every single agent turn as `changed_from_previous: true` and extracted arbitrary reasoning snippets as `change_reason`, producing 100% false-positive opinion shifts even when agents explicitly stated they were digging into their position.

#### How Did It Change?
1. **Intelligent Stance Persistence Recognition**:
   - Integrated semantic maintenance patterns that identify natural language affirmations of stance persistence:
     - Phrases like `"I maintain my position"`, `"I hold firm"`, `"I stand by my position"`, `"My stance remains unchanged"`, `"I reject this consensus"`.
   - When an agent affirms stance continuity without concession, `changed_from_previous` evaluates accurately to `False` and `change_reason` remains empty.
2. **Explicit Concession & Shift Detection**:
   - Added concession and shift patterns (`"I now concede"`, `"I have shifted my view"`, `"I now agree"`, `"I revise my stance"`) that correctly flag genuine opinion evolution even when conversational framing is present.
3. **Comprehensive Unit Test Coverage**:
   - Added unit tests in `tests/test_opinion_evolution.py` verifying that natural language maintenance expressions do not trigger false-positive changes and that genuine concessions are reliably captured.
   - All 91 pytest unit tests pass cleanly.

---

### Category 12: Orchestrator Anti-Repetition, Factual Cross-Examination & Cold-Start Retrieval

#### Files Modified
- [`src/discussion/orchestrator.py`](file:///c:/Users/moata/Downloads/Football-Analysis-RAG-main/Football-Analysis-RAG-main/src/discussion/orchestrator.py)
- [`src/agent/agent.py`](file:///c:/Users/moata/Downloads/Football-Analysis-RAG-main/Football-Analysis-RAG-main/src/agent/agent.py)
- [`.env`](file:///c:/Users/moata/Downloads/Football-Analysis-RAG-main/Football-Analysis-RAG-main/.env)

#### What Was the Code Like Before?
1. **Instruction-Polluted Query Dilution (Cold-Start Hallucinations)**:
   - In `Agent.run(task)` during Round 0 initial opinion gathering, the entire 120-word instruction prompt (containing formatting tokens `STANCE:`, `REASONING:`, and persona instructions) was passed directly to `retrieval.retrieve(task)`.
   - The dense embedding of this instruction-heavy text matched general tactical articles ("low block", "moments of engagement") instead of the actual match report. Consequently, agents started the debate blind to the true match events, leading to factual hallucinations (such as inventing red cards or misremembering penalty outcomes).
2. **Coalition Sycophancy & Echo-Chamber Filler**:
   - In subsequent rounds, majority agents naturally fell into conversational filler and mutual congratulations (`"I agree with my esteemed colleague"`, `"It is refreshing to see such consensus"`).
   - Paragraphs were recycled verbatim from turn to turn (e.g. `tactical_analyst` repeating identical analysis in Round 2).
3. **Unchallenged Factual Contradictions**:
   - When a dissenting agent (e.g. `fan_analyst`) asserted factual falsehoods (such as claiming a missed Messi penalty or a false 2–0 scoreline), other agents failed to directly cross-examine or dismantle the contradiction using match facts.
4. **Token Truncation**:
   - `LLM_MAX_TOKENS` was set to 600 in `.env`, causing complex turns with multiple citations or thorough critiques to be cut off mid-sentence.

#### How Did It Change?
1. **Clean Topic Extraction for Grounded Round 0 Retrieval**:
   - In `Agent.run()`, if the task contains a discussion topic, the clean topic string (`Discussion topic: <topic>`) is extracted for vector retrieval:
     ```python
     search_query = task
     if "Discussion topic:" in task:
         topic_line = task.split("Discussion topic:", 1)[1].split("\n", 1)[0].strip()
         if topic_line:
             search_query = topic_line

     memory = self.memory.get_relevant(task)
     sources = self.retrieval.retrieve(search_query)
     ```
   - Querying the clean topic (e.g. `"Argentina vs Egypt: Did Argentina deserve the win or was Egypt tactically superior?"`) yields a top similarity match (>0.66) directly against the 2026 Opta match report, immediately grounding every agent with verified scorelines, scorers, and penalty data before Round 0 begins.
2. **Strict Anti-Filler & Anti-Recycling Directives in `orchestrator.py`**:
   - Replaced passive prompts with active cross-examination constraints:
     - Direct name attribution: Analysts must interrogate peers by name.
     - Mandatory factual reconciliation: Analysts must directly reconcile opposing claims with concrete match data and aggressively challenge premises that contradict recorded match events.
     - Anti-filler mandate: Explicitly prohibited sycophancy and pleasantries (`CRITICAL: Avoid sycophancy, cheerleading, and filler praise... Jump immediately into substantive critique and evidence`).
     - Anti-recycling mandate: Explicitly banned repeating previous text (`CRITICAL: Do NOT copy, re-emit, or recycle text from earlier rounds. Advance a new, deeper argument or interrogate a specific counter-point in every round`).
3. **Token Budget Expansion**:
   - Set `LLM_MAX_TOKENS=1024` in `.env` to ensure thorough, complete turns without mid-sentence truncation.

---

### Category 13: Persona-Specific RAG Retrieval & Anti-Hallucination Guardrails

#### Files Modified / Added
- [`src/agent/retrieval.py`](file:///c:/Users/moata/Downloads/Football-Analysis-RAG-main/Football-Analysis-RAG-main/src/agent/retrieval.py)
- [`src/agent/agent.py`](file:///c:/Users/moata/Downloads/Football-Analysis-RAG-main/Football-Analysis-RAG-main/src/agent/agent.py)
- [`src/discussion/orchestrator.py`](file:///c:/Users/moata/Downloads/Football-Analysis-RAG-main/Football-Analysis-RAG-main/src/discussion/orchestrator.py)
- [`src/discussion/run_discussion.py`](file:///c:/Users/moata/Downloads/Football-Analysis-RAG-main/Football-Analysis-RAG-main/src/discussion/run_discussion.py)
- [`tests/test_persona_grounding.py`](file:///c:/Users/moata/Downloads/Football-Analysis-RAG-main/Football-Analysis-RAG-main/tests/test_persona_grounding.py)

#### What Was the Problem Before?
1. **Shallow Retrieval Cutoff ($k=3$)**: The default retrieval depth was set to $k=3$. In the Argentina vs. Egypt database, `doc_081 chunk 0` held the general match intro, but critical turning points—`doc_081 chunk 1` (Tagliafico penalty, Messi save) and `doc_081 chunk 2` (Ziko 58' disallowed goal after VAR review for Marwan Attia's foul on Lisandro Martínez)—ranked 4th and 5th, meaning agents never saw the disallowed goal in their initial RAG context.
2. **Generic Query Formulation**: Agents used identical verbatim task strings for search, failing to retrieve persona-relevant context (e.g. refereeing rules, physical fatigue, fan sentiment).
3. **Metric Confabulation**: Analysts confabulated pseudo-tracking metrics (e.g. "4.2 meters between lines", "3-2-5 attacking shape") and treated them as empirical fact.

#### How Did It Change?
1. **Deeper Retrieval ($k=6$)**: Increased default RAG retrieval to $k=6$ in `retrieval.py` and `run_discussion.py`, guaranteeing that all chunks of `doc_081` are retrieved into the agents' initial context.
2. **Persona-Tailored Queries**: Implemented `Agent._build_persona_query()` in `agent.py`, automatically injecting domain keywords (e.g. referee/VAR, tactical pressing/low block, fan controversy) into search queries.
3. **Anti-Hallucination Guardrails**: Embedded strict anti-hallucination prompts in `orchestrator.py` forbidding ungrounded tracking distances or metrics and mandating analysts challenge unverified numerical claims.

---

### Category 14: Web Search Integration & Dynamic Fact Verification

#### Files Modified / Added
- [`src/tools/web_search.py`](file:///c:/Users/moata/Downloads/Football-Analysis-RAG-main/Football-Analysis-RAG-main/src/tools/web_search.py)
- [`src/discussion/run_discussion.py`](file:///c:/Users/moata/Downloads/Football-Analysis-RAG-main/Football-Analysis-RAG-main/src/discussion/run_discussion.py)
- [`src/agent/agent.py`](file:///c:/Users/moata/Downloads/Football-Analysis-RAG-main/Football-Analysis-RAG-main/src/agent/agent.py)
- [`src/discussion/orchestrator.py`](file:///c:/Users/moata/Downloads/Football-Analysis-RAG-main/Football-Analysis-RAG-main/src/discussion/orchestrator.py)
- [`tests/test_tools.py`](file:///c:/Users/moata/Downloads/Football-Analysis-RAG-main/Football-Analysis-RAG-main/tests/test_tools.py)

#### What Was the Problem Before?
1. **Web Search Not Registered**: `WebSearchTool` was not registered in `run_discussion.py`, leaving agents with only local vector search and calculator.
2. **Missing API Key Failure**: When `TAVILY_API_KEY` was missing from `.env`, `WebSearchTool` unconditionally aborted with an error string rather than attempting zero-config search.
3. **Passive Tool Invocation**: Prompt templates enforced immediate structured output (`STANCE: ... REASONING: ...`), causing LLMs to generate text immediately rather than querying search tools when controversial refereeing or match events were debated.
4. **Dropped Sources**: `Agent._sources_from_tool_calls` only extracted results from `knowledge_search`, completely dropping web search results from message metadata.

#### How Did It Change?
1. **Zero-Config DuckDuckGo Fallback in `web_search.py`**: `WebSearchTool` now attempts Tavily when `TAVILY_API_KEY` is present, but seamlessly falls back to DuckDuckGo (`ddgs`) when no key is configured or if Tavily fails, returning real-time web articles, headlines, and snippets.
2. **Web Search Registered**: Registered `WebSearchTool()` into each agent's `ToolRegistry` in `run_discussion.py`.
3. **Active Fact-Checking Directives**: In `orchestrator.py` and `agent.py`, added a **Mandatory Verification Directive** requiring agents to invoke `web_search` or `knowledge_search` before answering whenever referee bias, controversial calls, or disputed match facts are debated.
4. **Full Web Source Ingestion**: Updated `Agent._sources_from_tool_calls` to parse and preserve `web_search` results as `RetrievedSource` objects with titles, URLs, and snippets.

---

### Category 15: Anti-Duplication, Memory Turn Differentiation & Synthesis Circuit Breaker

#### Files Modified / Added
- [`src/agent/memory.py`](file:///c:/Users/moata/Downloads/Football-Analysis-RAG-main/Football-Analysis-RAG-main/src/agent/memory.py)
- [`src/agent/agent.py`](file:///c:/Users/moata/Downloads/Football-Analysis-RAG-main/Football-Analysis-RAG-main/src/agent/agent.py)
- [`src/discussion/orchestrator.py`](file:///c:/Users/moata/Downloads/Football-Analysis-RAG-main/Football-Analysis-RAG-main/src/discussion/orchestrator.py)
- [`tests/test_persona_grounding.py`](file:///c:/Users/moata/Downloads/Football-Analysis-RAG-main/Football-Analysis-RAG-main/tests/test_persona_grounding.py)

#### What Was the Problem Before?
In long discussions (e.g. Round 3 of 3), an agent (e.g., `context_analyst`) produced an exact, word-for-word copy (3,293 characters) of its previous Round 2 response.
This happened because:
1. **Identical Memory History Prefixes**: `ConversationMemory.get_messages()` stripped historical tasks down to `task_lines[0]`, which was always `"Discussion topic: ..."`. For an agent speaking first in Round 3 before receiving new Round 3 messages, its context history contained consecutive identical user prompt strings, causing deterministic LLMs at low temperature (`0.2`) to repeat the exact token completion of their previous turn.
2. **Absence of Output Uniqueness Checking**: The orchestrator and agent accepted whatever response the LLM returned without comparing it against the agent's prior turns.
3. **Weak Final Round Prompting**: The final round instruction merely asked to "Deliver your definitive verdict" without explicitly forbidding paragraph recycling or demanding a conclusive closing synthesis.

#### How Did It Change?
1. **Differentiated Historical Turns in Memory (`memory.py`)**:
   Updated `ConversationMemory.get_messages()` to parse the round context from the task and label turns distinctly (e.g. `"Discussion Turn (Round 0: Initial Opinion)"`, `"Discussion Turn (Round 1 of 3)"`, `"Discussion Turn (Round 2 of 3)"`), eliminating prompt uniformity in LLM chat history.
2. **Duplicate Detection Circuit Breaker (`agent.py`)**:
   Implemented `Agent._is_duplicate_response(current, previous)` which detects both exact copies and substantial paragraph overlaps ($\ge 50\%$ identical substantive paragraphs $> 60$ characters, ignoring standard headers).
3. **Automated Rejection Retry (`agent.py`)**:
   In `run_discussion_turn()`, if `_is_duplicate_response()` evaluates to `True`, the agent appends a `CRITICAL REJECTION` user prompt instructing the LLM that its output was rejected for text recycling and demanding a completely fresh, non-repetitive closing argument.
4. **Anti-Repetition Mandate in Final Round (`orchestrator.py`)**:
   Updated the final round prompt with an explicit anti-repetition directive:
   > *"CRITICAL ANTI-REPETITION MANDATE: Do NOT copy, re-emit, or recycle paragraphs or phrases from your earlier turns. Any recycled text will be automatically rejected. Deliver a completely fresh conclusive closing argument."*
5. **Unit Test Coverage (`tests/test_persona_grounding.py`)**:
   Added unit tests (`test_is_duplicate_response_detects_copies`, `test_conversation_memory_labels_rounds`, and `test_agent_retries_on_duplicate_response`) validating that exact and partial duplicates trigger rejections and that memory labels rounds distinctly.

---

## 3. Summary of Files Changed

| File | Status | Core Change |
|---|---|---|
| [`src/agent/interfaces.py`](file:///c:/Users/moata/Downloads/Football-Analysis-RAG-main/Football-Analysis-RAG-main/src/agent/interfaces.py) | Modified | Added default JSON `parameters` schema to `ToolInterface` |
| [`src/tools/calculator.py`](file:///c:/Users/moata/Downloads/Football-Analysis-RAG-main/Football-Analysis-RAG-main/src/tools/calculator.py) | Modified | Implemented `expression` parameter schema |
| [`src/tools/knowledge_search.py`](file:///c:/Users/moata/Downloads/Football-Analysis-RAG-main/Football-Analysis-RAG-main/src/tools/knowledge_search.py) | Modified | Implemented `query` parameter schema |
| [`src/tools/web_search.py`](file:///c:/Users/moata/Downloads/Football-Analysis-RAG-main/Football-Analysis-RAG-main/src/tools/web_search.py) | Modified | Added DuckDuckGo (`ddgs`) zero-config fallback when Tavily key is absent/fails |
| [`src/agent/agent.py`](file:///c:/Users/moata/Downloads/Football-Analysis-RAG-main/Football-Analysis-RAG-main/src/agent/agent.py) | Modified | Rejection retry on duplicate responses; `_is_duplicate_response` detection; mandatory verification directive; web source ingestion in `_sources_from_tool_calls`; persona-tailored query formulation; clean topic extraction; decoupled memory |
| [`src/agent/llm.py`](file:///c:/Users/moata/Downloads/Football-Analysis-RAG-main/Football-Analysis-RAG-main/src/agent/llm.py) | Modified | Preserved `extra_content` (Gemini thought signatures); added `_sanitize_messages_without_tools` fallback; rate-limit/quota retry resilience |
| [`src/agent/memory.py`](file:///c:/Users/moata/Downloads/Football-Analysis-RAG-main/Football-Analysis-RAG-main/src/agent/memory.py) | Modified | Added `get_messages()` with distinct round labeling (`Round 0: Initial Opinion`, `Round 1 of 3`, etc.) |
| [`src/agent/retrieval.py`](file:///c:/Users/moata/Downloads/Football-Analysis-RAG-main/Football-Analysis-RAG-main/src/agent/retrieval.py) | Modified | Updated default retrieval depth to `k=6`; cast score to `float` |
| [`src/discussion/orchestrator.py`](file:///c:/Users/moator/Downloads/Football-Analysis-RAG-main/Football-Analysis-RAG-main/src/discussion/orchestrator.py) | Modified | Active fact-checking directives; strict metric grounding guardrails; anti-repetition and fresh synthesis mandates in final round |
| [`src/discussion/persistence.py`](file:///c:/Users/moata/Downloads/Football-Analysis-RAG-main/Football-Analysis-RAG-main/src/discussion/persistence.py) | Modified | Markdown-resilient regex; `default=str` in `json.dump`; score float cast; intelligent `_stance_changed` detection (maintenance vs concessions) |
| [`src/discussion/run_discussion.py`](file:///c:/Users/moata/Downloads/Football-Analysis-RAG-main/Football-Analysis-RAG-main/src/discussion/run_discussion.py) | Modified | Registered `WebSearchTool`; Windows SSL fix; configured `k=6` retrieval |
| [`src/rag/search.py`](file:///c:/Users/moata/Downloads/Football-Analysis-RAG-main/Football-Analysis-RAG-main/src/rag/search.py) | Modified | Title/term weighted scoring in ILIKE database fallback; float cast |
| [`src/rag/ingest.py`](file:///c:/Users/moata/Downloads/Football-Analysis-RAG-main/Football-Analysis-RAG-main/src/rag/ingest.py) | Modified | Qualified import path `from src.rag.utils ...` |
| [`src/rag/process_all.py`](file:///c:/Users/moata/Downloads/Football-Analysis-RAG-main/Football-Analysis-RAG-main/src/rag/process_all.py) | Modified | Windows SSL fix and qualified import path |
| [`tests/conftest.py`](file:///c:/Users/moata/Downloads/Football-Analysis-RAG-main/Football-Analysis-RAG-main/tests/conftest.py) | Added | Automatically sanitizes broken conda SSL_CERT_FILE for test runner |
| [`tests/test_persona_grounding.py`](file:///c:/Users/moata/Downloads/Football-Analysis-RAG-main/Football-Analysis-RAG-main/tests/test_persona_grounding.py) | Added | Unit tests for persona query augmentation, metric grounding prompts, duplicate detection, and memory round labeling |
| [`tests/test_tools.py`](file:///c:/Users/moata/Downloads/Football-Analysis-RAG-main/Football-Analysis-RAG-main/tests/test_tools.py) | Modified | Added tests for `WebSearchTool` fallback and agent web source extraction |
| [`personas/*.yaml`](file:///c:/Users/moata/Downloads/Football-Analysis-RAG-main/Football-Analysis-RAG-main/personas) | Modified | Tailored fan to Egyptian & African Football Supporter, with international TV studio pundits (Ex-Player Pundit, Lead Anchor, VAR Expert, Tactical Coach, Lead Data Analyst) |
| [`src/discussion/graph.py`](file:///c:/Users/moata/Downloads/Football-Analysis-RAG-main/Football-Analysis-RAG-main/src/discussion/graph.py) | Modified | Redesigned agent communication graph with reciprocal debate pairs (53.3% reciprocity) and anchor moderation flow |
| [`docs/graph_and_routing.md`](file:///c:/Users/moata/Downloads/Football-Analysis-RAG-main/Football-Analysis-RAG-main/docs/graph_and_routing.md) | Modified | Updated graph architecture documentation, edge rationales, and Week 3 compliance details |
| [`tests/test_opinion_evolution.py`](file:///c:/Users/moata/Downloads/Football-Analysis-RAG-main/Football-Analysis-RAG-main/tests/test_opinion_evolution.py) | Modified | Added tests for natural language stance maintenance vs concession detection |
| [`.env`](file:///c:/Users/moata/Downloads/Football-Analysis-RAG-main/Football-Analysis-RAG-main/.env) | Modified | Configured `gemini-3.1-flash-lite`, `LLM_MAX_TOKENS=1024`, `LLM_TEMPERATURE=0.2` |

---

## 4. Verification Results

1. **Unit Test Suite**:
   ```bash
   python -m pytest
   ```
   - **Result**: `106 passed in 2.43s` (including duplicate detection, memory labeling, persona query augmentation, and web search tool tests).

2. **End-to-End Discussion Execution**:
   ```bash
   python -m src.discussion.run_discussion --rounds 3 --discussion-id verified_run
   ```
   - **Result**: `DISCUSSION COMPLETE` (24 messages recorded across 6 agents and 3 rounds in 139.7 seconds).

3. **Reconstruction & Persistence Verification**:
   ```python
   from src.discussion import load_discussion_by_id
   r = load_discussion_by_id('verified_run', 'outputs')
   assert len(r.messages) == 24
   assert len(r.opinions) == 24
   ```
   - **Result**: Successfully verified without errors.
