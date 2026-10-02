# Discussion Engine Architecture

How a multi-agent discussion is run, saved and reloaded: the orchestrator,
the persisted JSON record, and run reproducibility. For who talks to whom, see
[agent graph and routing](agent-graph-and-routing.md); for failure handling, see
[reliability and checkpointing](reliability-and-checkpointing.md).

## 0. How a run works

1. **Choose agents.** The six specialist personas in `personas/*.yaml` (2–6 of
   them), LLM-generated 3v3 camps (`--dynamic-personas`), or explicitly chosen
   system/user personas (`--persona-ids`, `--camp-a-ids`, `--camp-b-ids`).
2. **Build the graph** and a stateless `GraphRouter`.
3. **Round 0 — opening statements.** Every agent gives an initial opinion.
4. **Rounds 1…N.** Each agent receives the previous round's messages from its
   graph neighbours and replies. Agents can call `knowledge_search`,
   `web_search` and `calculator` during a turn.
5. **Checkpoint after every completed turn** to `outputs/{discussion_id}.json`.

Runs start from the CLI (`python -m src.discussion.run_discussion`) or from
`POST /discussions`, which runs the same script as a background job (one at a
time, with up to `DISCUSSION_QUEUE_DEPTH` jobs waiting, default 4).

---

## 1. Persistent Discussion History

Every multi-agent discussion execution generates a persistent, self-contained record. This record allows the entire discussion flow to be reconstructed, inspected, and analyzed by the [analytics](analytics.md) pipeline.

### 1.1 Storage Format and Location

Discussions are persisted as formatted JSON files in the `outputs/` directory:

```text
outputs/
├── .gitkeep
├── {discussion_id_1}.json
└── {discussion_id_2}.json
```

- Each file name follows the pattern `{discussion_id}.json`. The CLI defaults to a UUID; the API generates IDs like `disc-0cc18aca`. IDs may only contain letters, digits, `_` and `-`.
- `outputs/*.json` is ignored by git (`.gitignore`), while `outputs/.gitkeep` preserves the directory.
- All writes use an atomic rename pattern (`.tmp` file followed by `os.replace`) to prevent corruption or partial files if a process is killed mid-write.

---

### 1.2 Discussion JSON Schema

```json
{
  "config": {
    "discussion_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "topic": "Evaluate Japan's 5-4-1 low block against Spain in World Cup 2022",
    "num_rounds": 3,
    "agent_ids": ["tactical_analyst", "statistical_analyst"],
    "graph": {
      "tactical_analyst": ["statistical_analyst"],
      "statistical_analyst": ["tactical_analyst"]
    },
    "llm_model": "<LLM_MODEL>",
    "llm_temperature": 0.2,
    "timestamp": "2026-09-07T14:00:00Z",
    "metadata": {
      "schema_version": 2,
      "status": "completed",
      "current_round": 3,
      "last_completed_round": 3,
      "persona_files": {"tactical_analyst": "personas/tactical_analyst.yaml"},
      "dynamic_personas": false,
      "camps": {},
      "retrieval": "week1_pgvector_k6",
      "llm_base_url": "<LLM_BASE_URL>",
      "llm_max_tokens": 1024
    }
  },
  "messages": [
    {
      "round_num": 1,
      "sender_id": "tactical_analyst",
      "recipient_ids": ["statistical_analyst"],
      "content": "Japan maintained horizontal compactness...",
      "sentiment_score": 0.42,
      "sentiment_label": "positive",
      "timestamp": "2026-09-07T14:01:00Z",
      "sources_used": [
        {
          "content": "Japan possession 17.7% vs Spain...",
          "source": "https://theanalyst.com/2022/12/japan-spain-world-cup",
          "score": 0.92,
          "metadata": {}
        }
      ],
      "retrieval_events": [
        {
          "query": "Japan low block Spain possession stats",
          "num_results": 1,
          "timestamp": "2026-09-07T14:00:45Z",
          "metadata": {}
        }
      ],
      "metadata": {}
    }
  ],
  "opinions": [
    {
      "agent_id": "tactical_analyst",
      "round_num": 0,
      "stance": "High-risk but structurally sound defensive setup.",
      "reasoning": "Midfield spacing denied central penetration.",
      "sources_used": "",
      "raw_text": "Initial opinion text...",
      "timestamp": "2026-09-07T14:00:05Z",
      "changed_from_previous": false,
      "change_reason": ""
    },
    {
      "agent_id": "tactical_analyst",
      "round_num": 1,
      "stance": "Confident the low block was net-positive.",
      "reasoning": "Transition moments punished Spain's high line, changing my assessment.",
      "sources_used": "",
      "raw_text": "Round 1 updated analysis...",
      "timestamp": "2026-09-07T14:02:10Z",
      "changed_from_previous": true,
      "change_reason": "Transition moments punished Spain's high line, changing my assessment."
    }
  ],
  "metadata": {
    "duration_seconds": 125.4,
    "total_messages": 2,
    "total_retrieval_events": 1,
    "errors": [],
    "extra": {}
  }
}
```

---

### 1.2.1 Opinion Evolution

`opinions[]` doubles as the agent's opinion-evolution history: for a given
`agent_id`, sorting its snapshots by `round_num` gives the initial opinion
(`round_num == 0`), the opinion recorded after every subsequent discussion
round, and the final opinion (the highest `round_num`). Two extra fields
on `OpinionSnapshot` track change over time:

- `changed_from_previous` (bool): whether the parsed `stance` differs from
  that same agent's immediately preceding snapshot (case/whitespace
  insensitive comparison). Always `false` for `round_num == 0`.
- `change_reason` (str): when a change is detected, a short excerpt taken
  from the agent's own `REASONING` for that round; otherwise `""`.

This is built by `build_opinion_history(state)` in `persistence.py`, which
walks `state.messages` per agent in round order — so it works for any
configured `total_rounds`, not just a fixed count.

### 1.3 Module APIs (`src.discussion.persistence`)

#### `save_discussion(result, output_dir="outputs") -> str`
- **Input**: A `DiscussionResult` dataclass instance or a conforming dictionary.
- **Action**: Validates `discussion_id`, ensures `output_dir` exists, writes atomically to `{output_dir}/{discussion_id}.json`.
- **Returns**: Path to the saved JSON file.
- **Exceptions**: Raises `ValueError` if required fields are missing; re-raises `IOError` / `OSError` on disk failures after logging.

#### `load_discussion(path) -> DiscussionResult`
- **Input**: Path to a `.json` discussion file.
- **Action**: Validates file existence and JSON validity, checks schema completeness, reconstructs full `DiscussionResult` and nested dataclasses (`DiscussionConfig`, `DiscussionMessage`, `OpinionSnapshot`, `DiscussionMetadata`).
- **Returns**: Reconstructed `DiscussionResult`.
- **Exceptions**: Raises `FileNotFoundError` if missing; raises `ValueError` if corrupted or invalid.

#### `list_discussions(output_dir="outputs") -> list[dict]`
- **Input**: Directory path (defaults to `"outputs"`).
- **Action**: Scans for `*.json` files, reads top-level metadata, handles and logs warnings for corrupt files without crashing.
- **Returns**: List of discussion summaries sorted newest first by timestamp.

#### `save_discussion_from_state(state, router=None, ...) -> str`
- **Input**: A `DiscussionState` object (from the orchestrator's `run()` method) and optionally the `GraphRouter` used.
- **Action**: Bridges the orchestrator's data model to the persistence JSON format:
  - Maps `round_number` → `round_num`
  - Maps `sources` → `sources_used`
  - Converts `tool_calls` → `retrieval_events`
  - Extracts `opinions[]` by parsing STANCE/REASONING/SOURCES USED markers from agent responses
  - Serializes the graph adjacency list from the router
- **Returns**: Path to the saved JSON file.
- **Integration example**:
  ```python
  from src.discussion.persistence import save_discussion_from_state

  state = orchestrator.run(topic="...", total_rounds=3)
  path = save_discussion_from_state(
      state=state,
      router=router,
      llm=llm,  # model and temperature are read from the adapter
      duration_seconds=elapsed,
  )
  ```

---

### 1.4 Logging Strategy

All persistence operations log through Python's standard `logging` library using logger `src.discussion.persistence`:

- **INFO**: Successful save operations (with file size, agent count, message count), successful loads (with topic and round count), and discovery counts during listing.
- **WARNING**: Corrupted JSON files skipped during `list_discussions()`, missing non-critical metadata fields during reconstruction.
- **ERROR**: File write failures, permission issues, JSON syntax errors, and schema validation failures with full exception traceback.

## 2. Run Identity & Reproducibility

### 2.1 Run identity

Every discussion run carries a `discussion_id`. By default the
orchestrator generates a UUID4, so two runs of the same topic never
collide. A caller can pin a deterministic name:

```python
state = orchestrator.run(topic="...", total_rounds=3, discussion_id="2026-09-09_japan-low-block")
```

Because `save_discussion` names the record `{discussion_id}.json`, the
identifier alone retrieves the complete history:

```python
from src.discussion import load_discussion_by_id
result = load_discussion_by_id("2026-09-09_japan-low-block")
```

### 2.2 Captured run configuration

The persisted `config` block records everything needed to trace a run
:

| Field | Source of truth |
|---|---|
| `discussion_id` | Orchestrator (or caller-supplied) |
| `topic`, `num_rounds`, `agent_ids` | `DiscussionState` |
| `graph` | Adjacency list serialized from the `GraphRouter` |
| `llm_model`, `llm_temperature` | The LLM adapter itself (`OpenAICompatibleLLM.model` / `.temperature`), captured automatically by `save_discussion_from_state(..., llm=llm)`. Hand-passed values keep priority and act as an override. |
| `metadata.llm_base_url`, `metadata.llm_max_tokens` | LLM adapter |
| `metadata.llm_seed` | `LLM_SEED` environment variable, recorded when set |
| `metadata.persona_files`, `metadata.retrieval`, `metadata.status` | Supplied by the runner (`src/discussion/run_discussion.py`) |

### 2.3 Nondeterminism

Exact reproduction of LLM output is not guaranteed: providers sample
stochastically, free tiers throttle, and tool traces may vary. The system
makes the run **traceable** instead:

* Set `LLM_TEMPERATURE=0` in `.env` for the most stable behavior.
* Optionally set `LLM_SEED`; it is recorded in the config metadata.
* Every message carries `timestamp` and `message_id`; recipients come
  from the persisted graph, so routing and ordering are reconstructable.

### 2.4 Reproducible demonstration

```bash
python -m src.discussion.run_discussion                       # default topic, 3 rounds
python -m src.discussion.run_discussion --discussion-id demo_run_1
```

The script builds the six persona agents, runs the discussion with knowledge-base
retrieval enabled, saves `outputs/{discussion_id}.json`, then reloads the
record by ID and prints a verification summary (participants, rounds,
messages, retrieval events, opinion changes).

Other runner options: `--rounds`, `--agents` (2–6), `--output-dir`,
`--personas-dir`, `--dynamic-personas`, `--force-regenerate`,
`--persona-ids`, `--camp-a-ids`, `--camp-b-ids`, and `--overwrite` to replace
an existing record with the same ID.
