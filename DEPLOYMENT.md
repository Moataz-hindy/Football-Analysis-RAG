# Production & Deployment Guide

> **Football Intelligence Multi-Agent Platform**  
> *Week 5 Capstone Productization & Containerization Guide (Person 5 - DevOps)*

---

## 1. System Architecture

```text
                                USER
                                 │
                                 ▼
                     ┌───────────────────────┐
                     │    Unified Web App    │ (Port 8000)
                     │  - Frontend: /app     │
                     │  - API Docs: /docs    │
                     │  - Health:   /health  │
                     │  - REST API: /api/v1  │
                     └───────────┬───────────┘
                                 │
                 [ backend_network (Isolated Bridge) ]
                                 │
                                 ▼
                     ┌───────────────────────┐
                     │ PostgreSQL + pgvector │ (Port 5432)
                     │ (Database Tier)       │
                     └───────────────────────┘
```

The system uses a containerized architecture where:
1. **Application Tier (`api`)**: A Python 3.11-slim container running FastAPI with Uvicorn. It simultaneously serves the static frontend dashboard (`/app`), Swagger UI documentation (`/docs`), background discussion workers, analytics caching, and the REST endpoints.
2. **Database Tier (`postgres`)**: PostgreSQL 16 with `pgvector` extension for football context embeddings.
3. **Network Isolation**: The application and database communicate across a dedicated Docker bridge network (`backend_network`).
4. **Health Checks**: Integrated health monitoring at container and orchestration levels via `GET /health` and `pg_isready`.

---

## 2. Prerequisites

- **Docker & Docker Compose**: Docker Engine 24+ and Docker Compose v2+
- **Python**: 3.10, 3.11, or 3.12 (if developing without Docker)
- **API Keys**: OpenAI API Key (`OPENAI_API_KEY`) or Google Gemini API Key (`GEMINI_API_KEY`)

---

## 3. Environment Configuration

Copy the example environment file and populate your keys:
```bash
cp .env.example .env
```

### Required Variables:
| Variable | Description | Default / Example | Required? |
| :--- | :--- | :--- | :--- |
| `OPENAI_API_KEY` | OpenAI API key for agent deliberations & embeddings | `sk-...` | **Yes** |
| `DATABASE_URL` | PostgreSQL connection string with pgvector | `postgresql://postgres:postgres@postgres:5432/football_intelligence` | **Yes** |
| `DB_USER` | PostgreSQL username | `postgres` | No (default `postgres`) |
| `DB_PASSWORD` | PostgreSQL password | `postgres` | No (default `postgres`) |
| `DB_NAME` | PostgreSQL database name | `football_intelligence` | No (default `football_intelligence`) |
| `LOG_LEVEL` | Application logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`) | `INFO` | No |
| `PORT` | Web & API port | `8000` | No (default `8000`) |

---

## 4. One-Command Docker Deployment (Recommended)

To build and start the entire multi-service stack with a single command:

```bash
docker compose up --build -d
```

### Accessing the Live Services:
- **Discussion Room Frontend**: [http://localhost:8000/app](http://localhost:8000/app)
- **FastAPI Interactive Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **System Health Check**: [http://localhost:8000/health](http://localhost:8000/health)
- **PostgreSQL Database**: `localhost:5432`

### Monitoring & Operations:
```bash
# View live application logs
docker compose logs -f api

# Check container health status
docker compose ps

# Stop all services gracefully
docker compose down
```

---

## 5. Single Container Build & Run (Alternative)

To build the standalone Docker image independently (fulfills Week 5 Section 32 & 33):

```bash
# Build the Docker image
docker build -t football-intelligence .

# Run the container (with .env mounted)
docker run -p 8000:8000 --env-file .env football-intelligence
```

---

## 6. Local Development (Without Docker)

If running the application locally on your host machine:

### Step A: Start PostgreSQL with pgvector
```bash
docker compose up -d postgres
```

### Step B: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step C: Start the Unified Application
```bash
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```
Then visit:
- Frontend: `http://localhost:8000/app`
- Swagger UI: `http://localhost:8000/docs`

---

## 7. Cloud Deployment Guide (Free Tier)

### Option A: Render.com (Recommended Free Docker Web Service)
1. Push this repository to GitHub.
2. Sign in to [Render.com](https://render.com) and click **New +** $\to$ **Web Service**.
3. Connect your GitHub repository.
4. Select **Docker** as the Runtime environment.
5. In **Environment Variables**, add:
   - `OPENAI_API_KEY`: *(your secret key)*
   - `PYTHONUNBUFFERED`: `1`
6. Click **Deploy Web Service**.
7. Render provisions your application at `https://football-intelligence.onrender.com`.
8. Verify health status: `curl https://<your-render-url>/health`.
9. Access the UI at `https://<your-render-url>/app`.

### Option B: Hugging Face Spaces (Docker SDK)
1. Create a new Space on Hugging Face and choose the **Docker** SDK.
2. Connect your GitHub repository or push directly.
3. In **Settings** $\to$ **Variables and Secrets**, add `OPENAI_API_KEY`.
4. Hugging Face builds and hosts the container automatically with public HTTPS.

---

## 8. Verification & Health Monitoring

### Health Endpoint (`GET /health`)
```bash
curl -i http://localhost:8000/health
```
**Expected Response:**
```json
HTTP/1.1 200 OK
content-type: application/json

{
  "status": "ok"
}
```

### Running Test Suite
```bash
pytest tests/test_api.py tests/test_health.py -v
```

---

## 9. Troubleshooting Guide

| Issue | Root Cause | Solution |
| :--- | :--- | :--- |
| **Port 5432 or 8000 already in use** | A local PostgreSQL or web server is running. | Stop the local service or change `PORT`/`DB_PORT` in your `.env`. |
| **Pydantic backtracking during pip install** | Old `pydantic>=2,<3` constraint causing solver backtracking. | Pin `pydantic>=2.7.0,<3.0.0` (already applied in `requirements.txt`). |
| **Database connection refused** | Database starting slower than API container. | `docker-compose.yml` uses `condition: service_healthy` to ensure Postgres is accepting queries before API launches. |
| **Frontend assets 404** | Missing `frontend/` directory inside container. | `Dockerfile` copies all files (`COPY . .`), ensuring `/app/frontend` is available to FastAPI static files. |
