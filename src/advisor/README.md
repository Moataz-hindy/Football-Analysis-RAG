# Discussion advisor

The advisor reads a completed saved discussion, produces a decision, match
review, or match preview, and checks its cited claims against the supplied
excerpts. It also researches the knowledge database and the public internet
before generating the report. Backend implementation files live in this package.

## Files

| File | Purpose |
| --- | --- |
| `models.py` | Validated requests, evidence, reports, and result statuses. |
| `evidence.py` | Transcript/source registry, document grouping, recorded publication metadata, preview cutoffs, and snapshot hash. |
| `research.py` | Automatic database/web discovery and bounded LLM-directed follow-up searches and article reads. |
| `search.py` | Structured Tavily/DDGS results and public HTML/text page extraction. |
| `decision.py` | Action versus no action, with pros, cons, alternatives, and recommendations. Selects whole excerpts within an input budget. |
| `match_analysis.py` | Reviews and previews for both named teams. Checks prediction prerequisites before and after verification. |
| `verification.py` | Domain-independent claim checks and report pruning. Preserves original claims, full evidence, exact quotations, and rejected-claim reasons. |
| `service.py` | Background worker, job tracking, deduplication, timing/snapshot guards, and disk cache. |
| `routes.py` | Submission and polling endpoints for the API. |
| `tests/` | Offline regression tests using synthetic discussions and stub model clients. |

The generic checking API is `verify_claims`. The three analyst modes and their
request/report models remain football-specific.

## Direct Python use

```python
from src.advisor.models import AnalystRequest
from src.advisor.verification import analyze_verified

request = AnalystRequest(
    discussion_id="your-completed-discussion-id",
    mode="decision",
    question="Should the club recruit an attacker?",
)
result = analyze_verified(request)
```

This uses the existing `LLM_API_KEY`, `LLM_BASE_URL`, and `LLM_MODEL` environment
settings. For deterministic tests, pass `analyst_client` and `verifier_client`
objects exposing `generate(messages, tools=None)`.
The analyst client must support function calls during research; the final report
and citation-checking calls return structured JSON without tools. Research tests
inject providers into `research_evidence`; generation-only tests isolate research.

For jobs, call `start_advisor_worker()`, then `submit_job(request)` and
`get_job(discussion_id, job_id)` from `src.advisor.service`. Always call
`shutdown_advisor_worker()` during application shutdown. The job service
optionally reads `ADVISOR_VERIFIER_MODEL` for a separate verifier model on the
same endpoint.

## Application integration

`src/api/main.py` registers the advisor routes and manages its worker lifecycle.
The React app launches the advisor after the API confirms completed discussion
rounds. Reports appear below the Arena discussion and at the top of Intelligence.

The endpoints are:

- `POST /discussions/{discussion_id}/advisor/jobs`, with body
  `{"request": {"discussion_id": "...", "mode": "decision", "question": "..."}, "force": false}`.
- `GET /discussions/{discussion_id}/advisor/jobs/{job_id}`.

POST returns 202 for an accepted job or 200 for a cached result. Job states are
`queued`, `running`, `completed`, and `failed`. The result's analytical status
is separate: `complete`, `partial`, `insufficient_evidence`, or `failed`.

Restart the API after backend changes. Use **Reanalyze discussion** in the panel
to obtain fresh research instead of a finished cached result.

## Evidence research

Each run searches the database and web for the request, then reads up to two
discovered articles. The research LLM can request more targeted
`knowledge_search`, `web_search`, or `read_web_page` calls. The entire run is
bounded to eight provider calls and three model research rounds. Provider
failures preserve evidence already available and appear as limitations.

Database retrieval uses the existing Postgres/embedding configuration. Web
search uses `TAVILY_API_KEY` when present, with DDGS fallback; DDGS also works
without a search API key. Article reading supports public HTML/plaintext pages,
with bounded downloads and redirects. JavaScript-only pages, PDFs and
subscription-only text may be unavailable.

Additional sources receive `R` evidence IDs and preserve source URL/title,
origin, query, excerpt type, retrieval time, and recorded publication/update
times. They have no invented discussion-message attachment. The original saved
discussion and its snapshot hash are preserved. The response's `research` audit
is retained even when no report survives verification. Generated search-provider
answers and the research model's own summary are never registered as evidence.

For previews, an old publication date alone cannot establish what a live page
contained before a past cutoff. Newly fetched web material requires a trusted
pre-cutoff capture to be eligible; the current public-page reader does not
provide historical captures. Dated pre-cutoff database/discussion evidence can
still be used. Missing or invalid dates remain excluded rather than backdated.

## Cache and timing

There is one analysis worker with one additional queued slot. Identical active
requests share a job even when `force=true`; force bypasses finished cache
entries. Completed job records expire after one hour and may be evicted sooner
at the 128-record limit. Running jobs are retained.

Cache entries live under `reports/api_cache/advisor`, which is already ignored
by the project's Git configuration. Researched reports last up to one hour
(older reports without research up to 24 hours), with at most 64 files retained.
Preview entries expire no later than kickoff. Cache keys bind
the complete request, discussion snapshot, model settings, and implementation
fingerprint, including research/provider implementation. Failed analysis or failed
verification is not cached. Cache-write errors do not discard an otherwise
valid result.

Job tracking is in memory and requires one API worker process. Restarting it
loses job IDs; eligible disk results can still be reused by resubmission. A
multi-process deployment needs a shared queue/job registry.

## Evidence limits

`complete` means the required sections survived checking. It does not certify
real-world truth. The verifier assesses supplied excerpts rather than fetching
or authenticating original articles, publication dates, or uncited assumptions.
The analysis and verifier are model judgments and can make mistakes.

Preview evidence must have usable recorded times at or before the cutoff.
Older undated source attachments are excluded; supporting predictions from
those records requires better publication metadata during ingestion. A
prediction also needs complete retained do/avoid plans and dated source
citations covering each named team. It is withheld if verification removes
those prerequisites, or if kickoff has passed.

## Offline checks

From the repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 python -B -m pytest -p no:cacheprovider src/advisor/tests -q
```

The explicit path is required because the project's default pytest discovery
is configured for the top-level `tests` directory. These checks use no live
model calls. Frontend checks run with `npm run test:advisor` in `frontend`.
