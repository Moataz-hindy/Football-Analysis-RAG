# Football Discussion Frontend

This folder contains the browser frontend for the multi-agent football discussion room.

## React Discussion Advisor

The React app automatically submits advisor analysis after the API confirms a
discussion is completed. In the Arena, the **Discussion Advisor** report appears
below the messages; **Read advisor report** at the top jumps to it. The same report
is available at the top of **Intelligence**. Reopening a completed discussion also
loads its advisor result, reusing the backend cache when eligible.

The default analysis is a decision with pros, cons, and a recommendation. Open
**Analysis settings** to select a match review or preview. Both match modes need
two different team names. Previews also require a cutoff at or before now and a
future kickoff. The date inputs use your browser's local timezone and are sent
to the API in UTC. Changing fields does not submit a job until you apply settings.

The panel shows queue progress, errors with retry, conditional recommendations,
evidence gaps, and clickable evidence excerpts. The advisor searches the database
and web, reads relevant public articles, and can request focused follow-up
research. **Evidence research** shows retrieval attempts; **Evidence library**
identifies discussion, database, search, and page excerpts with their sources.
Citation checks assess the
supplied excerpts; they do not certify real-world accuracy. **Reanalyze discussion**
explicitly bypasses finished cache entries. Normal loads and retries reuse
eligible backend results.
An uncited action label is never displayed as the advisor's verdict. Decisions
with empty option assessments withhold their recommendation. Preview research
continues to require evidence eligible at its cutoff; live pages are not
silently treated as historical captures.

For the React development workflow, keep the backend running from the repository
root, then start Vite in a second terminal:

```bash
python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000 --env-file .env
```

```bash
cd frontend
npm run dev
```

Open `http://localhost:3000/`. Vite proxies advisor requests to the API on port
8000 using its existing `/discussions` proxy. Backend LLM configuration is required
to generate new reports. No frontend API key is needed.

React advisor files:

- `src/App.jsx`: completion tracking and Arena/Intelligence placement.
- `src/hooks/useDiscussionAdvisor.js`: selection, settings, and subscriptions.
- `src/lib/advisorClient.js`: shared submission, polling, retries, and validation.
- `src/components/AdvisorPanel.jsx` and `.css`: themed report and evidence display.

Run offline advisor checks and the production build from this folder:

```bash
npm run test:advisor
npm run build
```

The sections below describe the older static frontend.

## What Is Implemented

- Curated football topic selection from `GET /topics`
- Custom topic input
- Discussion launch through `POST /discussions`
- Saved discussion list from `GET /discussions`
- Multi-agent role cards with avatar initials
- Agent-attributed conversation messages
- Round-based timeline with initial opinions and rounds 1 to 3
- Replay controls: reset, previous, play/pause, and next round
- Responsive layout for desktop, tablet, and mobile screens
- Static frontend hosting through FastAPI at `/app`

## Start The Frontend

The frontend is served by the FastAPI backend. Run these commands from the repository root in PowerShell:

```powershell
.venv\Scripts\Activate.ps1
.venv\Scripts\python.exe -m src.api.main
```

Open the frontend at:

```text
http://localhost:8000/app
```

The API documentation is available at:

```text
http://localhost:8000/docs
```

## Alternative Start Command

Without activating the virtual environment:

```powershell
.venv\Scripts\python.exe -m uvicorn src.api.main:app --reload
```

Then open `http://localhost:8000/app`.

## Files

- `index.html` - Discussion room markup and layout structure
- `app.js` - API calls, topic selection, discussion loading, timeline rendering, and replay behavior
- `styles.css` - Responsive visual styling
- `README.md` - Frontend feature and startup documentation

## Requirements

Install the project dependencies before starting the API:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

The `vaderSentiment` package is included in `requirements.txt` and is required by the API during startup.
