# Memory and RAG Retrieval Integration

This document outlines the design decisions, strategies, and limitations for the Memory and Knowledge Retrieval components implemented for the Week 2 Intelligent Agent Framework.

## 1. Memory Strategy (`src/agent/memory.py`)

The agent framework uses a **Summarized Sliding Window** approach for its memory mechanism (`ConversationMemory`).

### How it works:
1. **Recent Context (Sliding Window):** The memory maintains a literal, verbatim transcript of the most recent `max_turns` (default is 5). This ensures that the agent has exact quotes and perfect context for the immediate back-and-forth of the conversation.
2. **Older Context (Summarization):** When the conversation exceeds the `max_turns` threshold, the oldest interaction is popped from the verbatim list. Before being discarded, this interaction is passed to an LLM alongside the current running summary. The LLM generates a newly updated, concise summary of the entire conversation up to that point.
3. **Retrieval:** When the agent needs memory context, `get_relevant()` returns the running summary paragraph followed by the exact transcript of the last 5 turns.

### Known Limitations:
* **Loss of Fine-Grained Detail:** Because older turns are summarized, highly specific details (like exact metric numbers or niche tactical terms) mentioned early in a long conversation might be abstracted away by the summarizer LLM.
* **API Dependency:** The memory summarization step requires a live connection to the LLM API. If the API fails or rate-limits, the memory module currently drops the oldest message without summarizing it, leading to a silent loss of context.
* **No Disk Persistence:** Currently, memory only lives in the Python runtime. If the agent script is restarted, the memory is wiped clean.

---

## 2. RAG Retrieval Integration (`src/agent/retrieval.py`)

The retrieval component (`RAGRetrieval`) acts as a clean bridge between the new Agent framework and the Week 1 PostgreSQL `pgvector` knowledge base.

### How it works:
1. It imports the fully functional `search()` method from `src.rag.search`.
2. When the agent initiates a retrieval request, `RAGRetrieval.retrieve()` queries the database using the same embedding model defined in Week 1.
3. The raw dictionary outputs from Week 1 (containing `doc_id`, `text`, `similarity`, etc.) are wrapped into strongly typed `RetrievedSource` dataclasses.
4. This ensures the main `Agent` loop can access the exact text, origin URLs, and similarity scores without knowing anything about the underlying PostgreSQL implementation.

### Known Limitations:
* **Connection Management:** The retrieval class relies on `src.rag.search` to manage its own database connections. If the PostgreSQL Docker container is not running, retrieval will fail gracefully and return an empty list of sources, rather than crashing the agent.
