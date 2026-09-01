# Prompt Design

This document covers the prompt-engineering piece of Week 2: how persona,
memory, retrieved knowledge, and tool results reach the LLM, and why the
prompts are structured the way they are.

Code lives in `src/agent/prompts/`:
- `templates.py` — shared building blocks (persona/memory/sources formatting)
- `opinion_prompt.py` — the Initial Opinion Generation prompt + a lightweight parser

## 1. How persona information reaches the model

`format_persona_block()` turns the `Persona` object into direct
**instructions**, not a labeled list of fields. Early testing showed that
dumping fields ("Name: X, Stance: Y") produces a model that *mentions*
those traits in passing but still answers in a generic, balanced voice.
Phrasing the same information as imperatives ("you must always...", "your
priorities... should visibly shape your conclusion") produces noticeably
more distinct behavior between personas on the same topic.

## 2. How retrieved context reaches the model

`format_sources_block()` numbers every retrieved chunk (`[Source 1]`,
`[Source 2]`, ...) and includes its similarity score and origin URL. The
model is instructed to cite sources by number when it relies on them. This
was chosen over free-text attribution ("according to an article...")
because numbered citations can be mechanically checked afterward — a
reviewer (or a test) can confirm a claim actually traces back to a
retrieved chunk instead of trusting the model's paraphrase of "where it
got that."

If retrieval returns nothing, the model is told explicitly to say so
rather than filling the gap with invented information.

## 3. How memory is incorporated

`format_memory_block()` puts prior-interaction context in its own labeled
section, separate from retrieved knowledge, with an explicit note that it
is "not evidence for your opinion." This separation matters because
`ConversationMemory` can contain the agent's *own* earlier, possibly
speculative statements — without the separation, the model could treat a
previous guess as a confirmed fact in a later turn.

## 4. How tool results are incorporated

`format_tool_result()` prefixes every tool result with the tool's name
(`[calculator result] ...` / `[knowledge_search result] ...`) before it's
appended to the conversation as a `role: tool` message. The prefix lets
the model distinguish an exact computation (calculator) from a fuzzy
semantic match (knowledge_search), which affects how confidently it should
state the result.

## 5. Initial Opinion Generation prompt

Built by `build_opinion_prompt()`. Instead of asking for free-form
commentary, the model is asked to answer in a fixed structure:

```
STANCE: <one sentence>
REASONING: <2-4 sentences, citing sources by number>
SOURCES USED: <comma-separated source numbers>
```

Rationale:
- **Comparability** — with two personas answering the same topic in the
  same structure, differences in `STANCE` are easy to spot at a glance
  instead of buried in paragraph-length prose.
- **Verifiable grounding** — `SOURCES USED` gives a direct, checkable list
  per the acceptance criterion ("each opinion must be grounded in at least
  one relevant retrieved source").
- **Anti-genericness instruction** — the prompt explicitly forbids a
  "hedge-everything" answer, because early tests showed that without this
  line, two differently-configured personas would sometimes converge on
  the same cautious, balanced-sounding opinion.
- `parse_opinion()` does a best-effort split of the three fields so a demo
  script or test can assert on `stance` / `reasoning` / `sources_used`
  directly instead of grepping raw text.

## 6. Key design decisions (summary)

| Decision | Why |
|---|---|
| Persona as instructions, not a field list | Produces visibly different behavior, not just a different name |
| Memory and sources in separate labeled sections | Prevents the model from treating its own prior guesses as fact |
| Numbered, citable sources | Makes grounding checkable, not just claimed |
| Fixed STANCE/REASONING/SOURCES USED format for opinions | Makes persona differences and grounding easy to verify programmatically |
| Explicit anti-genericness instruction | Counters the model's default toward safe, hedged, near-identical answers |
| Prompt building centralized in `prompts/`, not inline in `agent.py` | Prompts can be edited/tested without touching orchestration logic |

## 7. Known limitations

- `parse_opinion()` is a simple line-based parser; it will misparse if the
  model doesn't follow the requested format exactly. It's a best-effort
  convenience, not a strict schema — no retry/validation loop is
  implemented yet.
- There's no automatic check that a persona's `STANCE` actually differs
  from another persona's; distinctness is currently verified manually
  (see "How to test" below) rather than with an automated similarity
  metric.
- The anti-genericness instruction is a prompt-level nudge, not a
  guarantee — a sufficiently cautious model can still hedge.

## 8. How to test prompt distinctness

Without calling the LLM, `build_system_prompt()` and `build_opinion_prompt()`
are pure string functions, so a cheap unit test can assert that two
different `Persona` objects produce different prompt text (e.g. the
`stance` and `communication_style` strings appear in the output). Testing
that the *resulting opinions* differ requires an actual LLM call and
belongs in the integration/demo test, not a unit test.