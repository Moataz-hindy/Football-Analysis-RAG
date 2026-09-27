---
title: Football Analysis RAG
emoji: ⚽
colorFrom: green
colorTo: indigo
sdk: docker
app_port: 8000
---

# Football Analysis RAG — Multi-Agent Deliberation & Intelligence Platform

A **multi-agent football intelligence and dialectical deliberation platform**. The system ingests professional football domain knowledge, orchestrates multi-agent tactical debates along strongly-connected passing graphs, tracks real-time opinion trajectories, calculates counterfactual causal influence, and serves an interactive **Touchline Intelligence** multi-page web application.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Week-by-Week Summary](#week-by-week-summary)
- [Touchline Intelligence Platform (Week 5)](#touchline-intelligence-platform-week-5)
- [Configurable Agent Rosters (2–6 Agents)](#configurable-agent-rosters-26-agents)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Setup & Installation](#setup--installation)
- [Running the Platform](#running-the-platform)
- [Analytics & Reporting](#analytics--reporting)
- [API Reference](#api-reference)
- [Testing](#testing)
- [Design Decisions](#design-decisions)
- [Historical Turn Latencies](#historical-turn-latencies)
- [Tech Stack](#tech-stack)
- [Documentation Index](#documentation-index)

---

## Overview

The platform spans five integrated layers:

```text
Week 1: Knowledge Infrastructure (PostgreSQL 16 + pgvector / SQLite Fallback)
         │
         ▼
Week 2: Intelligent Persona Agents (6 Specialists, Tool Registry, VADER)
         │
         ▼
Week 3: Multi-Agent Dialectical Deliberation (NetworkX Routing, 2-6 Agents)
         │
         ▼
Week 4: Analytics & Intelligence Layer (Stance, Agreement, Causal Ablation)
         │
         ▼
Week 5: Touchline Intelligence Platform (FastAPI + Vite/React Multi-Page App)
```

The end-to-end deliberation and analytics workflow:

```text
Football Web Sources ──▶ RAG Embeddings (1024-D) ──▶ Persona Agents (2 to 6)
                                                               │
                                                               ▼
Live Arena Stepper ◀── Turn Checkpoints ◀── NetworkX Graph Deliberation
        │                                                      │
        ▼                                                      ▼
Interactive Pitch                                   ┌───────────────────────┐
Passing Routes                                      │   Analytics Engine    │
                                                    ├───────────────────────┤
                                                    │ Stance Trajectories   │
                                                    │ Consensus Tracking    │
                                                    │ Causal Influence (τ)  │
                                                    │ Executive Synthesis   │
                                                    └───────────┬───────────┘
                                                                ▼
                                                    Intelligence Dashboard
                                                     (/intel & REST API)
```

---

## Architecture

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Week 1: Knowledge Layer                            │
│                                                                             │
│  Web Sources ──▶ Collector ──▶ Cleaner ──▶ Chunker & Embedder ──▶ Database │
│  (80+ URLs)     collect.py    clean.py    process_all.py        Postgres/   │
│                                                                 pgvector    │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ vector search (cosine distance)
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                       Week 2: Agent Layer                                   │
│                                                                             │
│  Specialist Personas (YAML-defined)                                        │
│  ├── LLM Adapter (OpenAI-compatible, Cerebras qwen-3.8-27b)                │
│  ├── Conversation Memory with sliding-window summarization                  │
│  ├── RAG Retrieval (KnowledgeSearchTool) & WebSearchTool (Tavily)          │
│  ├── CalculatorTool for mathematical & metric validation                    │
│  └── VADER Lexicon Sentiment Scorer                                         │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                     Week 3: Discussion Layer                                │
│                                                                             │
│  Discussion Orchestrator (src/discussion/orchestrator.py)                   │
│  ├── Graph Message Routing (NetworkX ring + chord topology)                │
│  ├── Multi-Round Discussions (Opening statements + N rounds)                │
│  ├── Configurable Rosters: 2, 3, 4, 5, or 6 Specialist Agents              │
│  ├── Turn-by-Turn Checkpointing to outputs/{id}.json                       │
│  └── In-Flight Memory Tracking for live status inspection                   │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                     Week 4: Analytics Layer                                 │
│                                                                             │
│  Analytics Engine (src/analytics/engine.py)                                │
│  ├── Task 1: Stance Trajectories & Shift Detection (stance.py)              │
│  ├── Task 2: Pairwise Consensus Agreement (agreement.py)                   │
│  ├── Task 3: Counterfactual Causal Ablation (causal_influence.py)          │
│  ├── Task 4: Message Sentiment Distribution (sentiment.py)                  │
│  ├── Task 5: Pearson Correlation Influence (correlation_influence.py)       │
│  └── LLM Executive Synthesis & Tactical Narrative (synthesis.py)            │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                  Week 5: Application & Platform Layer                       │
│                                                                             │
│  FastAPI Backend (:8000)                                                    │
│  ├── Multi-Tenant SQLite/PostgreSQL Database (Tenant Profiles & Personas)   │
│  ├── Discussion Worker Pool with Queue Depth Limiting & Graceful Shutdown   │
│  ├── Trailing-Comma Middleware & Path Traversal Sanitizers                  │
│  └── REST Endpoints: /discussions, /analytics, /auth, /profile, /personas   │
│                                                                             │
│  Vite + React 18 Multi-Page Frontend (:5173 / :3000 / /app)                 │
│  ├── Deep-Linkable Routes: /arena, /history, /intel, /devops                │
│  ├── Real-Time Streaming Transcript with Live-Edge Auto-Follow              │
│  ├── Interactive Tactical Pitch & Passing Graph Visualizer                  │
│  ├── Configurable Deliberation Stepper (Rounds & Agents Selector)           │
│  └── Claude Nocturne Design System (Glassmorphic Dark Mode)                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Week-by-Week Summary

### Week 1 — Knowledge Infrastructure
- **Collected** 80+ football web resources (IFAB Laws of the Game, tactical guides, World Cup match reports).
- **Cleaned** raw HTML to structured text with boilerplate stripping and character normalisation.
- **Chunked & embedded** documents (1,200 chars with 200-char overlap) producing 1,024-dimensional vectors.
- **Ingested** into PostgreSQL 16 + pgvector with cosine similarity indexing.
- **Evaluated** with retrieval benchmarks (Precision@5, Recall@5, MRR) across curated tactical queries.

### Week 2 — Intelligent Agents
- **6 specialist personas** defined in YAML: Tactical Analyst, Statistical Analyst, Fan Voice, Refereeing Analyst, Performance Analyst, and Historical Context Analyst.
- **Unified LLM adapter** speaking the OpenAI wire protocol, supporting Cerebras, Groq, OpenRouter, and local endpoints.
- **Conversation memory** with sliding windows and automatic summarisation.
- **Tool system**: `KnowledgeSearchTool` (RAG vector database), `CalculatorTool`, and `WebSearchTool` (Tavily).
- **VADER sentiment** scoring per turn.

### Week 3 — Multi-Agent Discussion System
- **NetworkX graph routing** directing messages between opposing and complementary analyst roles.
- **Multi-round debates** proceeding from initial opening statements through iterative peer critique rounds.
- **Live checkpointing** saving debate state to disk immediately after each agent turn.
- **Opinion evolution tracking** recording stance movements and change rationales.
- **Graceful degradation** enabling offline discussions when vector databases are unavailable.

### Week 4 — Analytics & Intelligence Layer
- **Opinion Trajectories**: Numeric stance scoring `[-1.0, +1.0]` with fast-fail local embedding fallbacks.
- **Consensus Agreement**: Pairwise discussion agreement score `A = 1 - D_mean / 2`.
- **Causal Influence Ablation**: Counterfactual exchange ablation calculating each agent's true persuasive power ($\tau$).
- **Sentiment Profiling**: Distribution of sentiment shifts across debate rounds.
- **Executive Synthesis**: Automated LLM tactical narrative and peer critique summaries.
- **Fabrication-Free Honesty**: Unscored or offline items remain honest `null` rather than generating synthetic heuristic data.

### Week 5 — Touchline Intelligence Platform
- **FastAPI REST API**: Asynchronous backend managing discussion worker queues, analytics caching, and platform authentication.
- **Vite + React 18 Frontend**: Futuristic glassmorphic tactical interface built on Claude Nocturne design principles.
- **Multi-Page HTML Architecture**: Deep-linkable independent HTML entry points (`/arena`, `/history`, `/intel`, `/devops`).
- **Live Stream Deliberation**: Real-time transcript streaming onto the pitch and dialogue stream without full-page reloads.
- **Configurable Agent Roster**: On-demand selection of 2 to 6 agents with dynamic strongly-connected topologies.
- **Multi-Tenant Scouting Profiles**: Role-based profiles (Scout, Head Coach, Tactical Analyst) with custom persona managers.

---

## Touchline Intelligence Platform (Week 5)

The frontend application provides four distinct operational views:

| View | Path | Description |
| :--- | :--- | :--- |
| **Landing** | `/` | Animated hero pitch simulating live passing routes, metric badges, and quick demo onboarding. |
| **Arena** | `/arena` | Main deliberation deck. Select debate topic, round count (2–5), and agent roster (2–6). Watch turns stream live. |
| **History** | `/history` | Catalog of past deliberations with live status badges (`Queued in Worker`, `Deliberating Live`, `Watch Live`, `Resume / Replay`). |
| **Intelligence**| `/intel` | Analytical command center. Displays consensus charts, stance trajectory lines, causal persuasion scores, and tactical synthesis. |
| **DevOps** | `/devops` | Platform telemetry, database status, API health, active CORS origins, and worker queue depths. |

---

## Configurable Agent Rosters (2–6 Agents)

Users can scale deliberations from focused 1v1 tactical clashes up to full 6-agent panel debates:

| Preset | Agent Count | Participating Personas | Graph Topology |
| :--- | :---: | :--- | :--- |
| **Head-to-Head** | **2** | Tactical Analyst, Statistical Analyst | Bidirectional 2-node clash |
| **Triad** | **3** | Tactical, Statistical, Performance | Bidirectional triangle with cross-chords |
| **Tactical Box** | **4** | Tactical, Statistical, Performance, Context | 4-node ring with opposing diagonals |
| **Pentagram** | **5** | Tactical, Statistical, Performance, Context, Refereeing | 5-node ring with cross-thematic bridges |
| **Full Pitch 3v3**| **6** | All 6 specialist personas | Symmetrical cross-camp debate network |

Every generated subgraph is mathematically guaranteed to be **strongly connected** (`nx.is_strongly_connected(graph)`), ensuring complete dialectical propagation across all rounds.

---

## Project Structure

```text
Football-Analysis-RAG/
├── frontend/                   # Week 5: Touchline Intelligence React App
│   ├── src/
│   │   ├── components/         # UI views, pitch visualizers, modals
│   │   │   ├── AgentCommunicationPitch.jsx  # Interactive passing pitch graph
│   │   │   ├── LandingPage.jsx              # Hero landing page
│   │   │   ├── MarkdownPreview.jsx          # Compiled markdown renderer
│   │   │   ├── SpeechCard.jsx               # Dialectical speech bubble
│   │   │   ├── HistoryView.jsx              # History cards with status badges
│   │   │   ├── AuthModal.jsx                # Multi-tenant authentication
│   │   │   └── ProfileModal.jsx             # Scouting persona configuration
│   │   ├── App.jsx             # Core application shell & live streaming logic
│   │   └── index.css           # Claude Nocturne CSS design system
│   ├── arena.html              # Multi-page entry point: Arena view
│   ├── history.html            # Multi-page entry point: History view
│   ├── intel.html              # Multi-page entry point: Intelligence view
│   ├── devops.html             # Multi-page entry point: DevOps view
│   ├── index.html              # Multi-page entry point: Landing view
│   ├── vite.config.js          # Multi-page rollup configuration & dev proxy
│   └── package.json
│
├── src/
│   ├── api/                    # Week 5: FastAPI REST Backend
│   │   ├── main.py             # Server lifecycle, middleware, routing
│   │   ├── routes.py           # Core discussion & analytics endpoints
│   │   ├── platform_routes.py  # Auth, profile, and persona endpoints
│   │   ├── schemas.py          # Pydantic request & response models
│   │   └── services/
│   │       ├── discussion_service.py # Worker pool & in-flight tracking
│   │       └── analytics_service.py  # Cached analytics orchestration
│   │
│   ├── platform/               # Week 5: Multi-Tenant Platform Engine
│   │   ├── db.py               # SQLite fallback & PostgreSQL connection
│   │   ├── auth.py             # Session token & tenant verification
│   │   ├── profile.py          # Scout/Coach persona preferences
│   │   └── models.py           # Platform SQL database models
│   │
│   ├── discussion/             # Week 3: Deliberation Orchestrator
│   │   ├── orchestrator.py     # Multi-round debate orchestration
│   │   ├── graph.py            # Symmetrical & dynamic NetworkX graphs
│   │   ├── router.py           # Stateless graph message router
│   │   ├── persistence.py      # Discussion serialization & checkpoints
│   │   └── run_discussion.py   # CLI debate runner with --agents support
│   │
│   ├── agent/                  # Week 2: Intelligent Agents
│   │   ├── agent.py            # Core Agent implementation & tool loop
│   │   ├── llm.py              # OpenAI-compatible client with pace budgets
│   │   ├── memory.py           # Context management & summarisation
│   │   ├── retrieval.py        # Knowledge base retrieval adapter
│   │   └── persona_loader.py   # YAML persona specification loader
│   │
│   ├── analytics/              # Week 4: Analytics Engine
│   │   ├── engine.py           # Unified analytics coordinator
│   │   ├── stance.py           # Numeric stance projection & honest nulls
│   │   ├── agreement.py        # Pairwise consensus metric calculation
│   │   ├── causal_influence.py # Counterfactual causal ablation scorer
│   │   └── synthesis.py        # LLM tactical executive narrative
│   │
│   ├── tools/                  # Agent tools (Calculator, WebSearch, RAG)
│   ├── rag/                    # Week 1: Knowledge vector pipeline
│   └── ingestion/              # Week 1: Scraping & cleaning tools
│
├── sql/migrations/             # Multi-tenant SQL migrations
├── personas/                   # Specialist YAML persona files
├── outputs/                    # Persisted deliberation JSON records
├── reports/                    # Generated charts & cached analytics
└── tests/                      # Pytest suite
```

---

## Prerequisites

- **Python 3.10+**
- **Node.js 18+** & **npm**
- **PostgreSQL 16** with `pgvector` *(optional: system automatically falls back to embedded SQLite if unavailable)*
- An **OpenAI-compatible LLM endpoint** (e.g. [Cerebras](https://cerebras.ai/) using `qwen-3.8-27b`, Groq, or OpenRouter)

---

## Setup & Installation

### 1. Clone & Python Environment

```bash
git clone https://github.com/Moataz-hindy/Football-Analysis-RAG.git
cd Football-Analysis-RAG

python -m venv .venv
source .venv/bin/activate       # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment (`.env`)

Create or update `.env` in the repository root:

```ini
# LLM Provider (Cerebras fast inference recommended)
LLM_API_KEY=your_cerebras_or_openai_key
LLM_BASE_URL=https://api.cerebras.ai/v1
LLM_MODEL=qwen-3.8-27b
LLM_TEMPERATURE=0.2

# Request pacing and retry budgets
LLM_RETRY_MAX_WAIT_SECONDS=120
LLM_MAX_RETRIES=2
LLM_PACER_MAX_PER_MINUTE=20
LLM_PACER_MAX_PER_HOUR=300

# Optional Web Search
TAVILY_API_KEY=your_tavily_key

# Optional Vector Database (PostgreSQL)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=football_intelligence
DB_USER=postgres
DB_PASSWORD=your_password
```

### 3. Frontend Setup

```bash
cd frontend
npm install
npm run build
cd ..
```

---

## Running the Platform

### Option A: Complete Web Experience (Recommended)

Start the FastAPI backend and the Vite development server in two separate terminals:

**Terminal 1 — Backend API:**
```bash
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

**Terminal 2 — Frontend Application:**
```bash
cd frontend
npm run dev
```

Open **`http://localhost:5173/`** in your browser to command deliberations, stream live messages, and view intelligence metrics.

### Option B: Standalone Production API Serving

The backend directly serves the compiled frontend bundle at `/app`:

```bash
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```
Visit **`http://localhost:8000/app`** for the frontend, or **`http://localhost:8000/docs`** for interactive Swagger API documentation.

### Option C: CLI Discussion Runner

Run a debate directly from the terminal with custom rounds and agent counts:

```bash
# 2-Agent Head-to-Head Debate (2 Rounds)
python -m src.discussion.run_discussion \
  --topic "Evaluate Argentina's defensive transition against France in the 2022 Final" \
  --rounds 2 \
  --agents 2 \
  --discussion-id "arg-fra-2p"

# Full 6-Agent Symmetrical Debate
python -m src.discussion.run_discussion \
  --topic "Did Japan's 5-4-1 low block expose Spain's central progression limits?" \
  --rounds 3 \
  --agents 6
```

---

## Analytics & Reporting

Compute multi-dimensional analytics for any completed deliberation:

```bash
python -m src.analytics.run_analytics \
  --input outputs/arg-fra-2p.json \
  --output-dir reports \
  --use-embeddings
```

### Analytics Output:
1. **Opinion Trajectories**: Sequential numeric stance changes across rounds.
2. **Agreement Matrix**: Pairwise consensus distance over time.
3. **Counterfactual Causal Ablation**: Quantified persuasion score ($\tau$) assessing how much each analyst moved peer opinions.
4. **Sentiment Breakdown**: VADER sentiment distribution per agent and round.
5. **Visual Charts**: Matplotlib-generated stance trajectory curves and weighted network graphs.

---

## API Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Server heartbeat and database connectivity check. |
| `GET` | `/topics` | Curated tactical football debate topics. |
| `POST` | `/discussions` | Launch a debate (`topic`, `num_rounds`, `num_agents`, optional `discussion_id`). |
| `GET` | `/discussions` | List all saved and in-flight discussions with live status. |
| `GET` | `/discussions/{id}` | Retrieve complete transcript and configuration for a deliberation. |
| `GET` | `/discussions/{id}/status` | Poll runtime execution progress (`queued`, `running`, `completed`). |
| `GET` | `/discussions/{id}/analytics` | Compute or load cached stance trajectories, agreement, and influence. |
| `POST`| `/discussions/{id}/causal-analysis` | Execute counterfactual exchange ablation to score true causal impact. |
| `POST`| `/auth/login` | Multi-tenant scout/coach authentication. |
| `GET` | `/profile` | Active user tactical preferences and personal scouting dossier. |
| `POST`| `/personas` | Create and customize dynamic analyst personas. |

---

## Testing

Execute the comprehensive offline test suite:

```bash
# Run test suite
python -m pytest tests/ -q

# Run platform multi-tenant tests
python -m pytest tests/test_platform.py -v
```

---

## Design Decisions

| Subsystem | Decision | Technical Rationale |
| :--- | :--- | :--- |
| **Inference Engine** | Cerebras `qwen-3.8-27b` | Sub-2s generation latency per turn with complete function/tool calling support. |
| **Worker Queue** | Deeper Semaphore Pool | Allows up to 4 queued deliberations without returning immediate `503` errors. |
| **Pacing & Backoffs** | Bounded 10s Retry Clamp | Prevents rate-limit freezes from holding background workers for tens of minutes. |
| **Graph Topology** | Ring with Cross-Chords | Guarantees strong connectivity for 2, 3, 4, 5, or 6 agents dynamically. |
| **Live Streaming** | Incremental Ref Tracking | Eliminates full-page reload requirements by streaming new checkpointed turns directly into DOM. |
| **Data Integrity** | Honest Null Stances | Deletes synthetic heuristic curves; unclassified stances remain honestly `null`. |
| **Database Storage** | SQLite Automatic Fallback | Seamless offline operation when PostgreSQL/pgvector Docker services are stopped. |

---

## Historical Turn Latencies

Observed turn latencies recorded across benchmark debate sessions:

- **Unthrottled Cerebras `qwen-3.8-27b`**: **~5s – 12s per turn** (a full 2-round debate completes in under 40 seconds).
- **Normal API Window (Standard Load)**: **~25s – 50s per turn**.
- **Throttled Window (Daily Quota Backoff)**: **~120s – 400s per turn** (handled automatically via exponential backoff ladders).

---

## Tech Stack

- **Backend**: FastAPI, Uvicorn, Python 3.10+, Pydantic v2
- **Agent Architecture**: Custom Multi-Agent Framework, NetworkX Graph Routing
- **AI / LLM**: OpenAI-compatible REST API (Cerebras `qwen-3.8-27b` / OpenRouter)
- **Frontend**: React 18, Vite, Tailwind CSS, Phosphor Icons, Marked.js
- **Database**: PostgreSQL 16 + pgvector (Semantic Embeddings), SQLite 3 (Fallback Platform DB)
- **Analytics**: Sentence-Transformers (`all-MiniLM-L6-v2`), NumPy, SciPy, VADER
- **Visualization**: Matplotlib (Agg headless engine), HTML5 Canvas Tactical Pitch

---

## Documentation Index

| Document | Description |
| :--- | :--- |
| [`frontend/README.md`](frontend/README.md) | Frontend architecture, component hierarchy, and build instructions. |
| [`docs/week4_analytics_guide.md`](docs/week4_analytics_guide.md) | Mathematical formulas and algorithms for stance, agreement, and causal ablation. |
| [`docs/discussion_architecture.md`](docs/discussion_architecture.md) | Multi-round debate orchestration mechanics. |
| [`docs/graph_and_routing.md`](docs/graph_and_routing.md) | Communication graph theory and reciprocal edge definitions. |
| [`docs/sentiment_and_analytics.md`](docs/sentiment_and_analytics.md) | VADER sentiment scoring integration. |
| [`docs/evaluation.md`](docs/evaluation.md) | Information retrieval benchmark and precision/recall evaluation. |
