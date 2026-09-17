# Football Analysis RAG — Multi-Agent Discussion & Analytics Platform

A **multi-agent discussion and analytics platform** built around football (soccer). The system ingests football knowledge, deploys persona-driven AI agents to debate football topics, and analyses the resulting discussions with measurable opinion dynamics, influence metrics, and automated reporting.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Week-by-Week Summary](#week-by-week-summary)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Setup & Installation](#setup--installation)
- [Running the Full Pipeline](#running-the-full-pipeline)
- [Analytics & Reporting (Week 4)](#analytics--reporting-week-4)
- [Testing](#testing)
- [Design Decisions](#design-decisions)
- [Known Limitations](#known-limitations)
- [Tech Stack](#tech-stack)
- [Documentation Index](#documentation-index)

---

## Overview

This project was built across four development weeks, each adding a new layer:

```text
Week 1: Knowledge Infrastructure
         │
         ▼
Week 2: Intelligent Agents
         │
         ▼
Week 3: Multi-Agent Discussion System
         │
         ▼
Week 4: Analytics & Intelligence Layer
         │
         ▼
Week 5: Dashboard (upcoming)
```

The end-to-end flow is:

```text
Web Pages ──▶ RAG Knowledge Base ──▶ 6 Persona Agents ──▶ Multi-Round Discussion
                                                                    │
                                                                    ▼
                                                        ┌───────────────────────┐
                                                        │   Analytics Engine    │
                                                        ├───────────────────────┤
                                                        │ Opinion Trajectories  │
                                                        │ Agreement Scores      │
                                                        │ Influence Metrics     │
                                                        │ Sentiment Analysis    │
                                                        └───────────┬───────────┘
                                                                    │
                                                          ┌─────────┴─────────┐
                                                          ▼                   ▼
                                                    Auto Report         Visualizations
                                                     (.md)          (trajectory + graph)
```

---

## Architecture

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Week 1: Knowledge Layer                            │
│                                                                             │
│  Web Pages ──▶ Collector ──▶ Cleaner ──▶ Chunker & Embedder ──▶ PostgreSQL │
│  (80+ URLs)   collect.py    clean.py    process_all.py          + pgvector  │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ vector search
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                       Week 2: Agent Layer                                   │
│                                                                             │
│  6 Persona Agents (YAML-defined)                                           │
│  ├── LLM Adapter (OpenAI-compatible)                                       │
│  ├── Conversation Memory                                                   │
│  ├── RAG Retrieval (KnowledgeSearchTool)                                   │
│  ├── Tool Registry (Calculator, Web Search)                                │
│  └── VADER Sentiment Scorer                                                │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                     Week 3: Discussion Layer                                │
│                                                                             │
│  Discussion Orchestrator                                                   │
│  ├── Graph-Based Message Routing (NetworkX)                                │
│  ├── Multi-Round Discussions (initial opinions + N rounds)                  │
│  ├── Per-Agent Opinion Evolution Tracking                                  │
│  └── Persistent Discussion Records (outputs/*.json)                        │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                     Week 4: Analytics Layer                                 │
│                                                                             │
│  Analytics Engine (src/analytics/engine.py)                                │
│  ├── Task 1: Stance Trajectories & Opinion Change (stance.py)              │
│  ├── Task 2: Pairwise Agreement Scoring (agreement.py)                     │
│  ├── Task 3: Distance-Reduction Influence (influence.py)                   │
│  ├── Task 4: VADER Sentiment per Message (sentiment.py)                    │
│  ├── Task 5: Correlation-Based Influence (correlation_influence.py)        │
│  ├── Data Validation (validation.py)                                       │
│  ├── Opinion Trajectory Chart (visualization/opinion_trajectory.py)        │
│  ├── Interaction Graph (visualization/interaction_graph.py)                │
│  └── Markdown Report Generator (reporting/report.py)                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Week-by-Week Summary

### Week 1 — Knowledge Infrastructure

Built the RAG (Retrieval-Augmented Generation) pipeline:

- **Collected** 80+ football web pages (IFAB laws, analytics explainers, tactical guides, World Cup match reports)
- **Cleaned** HTML to plain text with noise removal and mojibake repair
- **Chunked & embedded** documents (1,200 chars, 200-char overlap) using OpenRouter embeddings (1,024 dims)
- **Ingested** into PostgreSQL 16 + pgvector with IVFFlat cosine index
- **Search** via cosine similarity returns top-k relevant chunks
- **Evaluated** with 7-query benchmark (Precision@5, Recall@5, MRR)

### Week 2 — Intelligent Agents

Built persona-driven AI agents:

- **6 specialist personas** defined in YAML: Tactical, Statistical, Fan, Refereeing, Performance, Context analysts
- **LLM adapter** supporting OpenAI-compatible APIs (OpenRouter, local models)
- **Conversation memory** with sliding window and context management
- **Tool system**: KnowledgeSearchTool (Week 1 RAG), CalculatorTool, WebSearchTool
- **VADER sentiment** scoring on every agent message

### Week 3 — Multi-Agent Discussion System

Built the discussion orchestrator:

- **Graph-based routing** — agents communicate along a predefined NetworkX graph
- **Multi-round discussions** — initial opinions → N discussion rounds with routed messages
- **Opinion evolution** — tracks stance changes with `changed_from_previous` flag and `change_reason`
- **Mid-discussion retrieval** — agents query the Week 1 knowledge base during discussions
- **Persistent records** — full discussion history saved as `outputs/{discussion_id}.json`
- **Reproducible runs** — reload any discussion by ID for inspection or analytics

### Week 4 — Analytics & Intelligence Layer

Built the analytics engine on top of Week 3 discussions:

| Component | Description | Module |
|-----------|-------------|--------|
| **Opinion Change** | Per-agent, per-round numeric stance [-1, +1] with 3-tier scoring (rules/embeddings/LLM) | `src/analytics/stance.py` |
| **Agreement** | Per-round pairwise agreement score: `A = 1 - D_mean/2` | `src/analytics/agreement.py` |
| **Influence** | Distance-reduction metric + Pearson correlation-based influence | `src/analytics/influence.py`, `correlation_influence.py` |
| **Sentiment** | Per-message VADER compound scores with label counts | `src/analytics/sentiment.py` |
| **Unified Engine** | Single entry point returning all 4 categories | `src/analytics/engine.py` |
| **Data Validation** | Pre-analytics validation of discussion structure | `src/analytics/validation.py` |
| **Opinion Trajectory** | Multi-agent stance chart (matplotlib) | `src/visualization/opinion_trajectory.py` |
| **Interaction Graph** | Weighted directed agent network (networkx + matplotlib) | `src/visualization/interaction_graph.py` |
| **Report Generator** | Auto Markdown report with all 4 metrics + findings | `src/reporting/report.py` |

---

## Project Structure

```
Football-Analysis-RAG/
├── data/
│   ├── raw/                    # Scraped HTML documents (JSON) — 83 files
│   ├── clean/                  # Cleaned plain-text documents (JSON) — 81 files
│   └── embeddings/             # Chunks with vector embeddings (JSON) — 81 files
│
├── docs/                       # Architecture & metric documentation
│   ├── week4_analytics_guide.md    # Full analytics formulas & API reference
│   ├── week4_tasks_1_2_3.md        # Task implementation details
│   ├── discussion_architecture.md  # Week 3 orchestrator design
│   ├── graph_and_routing.md        # Message routing documentation
│   ├── sentiment_and_analytics.md  # Sentiment integration notes
│   └── evaluation.md              # Week 1 retrieval evaluation
│
├── personas/                   # Agent persona definitions (YAML)
│   ├── tactical_analyst.yaml
│   ├── statistical_analyst.yaml
│   ├── fan_analyst.yaml
│   ├── refereeing_analyst.yaml
│   ├── performance_analyst.yaml
│   └── context_analyst.yaml
│
├── src/
│   ├── ingestion/              # Week 1: Web scraping & cleaning
│   │   ├── collect.py
│   │   └── clean.py
│   │
│   ├── rag/                    # Week 1: RAG pipeline
│   │   ├── process_all.py      # Chunking & embedding
│   │   ├── ingest.py           # PostgreSQL ingestion
│   │   ├── search.py           # Vector similarity search
│   │   └── evaluate.py         # Retrieval benchmark
│   │
│   ├── agent/                  # Week 2: Intelligent agents
│   │   ├── agent.py            # Core Agent class
│   │   ├── llm.py              # OpenAI-compatible LLM adapter
│   │   ├── memory.py           # Conversation memory
│   │   ├── persona.py          # Persona dataclass
│   │   ├── persona_loader.py   # YAML persona loader
│   │   ├── retrieval.py        # RAG retrieval interface
│   │   ├── sentiment.py        # VADER sentiment scorer
│   │   ├── tool_registery.py   # Tool registry
│   │   └── types.py            # Agent response types
│   │
│   ├── tools/                  # Week 2: Agent tools
│   │   ├── calculator.py
│   │   ├── knowledge_search.py # Week 1 RAG integration
│   │   └── web_search.py
│   │
│   ├── discussion/             # Week 3: Discussion system
│   │   ├── orchestrator.py     # Multi-round discussion orchestrator
│   │   ├── graph.py            # Agent communication graph
│   │   ├── router.py           # Graph-based message router
│   │   ├── persistence.py      # Discussion save/load (JSON)
│   │   ├── run_discussion.py   # CLI to run a discussion
│   │   ├── types.py            # DiscussionResult, OpinionSnapshot, etc.
│   │   └── models.py           # Discussion data models
│   │
│   ├── analytics/              # Week 4: Analytics engine
│   │   ├── engine.py           # Unified AnalyticsEngine class
│   │   ├── stance.py           # 3-tier stance scoring
│   │   ├── agreement.py        # Pairwise agreement metric
│   │   ├── influence.py        # Distance-reduction influence
│   │   ├── correlation_influence.py  # Pearson correlation influence
│   │   ├── sentiment.py        # Discussion sentiment analysis
│   │   ├── validation.py       # Input data validation
│   │   ├── models.py           # Pydantic analytics models
│   │   └── run_analytics.py    # CLI analytics pipeline
│   │
│   ├── visualization/          # Week 4: Charts & graphs
│   │   ├── opinion_trajectory.py   # Multi-agent stance trajectory chart
│   │   └── interaction_graph.py    # Weighted agent interaction network
│   │
│   └── reporting/              # Week 4: Report generation
│       └── report.py           # Automatic Markdown report
│
├── tests/                      # Test suite (20 test files)
├── reports/                    # Generated reports & visualizations
├── outputs/                    # Saved discussion JSON files
├── scripts/                    # Utility & manual test scripts
├── sql/                        # PostgreSQL schema (init_db.sql)
│
├── requirements.txt            # Python dependencies
├── requirements-analytics-embeddings.txt  # Optional: sentence-transformers
├── docker-compose.yml          # PostgreSQL + pgvector container
├── .env.example                # Environment variable template
├── week2.md                    # Week 2 specification
├── week3.md                    # Week 3 specification
└── week4.md                    # Week 4 specification
```

---

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| **Python** | 3.10+ | Run all scripts |
| **Docker** | 20+ | Host PostgreSQL + pgvector |
| **Docker Compose** | v2+ | Spin up the database container |
| **OpenRouter API Key** | — | LLM calls & embeddings |

---

## Setup & Installation

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
# Edit .env with your API key and database credentials

# 5. Start PostgreSQL + pgvector
docker-compose up -d
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DB_HOST` | Database host | `localhost` |
| `DB_PORT` | Database port | `5432` |
| `DB_NAME` | Database name | `football_intelligence` |
| `DB_USER` | Database user | `postgres` |
| `DB_PASSWORD` | Database password | — |
| `OPENAI_API_KEY` | OpenRouter API key | — |
| `OPENROUTER_MODEL` | Embedding model | `liquid/lfm-2.5-embedding-350m:free` |
| `LLM_MODEL` | Chat model for agents | — |
| `LLM_TEMPERATURE` | LLM temperature | `0.7` |

---

## Running the Full Pipeline

### Step 1 — Build the Knowledge Base (Week 1)

```bash
python src/ingestion/collect.py      # Scrape 80+ football web pages
python src/ingestion/clean.py        # Clean HTML to plain text
python -m src.rag.process_all        # Chunk & embed documents
python -m src.rag.ingest             # Load into PostgreSQL
```

### Step 2 — Search the Knowledge Base

```bash
python src/rag/search.py "What is expected goals (xG)?"
```

### Step 3 — Run a Multi-Agent Discussion (Week 3)

```bash
# Run a full 6-agent, 3-round discussion
python -m src.discussion.run_discussion

# Or with a custom topic and ID
python -m src.discussion.run_discussion \
  --topic "Was Argentina the better team in the 2022 World Cup final?" \
  --discussion-id my_run_01 \
  --rounds 3
```

The discussion is saved to `outputs/{discussion_id}.json`.

### Step 4 — Run Analytics (Week 4)

```bash
# Run the full analytics pipeline on a saved discussion
python -m src.analytics.run_analytics outputs/{discussion_id}.json

# With visualizations and report
python -m src.analytics.run_analytics outputs/{discussion_id}.json \
  --generate-charts \
  --generate-report

# With LLM-based stance scoring (requires API key)
python -m src.analytics.run_analytics outputs/{discussion_id}.json \
  --use-llm \
  --generate-charts \
  --generate-report
```

### Step 5 — Re-inspect a Discussion

```bash
python -c "
from src.discussion import load_discussion_by_id
r = load_discussion_by_id('my_run_01')
print(r.config.topic, len(r.messages), 'messages')
"
```

---

## Analytics & Reporting (Week 4)

### Analytics Engine

The unified analytics engine processes a saved discussion and returns all four metric categories:

```python
from src.analytics.engine import AnalyticsEngine
from src.discussion.persistence import load_discussion

engine = AnalyticsEngine(reports_dir="reports")
discussion = load_discussion("outputs/my_run_01.json")

result = engine.analyze(
    discussion,
    generate_charts=True,
    generate_report=True,
)

# Access individual results
print(result["task1_opinion_trajectories"])  # Per-agent stance series
print(result["task2_agreement"])             # Per-round agreement scores
print(result["task3_influence"])             # Per-agent influence scores
print(result["task4_sentiment"])             # Per-message sentiment
```

### Metric Definitions

| Metric | Formula | Range | Interpretation |
|--------|---------|-------|----------------|
| **Stance** | Text-to-numeric scoring (rules/embeddings/LLM) | [-1.0, +1.0] | +1 = positive pole, -1 = negative pole |
| **Opinion Change** | `S(r) - S(r-1)` | [-2.0, +2.0] | Direction & magnitude of shift |
| **Agreement** | `A = 1 - D_mean / 2` | [0.0, 1.0] | 1.0 = perfect consensus, 0.0 = total polarization |
| **Influence** | Distance-reduction pull metric | varies | Higher = stronger estimated influence |
| **Correlation Influence** | Pearson r between messages and stance changes | [-1.0, +1.0] | Association (not causation) |
| **Sentiment** | VADER compound score | [-1.0, +1.0] | Positive/neutral/negative tone |

### Generated Outputs

```
reports/
├── discussion_report_{id}.md           # Markdown report with all 4 metrics
├── opinion_trajectory_{id}.png         # Multi-agent stance chart
└── interaction_graph_{id}.png          # Weighted agent network graph
```

### Opinion Trajectory Chart

Shows each agent's numeric stance across discussion rounds:

- X-axis: discussion rounds
- Y-axis: stance score [-1, +1]
- Each agent has a distinct colour and marker
- Final stance values annotated
- Largest single-round change highlighted

### Interaction Graph

Shows the agent communication network:

- Agents as coloured nodes
- Directed edges for message routes
- Edge weights reflecting message volume
- Curved bidirectional arrows for reciprocal communication

---

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test suites
python -m pytest tests/test_acceptance_week4.py -v    # Week 4 acceptance tests
python -m pytest tests/test_opinion_visualization.py -v  # Opinion chart tests
python -m pytest tests/test_analytics_stance.py -v    # Stance scoring tests
python -m pytest tests/test_analytics_agreement.py -v # Agreement tests
python -m pytest tests/test_analytics_influence.py -v # Influence tests

# Run Week 1 evaluation
python src/rag/evaluate.py
```

### Test Coverage

| Area | Test File | Tests |
|------|-----------|-------|
| Week 4 acceptance | `test_acceptance_week4.py` | Full pipeline, reports, visualizations |
| Opinion trajectory | `test_opinion_visualization.py` | Chart generation, agents, rounds, edge cases |
| Stance scoring | `test_analytics_stance.py` | 3-tier scoring, opinion change |
| Agreement | `test_analytics_agreement.py` | Pairwise metric, per-round scores |
| Influence | `test_analytics_influence.py` | Distance-reduction, insufficient data |
| Correlation | `test_correlation_engine.py` | Pearson correlation influence |
| Sentiment | `test_sentiment_analytics_integration.py` | VADER integration |
| Discussion | `test_opinion_evolution.py` | Opinion tracking across rounds |
| Persistence | `test_persistence.py` | Save/load discussion records |
| Personas | `test_personas.py`, `test_persona_grounding.py` | Persona loading & validation |
| Reproducibility | `test_reproducible_run.py` | Discussion round-trip |
| Week 3 reliability | `test_week3_reliability.py` | Orchestrator robustness |

---

## Design Decisions

### Knowledge Layer (Week 1)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Embedding model | `liquid/lfm-2.5-embedding-350m:free` (1,024 dims) | Free tier, reasonable quality |
| Vector DB | PostgreSQL 16 + pgvector (IVFFlat) | Required by assignment, mature extension |
| Chunking | 1,200 chars, 200-char overlap | Balances context vs. granularity |
| Search | Dense cosine similarity, top-5 | Simple, effective baseline |

### Agent Layer (Week 2)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Personas | 6 YAML-defined analyst roles | Diverse perspectives on football topics |
| LLM | OpenAI-compatible adapter | Works with OpenRouter, local models |
| Sentiment | VADER (lexicon-based) | No API cost, instant scoring |
| Tools | Knowledge search + calculator + web search | RAG integration + computation |

### Discussion Layer (Week 3)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Routing | NetworkX graph | Structured agent communication |
| Persistence | JSON per discussion | Simple, portable, inspectable |
| Opinion tracking | Per-agent snapshots with change flags | Enables Week 4 analytics |

### Analytics Layer (Week 4)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Stance scoring | 3-tier: rules → embeddings → LLM | Graceful degradation without API |
| Agreement | `1 - D_mean/2` (pairwise) | Simple, interpretable [0, 1] range |
| Influence | Distance-reduction + Pearson correlation | Two complementary perspectives |
| Visualization | matplotlib (Agg backend) | No GUI needed, PNG output |

---

## Known Limitations

1. **Stance scoring without LLM** — The rules-based fallback produces `null` stances for complex opinion text. Use `--use-llm` or `--use-embeddings` for reliable numeric stances.
2. **Influence ≠ causation** — Correlation-based influence measures association, not proof that one agent caused another's opinion change.
3. **Fixed-size chunking** — Character-based splitting may cut mid-sentence. Semantic chunking would improve retrieval quality.
4. **Free-tier LLM** — Response quality and rate limits depend on the provider's free tier.
5. **No hybrid search** — Only dense vector retrieval is used; BM25 keyword search could help exact-match queries.
6. **Static corpus** — Adding new sources requires editing `collect.py` and re-running the pipeline.

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.10+ |
| Web Scraping | `requests` + `BeautifulSoup4` |
| Embeddings | OpenRouter API (`liquid/lfm-2.5-embedding-350m:free`, 1,024 dims) |
| LLM | OpenAI-compatible API (OpenRouter) |
| Vector Database | PostgreSQL 16 + pgvector (IVFFlat cosine index) |
| Agent Framework | Custom (persona + memory + tools + LLM) |
| Graph Routing | NetworkX |
| Sentiment | VADER (`vaderSentiment`) |
| Analytics Models | Pydantic v2 |
| Visualization | matplotlib |
| Data Validation | Custom validators |
| Testing | pytest |
| Config | `python-dotenv` |
| Containerization | Docker Compose |

---

## Documentation Index

| Document | Description |
|----------|-------------|
| [`docs/week4_analytics_guide.md`](docs/week4_analytics_guide.md) | Full analytics formulas, API reference, and Week 5 handoff |
| [`docs/week4_tasks_1_2_3.md`](docs/week4_tasks_1_2_3.md) | Task implementation details |
| [`docs/discussion_architecture.md`](docs/discussion_architecture.md) | Week 3 orchestrator design |
| [`docs/graph_and_routing.md`](docs/graph_and_routing.md) | Message routing documentation |
| [`docs/sentiment_and_analytics.md`](docs/sentiment_and_analytics.md) | Sentiment integration notes |
| [`docs/evaluation.md`](docs/evaluation.md) | Week 1 retrieval evaluation methodology |
| [`docs/mixed_work_integration.md`](docs/mixed_work_integration.md) | Branch integration notes |
| [`docs/manual_testing.md`](docs/manual_testing.md) | Manual testing guide |
| [`CHANGES.md`](CHANGES.md) | Full changelog |
| [`week2.md`](week2.md) | Week 2 specification |
| [`week3.md`](week3.md) | Week 3 specification |
| [`week4.md`](week4.md) | Week 4 specification |
