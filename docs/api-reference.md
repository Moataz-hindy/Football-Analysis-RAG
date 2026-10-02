# API Reference

The FastAPI backend (`src/api/`) listens on port 8000 by default. Interactive
docs with request and response schemas for every endpoint are served at
**`/docs`** (Swagger UI) and **`/redoc`**, generated from the code. This page is
the overview.

- `src/api/routes.py`: discussions and analytics (no login required)
- `src/api/platform_routes.py`: accounts, profiles, personas, memory and reports
- `src/api/schemas.py`, `src/platform/models.py`: request and response models

---

## Discussions and analytics

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness check: `{"status": "ok"}` |
| `GET` | `/topics` | Curated debate topics |
| `GET` | `/discussions` | Saved and in-flight discussions, newest first |
| `POST` | `/discussions` | Start a discussion in the background; returns **202** with `discussion_id` and `status` |
| `GET` | `/discussions/{id}` | Full record: config, agents, graph, messages |
| `GET` | `/discussions/{id}/status` | `queued` · `running` · `completed` · `failed` · `not_found` · `unknown`, with `current_round` / `total_rounds` |
| `GET` | `/discussions/{id}/analytics` | Stance trajectories, agreement, influence and sentiment (computed once, then cached) |
| `GET` · `POST` | `/discussions/{id}/causal-analysis` | Counterfactual influence estimate (LLM) |
| `GET` · `POST` | `/discussions/{id}/synthesis` | LLM executive summary of the debate |
| `GET` · `POST` | `/discussions/{id}/advisor` | LLM "final decision" on the topic |

The last three are **get-or-compute**: both methods return the cached result if
there is one, and otherwise compute it (which costs LLM requests).

### Starting a discussion

```http
POST /discussions
Content-Type: application/json

{
  "topic": "Did Japan's 5-4-1 low block expose Spain's central progression?",
  "num_rounds": 3,
  "num_agents": 6
}
```

| Field | Default | Rules |
|---|---|---|
| `topic` | — | required, non-empty |
| `num_rounds` | `3` | 1–10 |
| `num_agents` | `6` | 2–6 |
| `discussion_id` | `disc-<8 hex>` | letters, digits, `_`, `-`; spaces are sanitised |
| `dynamic_personas` | `false` | generate 3v3 opposing camps with the LLM |
| `force_regenerate` | `false` | ignore cached generated personas |
| `persona_ids` | — | explicit list of system or user persona IDs |
| `camp_a_ids`, `camp_b_ids` | — | explicit camps; 2–6 personas in total, at least one per camp |

Jobs run **one at a time**. Up to `DISCUSSION_QUEUE_DEPTH` jobs (default 4,
counting the running one) are accepted; beyond that the API returns **503
"Discussion queue is full"**. Poll `/status` and then fetch the record. The
transcript is checkpointed after every turn, so `GET /discussions/{id}` shows
progress while the run is live.

Analytics, synthesis and advisor results are cached in `reports/api_cache/`
and recomputed when the discussion file changes. How analytics are scored is
explained in [analytics](analytics.md#2-stance-scoring-task-1).

---

## Accounts and personalisation

These endpoints use a session token returned by `/auth/register` or
`/auth/login` (valid for 14 days). Send it as `Authorization: Bearer <token>`,
or as a `session_token` cookie. Platform data is stored in SQLite at
`data/football_platform.db`.

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/auth/register` | — | Create an account and its profile; returns a token |
| `POST` | `/auth/login` | — | Log in; returns a token |
| `POST` | `/auth/logout` | ✓ | Invalidate the current session |
| `GET` | `/auth/me` | ✓ | Current user and profile |
| `GET` | `/profile` | ✓ | Current profile |
| `PATCH` | `/profile` | ✓ | Update profile settings and preferences |
| `GET` | `/profile/types` | — | Available profile types and their analytical priorities |
| `GET` | `/profile/memory` | ✓ | Saved memory items (optional `memory_type` filter) |
| `POST` | `/profile/memory` | ✓ | Create or update a memory item |
| `DELETE` | `/profile/memory/{memory_id}` | ✓ | Delete a memory item |
| `GET` | `/profile/personas` | ✓ | System personas plus the profile's own personas |
| `GET` | `/profile/personas/fields` | — | Supported persona fields |
| `POST` | `/profile/personas` | ✓ | Create a custom persona |
| `PATCH` | `/profile/personas/{persona_id}` | ✓ | Update a custom persona |
| `DELETE` | `/profile/personas/{persona_id}` | ✓ | Delete a custom persona |
| `POST` | `/profile/personas/generate` | ✓ | Generate personas with the LLM |
| `GET` | `/reports` | ✓ | The profile's reports |
| `GET` | `/reports/{report_id}` | ✓ | One report |
| `POST` | `/reports/generate` | ✓ | Generate a personalised report from a discussion |

---

## Frontend and static files

| Path | Serves |
|---|---|
| `/` | Redirects to `/app/` (the landing page) |
| `/arena`, `/history`, `/intel`, `/devops` | The matching page of the web app (also under `/app/…` and with `.html`) |
| `/app` | Static files of the built React app (`frontend/dist`) or, if it has not been built, of `frontend/` |

Allowed browser origins come from `CORS_ORIGINS` (comma-separated). When it is
unset, the local dev ports 3000, 5173 and 8501 are allowed.
