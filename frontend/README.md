# Football Discussion Frontend

This folder contains the browser frontend for the multi-agent football discussion room.

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
