"""FastAPI Application Entry Point for Football Analysis Platform."""

import json
import logging
import os
import re
import sys
import time
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=True)
except ImportError:
    pass
from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
from src.api.routes import router
from src.api.services.discussion_service import(
    start_discussion_worker,
    shutdown_discussion_worker
)

# Multi-Tenant Platform & Persona routes
from src.api.platform_routes import router as platform_router
from src.platform.db import init_db as init_platform_db

# ── Structured Logging ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger("src.api")

# ── Configurable CORS ──
DEFAULT_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:8501",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:8501",
]

env_cors = os.environ.get("CORS_ORIGINS", "").strip()
allowed_origins = (
    [origin.strip() for origin in env_cors.split(",") if origin.strip()]
    if env_cors
    else DEFAULT_ORIGINS
)


def _init_database_if_needed():
    """Ensure pgvector extension, table schema, and precomputed embeddings exist."""
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return
    if not (os.environ.get("DATABASE_URL") or os.environ.get("DB_HOST")):
        return
    try:
        from src.rag.search import get_connection
        conn = get_connection()
        cur = conn.cursor()
        init_sql_path = Path(__file__).resolve().parents[2] / "sql" / "init_db.sql"
        if init_sql_path.is_file():
            cur.execute(init_sql_path.read_text(encoding="utf-8"))
            conn.commit()
        cur.execute("SELECT COUNT(*) FROM football_chunks")
        count = cur.fetchone()[0]
        if count == 0:
            logger.info("Database football_chunks is empty. Ingesting precomputed embeddings...")
            from src.rag.ingest import main as run_ingest
            run_ingest()
            logger.info("Precomputed embeddings ingested successfully.")
        else:
            logger.info("Database football_chunks ready with %d chunks.", count)
        conn.close()
    except Exception as e:
        logger.warning("Database auto-init skipped or failed: %s", e)


# ── Application Lifespan ──
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage the discussion worker."""
    logger.info("Starting Football Analysis Platform API server...")
    logger.info("Configured CORS origins: %s", allowed_origins)


    # Initialize multi-tenant platform database (Postgres or embedded SQLite fallback)
    try:
        init_platform_db()
    except Exception as e:
        logger.warning("Platform database initialization failed: %s", e)
    start_discussion_worker()

    try:
        asyncio.create_task(
            run_in_threadpool(_init_database_if_needed)
        )

        yield

    finally:
        logger.info(
            "Waiting for accepted background jobs to finish..."
        )

        await run_in_threadpool(shutdown_discussion_worker)

        logger.info(
            "Discussion worker stopped."
        )


# ── FastAPI App Instance ──
app = FastAPI(
    title="Football Analysis Platform API",
    description=(
        "Multi-agent football discussions, evidence-based advice, "
        "and intelligence analytics."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS Middleware ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class JsonTrailingCommaMiddleware:
    """ASGI middleware to strip trailing commas from JSON request bodies before parsing."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope.get("method") in ("POST", "PUT", "PATCH"):
            content_type = ""
            for name, value in scope.get("headers", []):
                if name.lower() == b"content-type":
                    content_type = value.decode("latin1")
                    break
            if "application/json" in content_type:
                body_parts = []
                more_body = True
                while more_body:
                    message = await receive()
                    if message["type"] == "http.request":
                        body_parts.append(message.get("body", b""))
                        more_body = message.get("more_body", False)
                    elif message["type"] == "http.disconnect":
                        return
                raw_body = b"".join(body_parts)
                cleaned_body = raw_body

                if raw_body:
                    try:
                        json.loads(raw_body)
                    except Exception:
                        text_body = raw_body.decode("utf-8", errors="replace")
                        cleaned_text = text_body
                        for _ in range(5):
                            cleaned_text = re.sub(r',\s*([}\]])', r'\1', cleaned_text)
                        try:
                            json.loads(cleaned_text)
                            cleaned_body = cleaned_text.encode("utf-8")
                        except Exception:
                            cleaned_body = raw_body

                if cleaned_body != raw_body:
                    new_headers = []
                    for h_name, h_val in scope.get("headers", []):
                        if h_name.lower() == b"content-length":
                            new_headers.append((b"content-length", str(len(cleaned_body)).encode("latin1")))
                        else:
                            new_headers.append((h_name, h_val))
                    scope = dict(scope)
                    scope["headers"] = new_headers

                sent = False
                async def custom_receive():
                    nonlocal sent
                    if not sent:
                        sent = True
                        return {
                            "type": "http.request",
                            "body": cleaned_body,
                            "more_body": False,
                        }
                    return {"type": "http.disconnect"}

                await self.app(scope, custom_receive, send)
                return

        await self.app(scope, receive, send)


app.add_middleware(JsonTrailingCommaMiddleware)



# ── Request Logging Middleware ──
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log incoming requests with method, path, HTTP status, and duration."""
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    logger.info(
        "method=%s path=%s status=%d duration=%.4fs",
        request.method,
        request.url.path,
        response.status_code,
        duration,
    )
    return response


# ── Global Exception Handlers ──
@app.exception_handler(FileNotFoundError)
async def handle_not_found(request: Request, exc: FileNotFoundError):
    logger.warning("Resource not found: %s", exc)
    return JSONResponse(
        status_code=404,
        content={"error": "Not Found", "detail": str(exc)},
    )


@app.exception_handler(ValueError)
async def handle_validation_error(request: Request, exc: ValueError):
    logger.warning("Validation error on %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=422,
        content={"error": "Validation Error", "detail": str(exc)},
    )


@app.exception_handler(RequestValidationError)
async def handle_request_validation_error(request: Request, exc: RequestValidationError):
    logger.warning("Request validation error on %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=422,
        content=jsonable_encoder({"error": "Unprocessable Entity", "detail": exc.errors()}),
    )


@app.exception_handler(json.decoder.JSONDecodeError)
async def handle_json_decode_error(request: Request, exc: json.decoder.JSONDecodeError):
    logger.warning("JSON decode error on %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=400,
        content={"error": "Invalid JSON", "detail": str(exc)},
    )

@app.exception_handler(Exception)
async def handle_internal_error(request: Request, exc: Exception):
    logger.error("Unhandled exception processing %s %s: %s", request.method, request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal Server Error", "detail": str(exc)},
    )


# ── Frontend (multi-page: /, /arena, /history, /intel, /devops) ──
# The Vite build emits one HTML document per view and references its bundle with
# relative asset URLs (./assets/…). Documents are served both at the mount
# prefix and at the site root, so relative asset paths are re-rooted at the
# mount before the page reaches the browser.
FRONTEND_MOUNT = "/app"
frontend_dist = os.path.join(os.getcwd(), "frontend", "dist")
frontend_dir = frontend_dist if os.path.isdir(frontend_dist) else os.path.join(os.getcwd(), "frontend")

_FRONTEND_PAGES = {
    "index": "index.html",
    "arena": "arena.html",
    "history": "history.html",
    "intel": "intel.html",
    "devops": "devops.html",
}

_RELATIVE_ASSET_RE = re.compile(r'(?P<attr>src|href)="(?:\./|\.\./)(?P<asset>assets/[^"]*)"')


def _render_frontend_page(filename: str) -> str:
    """Return a built page, with relative bundle URLs rooted at the mount."""
    page_path = Path(frontend_dir) / filename
    if not page_path.is_file():
        # Fallback page for builds that predate the multi-page entrypoints.
        page_path = Path(frontend_dir) / _FRONTEND_PAGES["index"]
    html = page_path.read_text(encoding="utf-8")
    return _RELATIVE_ASSET_RE.sub(
        lambda match: f'{match.group("attr")}="{FRONTEND_MOUNT}/{match.group("asset")}"',
        html,
    )


def _frontend_page_endpoint(filename: str):
    """Build a read-only endpoint that serves one frontend document."""

    async def _serve_frontend_page() -> HTMLResponse:
        return HTMLResponse(_render_frontend_page(filename))

    return _serve_frontend_page


def _frontend_page_routes() -> dict:
    """Map every supported page URL (root and mounted) to its document."""
    routes = {
        "/index.html": _FRONTEND_PAGES["index"],
        f"{FRONTEND_MOUNT}/index.html": _FRONTEND_PAGES["index"],
    }
    for slug, filename in _FRONTEND_PAGES.items():
        if slug == "index":
            continue
        for route in (f"/{slug}", f"/{slug}.html", f"{FRONTEND_MOUNT}/{slug}", f"{FRONTEND_MOUNT}/{slug}.html"):
            routes[route] = filename
    return routes


# Registered before the static mount so these readable URLs win over the mount.
for _route, _filename in _frontend_page_routes().items():
    app.add_api_route(
        _route,
        _frontend_page_endpoint(_filename),
        methods=["GET"],
        include_in_schema=False,
    )

app.mount(FRONTEND_MOUNT, StaticFiles(directory=frontend_dir, html=True), name="frontend")



# ── Mount Routers ──
app.include_router(router)
app.include_router(platform_router)


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
    )
