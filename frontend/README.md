# Touchline Intelligence — Frontend

The web app for launching multi-agent football debates, watching them live,
and exploring their analytics. React 18 + Vite, styled with Tailwind (CDN) and
Phosphor icons.

## Pages

The build is a **multi-page app**: each page has its own HTML entry, all
rendering the same React `App`. The app reads the URL to pick the page, so
deep links work without a client-side router.

| URL | Entry | Page |
|---|---|---|
| `/` | `index.html` | Landing: animated pitch hero and quick start |
| `/arena` | `arena.html` | Arena: choose topic, rounds and agents; watch the debate stream turn by turn; replay it |
| `/history` | `history.html` | Past and in-flight debates with live status |
| `/intel` | `intel.html` | Intelligence: stance trajectories, agreement, influence, synthesis and advisor decision |
| `/devops` | `devops.html` | API health and system telemetry |

The FastAPI backend serves the same pages at `/arena`, `/app/arena`,
`/arena.html`, and so on. (The in-app router also maps `deliberation` → arena
and `intelligence` / `analytics` → intel, but the server does not serve those
URLs directly.)

While a debate runs, the Arena polls `GET /discussions/{id}/status` every
2.5 s and reloads the transcript, so new turns appear without a page refresh.
Signing in stores a session token in `localStorage` (`touchline_token`).

## Source layout

```text
frontend/
├── index.html, arena.html, history.html, intel.html, devops.html   # page entries
├── vite.config.js            # multi-page build + dev proxy to :8000
├── src/
│   ├── main.jsx              # mounts <App />
│   ├── App.jsx               # app shell, routing, data fetching, all five pages
│   ├── index.css             # design tokens and animations
│   └── components/
│       ├── LandingPage.jsx
│       ├── AgentCommunicationPitch.jsx   # pitch graph of agents and message routes
│       ├── MarkdownPreview.jsx           # renders agent messages (marked)
│       ├── AuthModal.jsx, OnboardingModal.jsx, ProfileModal.jsx
│       └── PersonaManagerModal.jsx       # create/edit custom personas
└── dist/                     # production build, committed (rebuild + commit after changes)
```

`src/components/` also contains components that `App.jsx` does **not**
currently import: `Header`, `BottomNav`, `DeliberationView`,
`IntelligenceView`, `HistoryView`, `DevOpsView`, `SpeechCard`,
`TacticalPitch`, `OpinionTrajectories`, `AnimatedNumber`, `TouchlineLogo`.
They come from an earlier modular version of the app. Wire them in or delete
them; don't assume they are live.

Other folders that are **not part of the React build**:

| Path | What it is |
|---|---|
| `vanilla_app/` | The original plain-JS discussion room (`app.js`, `styles.css`, `index.html`) |
| `app.js`, `styles.css` (root) | Copies of the `vanilla_app/` files, unused by the React app |
| `components/charts.py`, `views/analytics.py` | Python chart helpers from the Week 4 analytics dashboard prototype |
| `claude_design/` | Design-system export used as visual reference |

## Development

Requires Node.js 18+. Start the backend first (from the repository root):

```bash
python -m uvicorn src.api.main:app --port 8000 --reload
```

Then, in `frontend/`:

```bash
npm install
npm run dev        # http://localhost:3000, proxies API calls to :8000
```

The dev server proxies `/health`, `/topics`, `/discussions`, `/analytics`,
`/auth`, `/profile`, `/reports`, `/docs` and `/openapi.json` to the backend. If
you add an API route with a new prefix, add it to `server.proxy` in
`vite.config.js`.

## Production build

```bash
npm run build      # writes dist/
npm run preview    # serves dist/ on :3000 for a quick check
```

The backend serves `frontend/dist` automatically when it exists (otherwise the
raw `frontend/` folder), so after a build the whole app is available from the
API at `http://localhost:8000/`. Rebuild before building the Docker image so it
contains the current frontend.
