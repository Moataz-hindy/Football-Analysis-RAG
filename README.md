# ⚽ Football Analysis RAG — Week 1: Knowledge Infrastructure

A **Retrieval-Augmented Generation (RAG)** system that builds a searchable knowledge base of football (soccer) content — covering the **Laws of the Game**, **football analytics metrics**, **tactical concepts**, and **match analysis** — and retrieves the most relevant passages for any natural-language question using vector similarity search.

This repository is the **Week 1 deliverable** for the Knowledge Infrastructure milestone. It provides the retrieval foundation that Week 2 agents, Week 3 discussions, and Week 4 analytics will build upon.

---

## 📖 Table of Contents

- [Domain Selection](#domain-selection)
- [Overview](#overview)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Setup & Installation](#setup--installation)
- [Running the Pipeline](#running-the-pipeline)
- [Searching the Knowledge Base](#searching-the-knowledge-base)
- [Design Decisions](#design-decisions)
- [Evaluation](#evaluation)
- [Week 2 Handoff — Retrieval Interface](#week-2-handoff--retrieval-interface)
- [Known Limitations](#known-limitations)
- [Tech Stack](#tech-stack)

---

## Domain Selection

**Domain:** Football (Soccer) — Laws, Analytics, Tactics & Match Analysis

Football was chosen because it offers a well-defined knowledge domain with four distinct sub-topics that test retrieval across very different content styles:

| Sub-topic | Source type | Content style |
|---|---|---|
| **Laws of the Game** | IFAB official laws | Formal, rule-based, precise language |
| **Analytics Metrics** | Articles on xG, xA, PPDA, xT | Technical, statistical, definition-heavy |
| **Tactical Concepts** | Guides on formations, pressing, transitions | Descriptive, instructional, diagram-heavy |
| **Match Analysis** | World Cup match reports | Narrative, event-driven, stat-rich |

This diversity makes retrieval evaluation meaningful — a system that works well across all four sub-topics demonstrates genuine retrieval quality rather than benefiting from a narrow, homogeneous corpus.

---

## Overview

This project implements an end-to-end RAG pipeline:

1. **Collect** — Scrapes 80+ football-related web pages from seed URLs (IFAB laws, analytics explainers, tactical guides, World Cup match reports).
2. **Clean** — Strips HTML boilerplate, navigation, ads, and noise widgets; repairs encoding issues (mojibake); extracts pure article text.
3. **Chunk & Embed** — Splits each document into overlapping 1 200-character chunks and generates 1 024-dimensional vector embeddings via the OpenRouter API.
4. **Ingest** — Loads the embedded chunks into a PostgreSQL database with the **pgvector** extension using upsert semantics.
5. **Search** — Embeds a user's question with the same model and retrieves the top-k most similar chunks using cosine distance.
6. **Evaluate** — Runs a 7-query benchmark to measure Precision@5, Recall@5, and MRR of the retriever.

---

## Architecture

```
┌────────────┐     ┌────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Web Pages │────▶│  Collector │────▶│  Cleaner        │────▶│  Chunker &      │
│  (80+ URLs)│     │ collect.py │     │  clean.py       │     │  Embedder       │
└────────────┘     └────────────┘     └─────────────────┘     │ process_all.py  │
                                                               └────────┬────────┘
                                                                        │
                                                                        ▼
┌────────────┐     ┌────────────┐                          ┌─────────────────────┐
│   User     │────▶│  Search    │◀────────────────────────▶│    PostgreSQL 16    │
│  Question  │     │ search.py  │   cosine similarity      │   + pgvector        │
└────────────┘     └────────────┘                          │   (IVFFlat index)   │
                                                           └─────────────────────┘
```

---

## Project Structure

```
Football-Analysis-RAG/
├── data/
│   ├── raw/                  # Scraped HTML documents (JSON) — 83 files
│   ├── clean/                # Cleaned plain-text documents (JSON) — 81 files
│   └── embeddings/           # Chunks with vector embeddings (JSON) — 81 files
├── docs/
│   └── evaluation.md         # Retrieval evaluation methodology & interpretation
├── sql/
│   └── init_db.sql           # PostgreSQL schema (pgvector table + IVFFlat index)
├── src/
│   ├── ingestion/
│   │   ├── collect.py        # Web scraper — fetches pages from seed URLs
│   │   └── clean.py          # HTML cleaner — extracts article text
│   └── rag/
│       ├── utils.py          # Shared paths & chunking utility
│       ├── process_all.py    # Chunks documents & generates embeddings
│       ├── ingest.py         # Loads embeddings into PostgreSQL
│       ├── search.py         # Vector similarity search (CLI + function)
│       └── evaluate.py       # Retrieval benchmark (Precision, Recall, MRR)
├── .env.example              # Template for environment variables
├── docker-compose.yml        # PostgreSQL + pgvector container
├── requirements.txt          # Python dependencies
└── README.md                 # ← You are here
```

---

## Prerequisites

| Tool               | Version | Purpose                            |
|--------------------|---------|------------------------------------|
| **Python**         | 3.10+   | Run all scripts                    |
| **Docker**         | 20+     | Host the PostgreSQL + pgvector DB  |
| **Docker Compose** | v2+     | Spin up the database container     |
| **OpenRouter API Key** | —   | Generate text embeddings           |

---

## Setup & Installation

### 1. Clone the repository

```bash
git clone https://github.com/Moataz-hindy/Football-Analysis-RAG.git
cd Football-Analysis-RAG
```

### 2. Create a Python virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in your real values:

| Variable           | Description                                                       |
|--------------------|-------------------------------------------------------------------|
| `DB_HOST`          | Database host (default: `localhost`)                               |
| `DB_PORT`          | Database port (default: `5432`)                                    |
| `DB_NAME`          | Database name (default: `football_intelligence`)                   |
| `DB_USER`          | Database user (default: `postgres`)                                |
| `DB_PASSWORD`      | Database password                                                  |
| `OPENAI_API_KEY`   | Your [OpenRouter](https://openrouter.ai/) API key                  |
| `OPENROUTER_MODEL` | Embedding model (default: `liquid/lfm-2.5-embedding-350m:free`)    |

### 5. Start the database

```bash
docker-compose up -d
```

This launches a **PostgreSQL 16** container with the **pgvector** extension. The schema in `sql/init_db.sql` runs automatically on first start, creating the `football_chunks` table with a 1 024-dimensional vector column and an IVFFlat cosine index.

---

## Running the Pipeline

Run each step **in order** from the project root:

### Step 1 — Collect raw data

```bash
python src/ingestion/collect.py
```

Scrapes all 80+ seed URLs and saves the raw HTML as JSON files in `data/raw/`. Each document preserves the source URL, page title, collection timestamp, and full HTML. A 2-second delay between requests is used to be polite to servers.

**Output:** 83 raw JSON files in `data/raw/`

### Step 2 — Clean the data

```bash
python src/ingestion/clean.py
```

Strips HTML tags, `<script>`, `<style>`, `<nav>`, `<footer>`, `<header>`, `<aside>` elements, and noise widgets (live-score tickers, cookie banners, ads). Repairs mojibake encoding issues. Documents with less than 100 characters after cleaning are skipped.

**Output:** 81 cleaned JSON files in `data/clean/`

### Step 3 — Chunk & embed

```bash
python src/rag/process_all.py
```

Splits each cleaned document into overlapping chunks (1 200 chars, 200-char overlap) and calls the OpenRouter embedding API in batches of 50. Includes retry logic with exponential backoff for API rate limits. Already-embedded documents are skipped by default.

**Output:** 81 embedding JSON files in `data/embeddings/`

### Step 4 — Ingest into PostgreSQL

```bash
python src/rag/ingest.py
```

Loads all embedded chunks into the `football_chunks` table. Uses upsert (`ON CONFLICT ... DO UPDATE`) so it's safe to re-run. Validates that the embedding dimension matches the database column before inserting.

### Step 5 — Search (demo)

```bash
python src/rag/search.py "What is expected goals (xG)?"
```

### Step 6 — Evaluate

```bash
python src/rag/evaluate.py
```

---

## Searching the Knowledge Base

### Interactive mode

```bash
python src/rag/search.py
```

Opens an interactive prompt — type any football question and get the top-5 most relevant chunks with similarity scores. Type `quit` or `exit` to stop.

### Single query mode

```bash
python src/rag/search.py "What is the offside rule in football?"
```

Returns the 5 most similar chunks with doc ID, chunk index, title, and a text preview.

---

## Design Decisions

### Data Collection Strategy

| Decision | Choice | Rationale |
|---|---|---|
| **Source discovery** | Manually curated seed URLs | Ensures high-quality, on-topic sources rather than noisy web crawling. The 80+ URLs are grouped into 4 sub-topics for balanced corpus coverage. |
| **Scraping tool** | `requests` + `BeautifulSoup` | Lightweight, no browser overhead. Sufficient for static content pages. |
| **Document format** | JSON with `id`, `url`, `title`, `collection_date`, `raw_html` | Preserves full provenance. Storing raw HTML allows re-cleaning with different strategies without re-scraping. |
| **Encoding handling** | `response.apparent_encoding` fallback | Many servers don't declare charset; sniffing avoids mojibake from the default ISO-8859-1 assumption. |
| **Rate limiting** | 2-second sleep between requests | Prevents aggressive crawling and potential IP blocks. |

### Cleaning Strategy

| Decision | Choice | Rationale |
|---|---|---|
| **Approach** | Tag-based removal + keyword-based noise filtering | Removes structural HTML (`<script>`, `<style>`, `<nav>`, etc.) first, then identifies noise widgets by class/id keywords (e.g., `ticker`, `livescore`, `cookie`, `banner`). |
| **Mojibake repair** | `latin1 → utf-8` re-encoding | Detects and fixes double-encoded UTF-8 characters (e.g., `â€¢` → `•`). |
| **Minimum length** | 100 characters | Documents with less than 100 chars of clean text are likely empty shells or error pages and are skipped. |
| **Whitespace normalization** | `" ".join(text.split())` | Collapses all whitespace (newlines, tabs, multiple spaces) into single spaces for uniform chunk boundaries. |

### Chunking Strategy

| Decision | Choice | Rationale |
|---|---|---|
| **Method** | Fixed-size character chunking with overlap | Simple, dependency-free, and predictable. No external NLP libraries needed. |
| **Chunk size** | 1 200 characters | Fits comfortably within the embedding model's context window while being large enough to preserve meaningful context. |
| **Overlap** | 200 characters | Ensures that a fact split across a chunk boundary appears whole in at least one chunk. ~17% overlap balances redundancy vs. coverage. |
| **Trade-offs considered** | Sentence-based chunking would produce more semantically coherent chunks, but adds dependency on sentence tokenizers and is harder to control for size. Fixed-size is a pragmatic baseline. |

### Embedding Model

| Property | Value |
|---|---|
| **Model** | `liquid/lfm-2.5-embedding-350m:free` |
| **Provider** | [OpenRouter](https://openrouter.ai/) |
| **Vector dimensionality** | 1 024 |
| **Reason for selection** | Free tier on OpenRouter — no cost for the project. 350M parameters provide reasonable semantic quality. The 1 024-dimensional output is a good balance between expressiveness and storage/compute cost. |

### Vector Database Configuration

| Decision | Choice | Rationale |
|---|---|---|
| **Database** | PostgreSQL 16 + pgvector | Required by the assignment. pgvector is the most mature Postgres vector extension. |
| **Container** | `pgvector/pgvector:pg16` via Docker Compose | Official image with pgvector pre-installed. Reproducible single-command setup. |
| **Index type** | IVFFlat with `vector_cosine_ops`, 100 lists | IVFFlat is faster to build than HNSW and sufficient for a corpus of this size. Cosine distance matches the embedding model's similarity semantics. |
| **Schema** | Single `football_chunks` table with `(doc_id, chunk_index)` unique constraint | Simple flat schema. Upsert support allows safe re-ingestion. |

### Retrieval Strategy

| Decision | Choice | Rationale |
|---|---|---|
| **Approach** | Dense vector RAG (basic vector similarity) | The corpus is well-curated and the embedding model handles semantic matching well. No evidence of a retrieval failure pattern that would justify the added complexity of re-ranking, hybrid search, or graph-based retrieval at this stage. |
| **Distance metric** | Cosine similarity (`1 - cosine_distance`) | Standard for text embeddings. The IVFFlat index is built with `vector_cosine_ops` to match. |
| **Top-k** | 5 (default) | Enough to surface relevant context from multiple sources without overwhelming downstream consumers. |
| **Query embedding** | Same model as document embeddings | Required for consistent vector space — query and document vectors must be comparable. |

---

## Evaluation

### Methodology

The retrieval system is evaluated against a benchmark of **7 representative football questions** spanning all four sub-topics. Each query has manually labeled relevant source documents identified by `doc_id`. A retrieved chunk is considered relevant when its source document is in the label set.

Labels are source-level (not chunk-level) because the pipeline does not persist human-authored chunk relevance judgments.

### Metrics (at k=5)

| Metric | Definition |
|---|---|
| **Precision@5** | Unique relevant source documents in the top-5 ÷ 5 |
| **Recall@5** | Unique relevant source documents found in the top-5 ÷ total labeled relevant documents |
| **MRR** | 1 ÷ rank of the first relevant source (0 if none retrieved) |

### Evaluation Set

| ID | Query | Relevant Sources |
|---|---|---|
| `rules-offside` | When is a player in an offside position, and when is it an offence? | `doc_011`, `doc_012` |
| `analytics-xg` | What is expected goals (xG), and how should a value of 0.2 be interpreted? | `doc_019`, `doc_024`, `doc_027` |
| `analytics-pressing` | What does PPDA measure and how is it used to assess pressing intensity? | `doc_028`, `doc_027`, `doc_024` |
| `analytics-progression` | What is expected threat (xT) and how does it value ball progression? | `doc_030`, `doc_024`, `doc_027` |
| `tactics-formation` | How is a 4-3-3 football formation structured, and what are its player lines? | `doc_043`, `doc_046`, `doc_047` |
| `tactics-counterattack` | What happens during a counter-attack immediately after winning the ball? | `doc_060`, `doc_061`, `doc_053` |
| `match-japan-spain` | What happened in Japan's 2-1 World Cup win over Spain? | `doc_077` |

### How to Run

```bash
python src/rag/evaluate.py
```

Results are written to `docs/evaluation_results.json`.

### Interpretation Guidelines

| Symptom | Likely Cause | Suggested Fix |
|---|---|---|
| Low MRR with reasonable recall | Right source present but ranked too low | Add a re-ranker or improve chunk boundaries |
| Low recall for one topic | Missing or poorly labeled corpus coverage | Add more sources for that topic |
| Low precision with high recall | Duplicate or overly broad chunks | Reduce overlap or add a re-ranker |
| Consistently low scores | Embedding model, index, or query config issue | Investigate model quality and index parameters |

See [`docs/evaluation.md`](docs/evaluation.md) for the full evaluation methodology document.

---

## Week 2 Handoff — Retrieval Interface

Week 2 agents will use this system to retrieve factual context for their reasoning. The retrieval interface is exposed as a **Python function** in `src/rag/search.py`.

### Interface

```python
from search import search

results = search(question, k=5)
```

### Input

| Parameter | Type | Default | Description |
|---|---|---|---|
| `question` | `str` | — | Natural-language query |
| `k` | `int` | `5` | Number of chunks to retrieve |
| `client` | `OpenAI` | `None` | Optional pre-initialized OpenAI client (created automatically if not provided) |
| `model` | `str` | `None` | Optional embedding model name (read from `.env` if not provided) |
| `conn` | `psycopg2.connection` | `None` | Optional pre-opened DB connection (created automatically if not provided) |

### Output

Returns a `list[dict]` ordered by similarity (best match first). Each dict contains:

```python
{
    "doc_id": "doc_011",          # Source document identifier
    "chunk_index": 3,             # Position of the chunk within the document
    "title": "Offside | IFAB",    # Page title of the source
    "url": "https://...",         # Original source URL
    "text": "A player is in...",  # Full chunk text
    "similarity": 0.847           # Cosine similarity score (0–1)
}
```

### Example

```python
from search import search

results = search("What is expected goals (xG)?", k=3)

for r in results:
    print(f"[{r['doc_id']}] similarity={r['similarity']:.3f}")
    print(f"  {r['text'][:100]}...")
```

### CLI Access

```bash
# Single query
python src/rag/search.py "What is the offside rule?"

# Interactive mode
python src/rag/search.py
```

---

## Known Limitations

1. **Fixed-size chunking** — Character-based splitting is not sentence-aware and may cut mid-word or mid-sentence. Sentence-based or semantic chunking would improve chunk quality.
2. **No re-ranking** — The system returns raw cosine similarity results without a cross-encoder re-ranker, which could improve precision for ambiguous queries.
3. **Free-tier embedding model** — The `liquid/lfm-2.5-embedding-350m:free` model is lightweight (350M params). A larger model would likely improve retrieval quality but would introduce cost.
4. **Static corpus** — The seed URLs are hardcoded. Adding new sources requires editing `collect.py` and re-running the pipeline.
5. **No hybrid search** — Only dense vector retrieval is used. Adding BM25 keyword search alongside vector search could help with exact-match queries (e.g., specific rule numbers).
6. **Single-table schema** — All chunks are in one flat table. A multi-table schema with separate documents and chunks tables would better support metadata queries and document-level operations.

---

## Tech Stack

| Component        | Technology                                                                |
|------------------|---------------------------------------------------------------------------|
| Language         | Python 3.10+                                                              |
| Web Scraping     | `requests` + `BeautifulSoup4`                                             |
| Embeddings       | [OpenRouter API](https://openrouter.ai/) — `liquid/lfm-2.5-embedding-350m:free` (1 024 dims) |
| Vector Database  | PostgreSQL 16 + [pgvector](https://github.com/pgvector/pgvector)          |
| Vector Index     | IVFFlat with cosine distance (`vector_cosine_ops`, 100 lists)             |
| DB Driver        | `psycopg2` + `pgvector` Python package                                   |
| Containerization | Docker Compose                                                            |
| Config           | `python-dotenv` (`.env` file, no secrets in repo)                         |

---

## Reviewer Reproduction

A reviewer can reproduce the full pipeline with the following commands:

```bash
# 1. Clone and enter the project
git clone https://github.com/Moataz-hindy/Football-Analysis-RAG.git
cd Football-Analysis-RAG

# 2. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# Edit .env with your real API key and database password

# 5. Start PostgreSQL
docker-compose up -d

# 6. Run the data pipeline
python src/ingestion/collect.py      # Step 1: Collect raw data (80+ pages)
python src/ingestion/clean.py        # Step 2: Clean HTML → plain text
python src/rag/process_all.py        # Step 3: Chunk & embed documents
python src/rag/ingest.py             # Step 4: Load into PostgreSQL

# 7. Run retrieval
python src/rag/search.py "What is expected goals (xG)?"

# 8. Run evaluation
python src/rag/evaluate.py
```
