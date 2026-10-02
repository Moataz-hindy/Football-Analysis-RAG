# Short discussion Advisor

The Arena places the Advisor's opinion above the debate. After confirmed completion,
opening the discussion requests a 100–180 word assessment of the original topic.
Transfer questions get advice and tradeoffs; match reviews get supported explanations
and possible improvements. The Advisor is a synthesis, not independent fact-checking.
It uses saved source excerpts and identifies uncertain premises. No external research,
tools, verifier model, format-repair loop, or full-report regeneration is run.

## Request and cost contract

- `GET /discussions/{id}/advisor` only reads the result/status.
- `POST /discussions/{id}/advisor` with `{}` generates once if missing.
- One generation per new discussion snapshot, up to 700 output tokens; the
  prompt plus supplied context is bounded to 24,000 characters (not a token count).
- Transient provider failures use the shared `LLM_MAX_RETRIES` and delay-window
  settings: by default eight retries with 5, 10, 20, 40, 60, 90, 120, 180 second
  waits, small jitter, a 300-second single-wait cap and 600-second total sleep budget.
  SDK retries remain disabled. The 45-second request timeout is per attempt.
- Failures are persisted. `{ "retry_failed": true }` explicitly retries a failed
  opinion, including older failures that exhausted the previous two-attempt limit.
  Reopening a failure does not generate automatically. Successful results are reused.
- A heartbeat renews the generation claim every 30 seconds through long retry waits.
  Claims with no heartbeat for five minutes become retryable. Attempt start times
  remain in the separate usage ledger. The browser reconnects after a lost POST
  response and continues read-only polling while the claim is running.
- SQLite atomically claims a snapshot before generation, preventing duplicate paid
  calls across browser tabs and server processes sharing the cache file. Do not run
  multiple replicas with independent cache files if global deduplication is required.
- Cached results have no automatic expiry. The key includes discussion content,
  saved evidence, model, endpoint, prompt, and input version. Analytics/UI metadata
  changes do not invalidate it. Deleting the cache or changing these inputs permits
  a new request. No recurring/background refresh is scheduled.

Optional `ADVISOR_MODEL` selects a model on the configured `LLM_BASE_URL`; otherwise
the Advisor uses `LLM_MODEL` and `LLM_API_KEY`. Existing provider configuration applies.
Retries may incur additional provider charges; failed request usage may be unknown.
The successful provider response's usage fields are saved with the result in
`reports/api_cache/advisor/opinions.sqlite3` and returned by the API. Missing usage
is unknown, not zero. The GET response also includes an `attempt_usage` ledger so a
retry does not erase the first attempt's usage. A provider error may leave usage
unknown even if billed.

Estimate cost using the provider's actual input/output prices and recorded tokens:
`input_tokens / 1_000_000 * input_price + output_tokens / 1_000_000 * output_price`.
Include any provider-specific reasoning/cache charges. No dollar estimate or spending
cap is implied by the character bound. Existing debate/analytics calls are separate.

## Limitations and checks

Each speaker's latest messages are selected first in a balanced order. Messages and
source excerpts are shortened to fit the budget, with shortening explicitly marked.
Source IDs are validated locally; semantic support is judged in the single generation
call and is not independently verified. Contradictions can still escape the model.
The panel displays this limitation and exposes cited source excerpts.

Tests use stub clients, with network blocked by the project test fixture:

```bash
python -m pytest tests/test_advisor.py tests/test_llm.py -q
cd frontend
node --test src/lib/advisorClient.test.js
npm run build
```

The new Advisor does not replace the separate Intelligence synthesis or alter the
discussion agents. A future shared facts/contradiction-validation stage belongs upstream
of both the debate and the Advisor, rather than inside another expensive repair loop.

## Strategic decision panel

The Intelligence view retains the structured decision dossier from the incoming changes.
It uses `GET /discussions/{id}/advisor/decision` to read and `POST` with `{}` to generate.
The response has the same `state`, `retryable`, and cache metadata as the short opinion,
with its output under `decision`. Both endpoints share durable claims, heartbeat renewal,
provider retry windows, snapshot invalidation and usage tracking, but have separate cache
keys and output budgets (700 tokens for the opinion, 2,500 for the decision).

The dossier is requested only when opening Intelligence for a completed discussion.
It uses saved excerpts, validates its JSON and citations, and displays failures with an
explicit retry action. It never substitutes canned rulings or statistics on model failure.
Successful results are reused; checking again does not force another generation.

The structured decision now sends `response_format.type=json_schema` to the model
endpoint, using the same Pydantic model as local validation (including required fields,
allowed topic types, three action steps, and nested stakeholder fields). The short
opinion and debate turns remain text responses. The endpoint must support JSON-schema
structured output. The decision cache key includes this schema so old failed free-text
attempts cannot prevent generation with the corrected request. Format failures are still
reported explicitly; there is no hidden fallback to unrestricted text or fabricated output.
