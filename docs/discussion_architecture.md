# Discussion Engine Architecture

This document describes the multi-agent discussion architecture developed for Week 3 of the Football Analysis RAG project, detailing the components, data models, persistence format, and interaction protocols.

---

## 1. Persistent Discussion History (Section 4.6, 16, 17, 23, 30)

Every multi-agent discussion execution generates a persistent, self-contained record. This record allows the entire discussion flow to be reconstructed, inspected, and analyzed by the downstream Week 4 analytics engine.

### 1.1 Storage Format and Location

Discussions are persisted as formatted JSON files in the `outputs/` directory:

```text
outputs/
├── .gitkeep
├── {discussion_id_1}.json
└── {discussion_id_2}.json
```

- Each file name follows the pattern `{discussion_id}.json` using a UUID.
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
    "agent_ids": ["Tactical Analyst", "Statistical Analyst"],
    "graph": {
      "Tactical Analyst": ["Statistical Analyst"],
      "Statistical Analyst": ["Tactical Analyst"]
    },
    "llm_model": "openai/gpt-oss-20b",
    "llm_temperature": 0.2,
    "timestamp": "2026-09-07T14:00:00Z",
    "metadata": {}
  },
  "messages": [
    {
      "round_num": 1,
      "sender_id": "Tactical Analyst",
      "recipient_ids": ["Statistical Analyst"],
      "content": "Japan maintained horizontal compactness...",
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
      "agent_id": "Tactical Analyst",
      "round_num": 0,
      "stance": "High-risk but structurally sound defensive setup.",
      "reasoning": "Midfield spacing denied central penetration.",
      "sources_used": "",
      "raw_text": "Initial opinion text...",
      "timestamp": "2026-09-07T14:00:05Z",
      "metadata": {}
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

---

### 1.4 Logging Strategy

All persistence operations log through Python's standard `logging` library using logger `src.discussion.persistence`:

- **INFO**: Successful save operations (with file size, agent count, message count), successful loads (with topic and round count), and discovery counts during listing.
- **WARNING**: Corrupted JSON files skipped during `list_discussions()`, missing non-critical metadata fields during reconstruction.
- **ERROR**: File write failures, permission issues, JSON syntax errors, and schema validation failures with full exception traceback.
