"""Durable opinion cache with provider recovery and renewable generation claims."""
from contextlib import contextmanager
import json
import logging
import os
import sqlite3
import time
from pathlib import Path
from threading import BoundedSemaphore, Event, Thread

from src.advisor.core import PROMPT, MAX_OUTPUT_TOKENS, discussion_snapshot, fingerprint, generate_opinion
from src.analytics import advisor as decision_core
from src.agent.llm import OpenAICompatibleLLM
from src.api.services.discussion_service import get_saved_discussion, get_discussion_status_record

logger = logging.getLogger(__name__)
CACHE_PATH = Path(__file__).resolve().parents[2] / "reports/api_cache/advisor/opinions.sqlite3"
SLOTS = BoundedSemaphore(2)
STALE_SECONDS = 300
HEARTBEAT_SECONDS = 30


class NotReady(ValueError):
    pass


class Busy(RuntimeError):
    pass


def _connect():
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(CACHE_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE IF NOT EXISTS opinions (
        cache_key TEXT PRIMARY KEY, state TEXT NOT NULL, attempts INTEGER NOT NULL,
        started REAL NOT NULL, result TEXT NOT NULL)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS attempt_usage (
        cache_key TEXT NOT NULL, attempt INTEGER NOT NULL, started REAL NOT NULL,
        result TEXT, PRIMARY KEY (cache_key, attempt))""")
    return conn


def _context(discussion_id, kind="opinion"):
    if kind not in {"opinion", "decision"}:
        raise ValueError("Unknown Advisor output kind")
    discussion = get_saved_discussion(discussion_id)
    if get_discussion_status_record(discussion_id).status != "completed" or not discussion.messages:
        raise NotReady("The Advisor needs a completed, nonempty discussion.")
    model = os.environ.get("ADVISOR_MODEL", "").strip() or os.environ.get("LLM_MODEL", "").strip()
    snapshot = discussion_snapshot(discussion)
    cache_inputs = {"discussion_id": discussion_id, "snapshot": snapshot, "model": model,
                       "endpoint": os.environ.get("LLM_BASE_URL", ""), "prompt": PROMPT if kind == "opinion" else decision_core.ADVISOR_SYSTEM_PROMPT,
                       "input_version": 1, "output_tokens": MAX_OUTPUT_TOKENS if kind == "opinion" else decision_core.MAX_OUTPUT_TOKENS}
    if kind == "decision":
        # Older free-text attempts must not block the corrected structured request.
        cache_inputs["response_format"] = decision_core.decision_response_format()
    key = fingerprint(cache_inputs)
    return discussion, model, snapshot, key


def _view(row, key):
    if row is None:
        return {"state": "missing", "cache_key": key, "retryable": False}
    result = json.loads(row["result"])
    stale = row["state"] == "running" and time.time() - row["started"] > STALE_SECONDS
    if stale:
        result.update(state="failed", error="The previous Advisor request was interrupted or timed out.")
    result.update(cache_key=key, cached=True, attempts=row["attempts"],
                  retryable=(result["state"] == "failed"))
    return result


def _renew_claim(key, attempt):
    # Separate connection: SQLite connections cannot cross thread boundaries.
    conn = _connect()
    try:
        conn.execute("UPDATE opinions SET started=? WHERE cache_key=? AND attempts=? AND state='running'",
                     (time.time(), key, attempt))
        conn.commit()
    finally:
        conn.close()


@contextmanager
def _keep_claim_alive(key, attempt):
    stop = Event()

    def heartbeat():
        while not stop.wait(HEARTBEAT_SECONDS):
            try:
                _renew_claim(key, attempt)
            except Exception:
                logger.exception("Could not renew Advisor claim")

    thread = Thread(target=heartbeat, name="advisor-heartbeat", daemon=True)
    thread.start()
    try:
        yield
    finally:
        stop.set()
        thread.join()


def get_opinion(discussion_id, kind="opinion"):
    _, _, _, key = _context(discussion_id, kind)
    conn = _connect()
    try:
        view = _view(conn.execute("SELECT * FROM opinions WHERE cache_key=?", (key,)).fetchone(), key)
        view["attempt_usage"] = [
            {"attempt": row["attempt"], "started": row["started"],
             "usage": json.loads(row["result"]).get("usage") if row["result"] else None}
            for row in conn.execute("SELECT * FROM attempt_usage WHERE cache_key=? ORDER BY attempt", (key,))
        ]
        return view
    finally:
        conn.close()


def create_opinion(discussion_id, retry_failed=False, kind="opinion"):
    discussion, model, snapshot, key = _context(discussion_id, kind)
    if not SLOTS.acquire(blocking=False):
        raise Busy("The Advisor is busy. Try again shortly.")
    conn = None
    try:
        conn = _connect()
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT * FROM opinions WHERE cache_key=?", (key,)).fetchone()
        view = _view(row, key)
        if row and not (retry_failed and view["retryable"]):
            conn.commit()
            return view
        # Validate configuration before recording a paid attempt.
        if not model or not os.environ.get("LLM_API_KEY") or not os.environ.get("LLM_BASE_URL"):
            raise NotReady("Configure the model endpoint and credentials before using the Advisor.")
        attempts = row["attempts"] + 1 if row else 1
        initial = {"state": "running", "model": model, "snapshot": snapshot}
        conn.execute("INSERT OR REPLACE INTO opinions VALUES (?, ?, ?, ?, ?)",
                     (key, "running", attempts, time.time(), json.dumps(initial)))
        conn.execute("INSERT INTO attempt_usage VALUES (?, ?, ?, NULL)", (key, attempts, time.time()))
        conn.commit()  # Durable claim BEFORE any external request.
        try:
            client = OpenAICompatibleLLM(model=model, temperature=0.2,
                max_tokens=MAX_OUTPUT_TOKENS if kind == "opinion" else decision_core.MAX_OUTPUT_TOKENS, timeout=45, use_pacer=False)
            # Keep the durable claim live throughout every provider retry window.
            with _keep_claim_alive(key, attempts):
                result = (generate_opinion(discussion, client) if kind == "opinion"
                          else decision_core.generate_advisor_decision(discussion, client))
            if discussion_snapshot(get_saved_discussion(discussion_id)) != snapshot:
                result.update(state="failed", opinion=None, decision=None,
                              error="The discussion changed during analysis. Reload the discussion.")
        except Exception:
            logger.exception("Advisor attempt failed for %s", discussion_id)
            result = {"state": "failed", "opinion": None, "decision": None,
                      "error": "The Advisor could not finish after provider recovery. Retry using the saved discussion."}
        result.update(model=model, snapshot=snapshot, created_at=time.time())
        conn.execute("UPDATE attempt_usage SET result=? WHERE cache_key=? AND attempt=?",
                     (json.dumps(result), key, attempts))
        # A stale attempt cannot overwrite a newer manually requested attempt.
        conn.execute("UPDATE opinions SET state=?, result=? WHERE cache_key=? AND attempts=?",
                     (result["state"], json.dumps(result), key, attempts))
        conn.commit()
        stored = conn.execute("SELECT * FROM opinions WHERE cache_key=?", (key,)).fetchone()
        return {**_view(stored, key), "cached": False}
    finally:
        if conn is not None:
            conn.close()
        SLOTS.release()
