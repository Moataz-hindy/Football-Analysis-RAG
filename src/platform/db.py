"""Database management and logical multi-tenancy layer.

Supports PostgreSQL 16 (production/docker) with automatic fallback to
embedded SQLite (local dev/test) when Postgres is unavailable, ensuring
resilience, zero downtime, and complete compatibility.
"""

import json
import logging
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
SQLITE_DB_PATH = DATA_DIR / "football_platform.db"

_PG_AVAILABLE = None


def is_postgres_configured() -> bool:
    """Check if PostgreSQL credentials or URL are present in the environment."""
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return False
    return bool(os.environ.get("DATABASE_URL") or os.environ.get("DB_HOST"))


def get_pg_connection():
    """Attempt connecting to PostgreSQL."""
    import psycopg2
    from pgvector.psycopg2 import register_vector

    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        conn = psycopg2.connect(db_url, connect_timeout=4)
    else:
        conn = psycopg2.connect(
            host=os.environ.get("DB_HOST", "localhost"),
            port=os.environ.get("DB_PORT", "5432"),
            dbname=os.environ.get("DB_NAME", "football_intelligence"),
            user=os.environ.get("DB_USER", "postgres"),
            password=os.environ.get("DB_PASSWORD", "postgres"),
            connect_timeout=4,
        )
    return conn


def _init_sqlite_schema(conn: sqlite3.Connection):
    """Initialize platform tables in SQLite fallback mode."""
    cur = conn.cursor()
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        salt TEXT NOT NULL,
        display_name TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS profiles (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
        display_name TEXT NOT NULL,
        profile_type TEXT NOT NULL DEFAULT 'scout',
        football_focus TEXT DEFAULT 'Player Recruitment & Positional Profiling',
        experience_level TEXT DEFAULT 'Professional',
        preferred_analysis_style TEXT DEFAULT 'Statistical & Quantitative',
        preferred_report_type TEXT DEFAULT 'Scout Report',
        favorite_competitions TEXT DEFAULT '["UEFA Champions League", "FIFA World Cup", "Premier League"]',
        favorite_teams TEXT DEFAULT '["Argentina", "Manchester City", "Arsenal"]',
        favorite_analysis_areas TEXT DEFAULT '["Tactical Structures", "Pressing Metrics", "xG Differential"]',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS sessions (
        token TEXT PRIMARY KEY,
        user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        profile_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
        created_at TEXT NOT NULL,
        expires_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS profile_memory (
        id TEXT PRIMARY KEY,
        profile_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
        memory_type TEXT NOT NULL,
        key TEXT NOT NULL,
        value TEXT NOT NULL,
        source TEXT NOT NULL DEFAULT 'explicit',
        confidence REAL DEFAULT 1.0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS profile_personas (
        id TEXT PRIMARY KEY,
        profile_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
        name TEXT NOT NULL,
        field TEXT NOT NULL,
        background TEXT NOT NULL,
        stance TEXT NOT NULL,
        communication_style TEXT NOT NULL,
        expertise TEXT NOT NULL,
        priorities TEXT NOT NULL,
        source TEXT NOT NULL DEFAULT 'user',
        is_active INTEGER DEFAULT 1,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS profile_reports (
        id TEXT PRIMARY KEY,
        profile_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
        discussion_id TEXT,
        report_type TEXT NOT NULL,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        sections TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS user_discussions (
        id TEXT PRIMARY KEY,
        profile_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
        discussion_id TEXT NOT NULL,
        topic TEXT NOT NULL,
        num_rounds INTEGER DEFAULT 3,
        num_agents INTEGER DEFAULT 6,
        created_at TEXT NOT NULL
    );

    CREATE INDEX IF NOT EXISTS idx_profiles_user_id ON profiles(user_id);
    CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token);
    CREATE INDEX IF NOT EXISTS idx_profile_memory_profile_id ON profile_memory(profile_id);
    CREATE INDEX IF NOT EXISTS idx_profile_personas_profile_id ON profile_personas(profile_id);
    CREATE INDEX IF NOT EXISTS idx_profile_reports_profile_id ON profile_reports(profile_id);
    """)
    conn.commit()


def init_db():
    """Ensure database schema is ready on startup."""
    global _PG_AVAILABLE
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if is_postgres_configured():
        try:
            conn = get_pg_connection()
            cur = conn.cursor()
            migration_path = PROJECT_ROOT / "sql" / "migrations" / "001_multi_tenant_profiles.sql"
            if migration_path.is_file():
                cur.execute(migration_path.read_text(encoding="utf-8"))
                conn.commit()
            conn.close()
            _PG_AVAILABLE = True
            logger.info("PostgreSQL multi-tenant schema initialized successfully.")
            return
        except Exception as e:
            logger.warning("PostgreSQL connection failed (%s); falling back to embedded SQLite.", e)
            _PG_AVAILABLE = False
    else:
        _PG_AVAILABLE = False

    # SQLite fallback
    conn = sqlite3.connect(str(SQLITE_DB_PATH))
    conn.execute("PRAGMA foreign_keys = ON")
    _init_sqlite_schema(conn)
    conn.close()
    logger.info("Embedded SQLite platform database ready at %s", SQLITE_DB_PATH)


class PgCursorWrapper:
    """Translate SQLite-style '?' placeholders into PostgreSQL '%s' placeholders."""

    def __init__(self, raw_cur):
        self._cur = raw_cur

    def execute(self, query, vars=None):
        if isinstance(query, str) and "?" in query:
            query = query.replace("?", "%s")
        if vars is not None:
            return self._cur.execute(query, vars)
        return self._cur.execute(query)

    def executemany(self, query, vars_list):
        if isinstance(query, str) and "?" in query:
            query = query.replace("?", "%s")
        return self._cur.executemany(query, vars_list)

    def __getattr__(self, name):
        return getattr(self._cur, name)


@contextmanager
def get_db_cursor() -> Generator[Any, None, None]:
    """Provide a database cursor with automatic commit/rollback and dictionary-like row mapping."""
    global _PG_AVAILABLE
    if _PG_AVAILABLE is None:
        init_db()

    if _PG_AVAILABLE:
        conn = None
        try:
            conn = get_pg_connection()
            import psycopg2.extras
            raw_cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur = PgCursorWrapper(raw_cur)
            yield cur
            conn.commit()
            raw_cur.close()
        except Exception:
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
    else:
        conn = sqlite3.connect(str(SQLITE_DB_PATH))
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        try:
            yield cur
            conn.commit()
            cur.close()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
