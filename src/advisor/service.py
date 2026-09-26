"""Background verified analysis jobs and snapshot-aware disk caching."""
from __future__ import annotations
import hashlib
import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import NamedTemporaryFile
from threading import BoundedSemaphore, RLock
from typing import Literal

from src.advisor.evidence import build_evidence_bundle
from src.advisor.models import AnalystRequest, SnapshotHash, StrictModel
from src.advisor.verification import CheckedResponse, analyze_verified
from src.agent.llm import OpenAICompatibleLLM
from src.api.services.discussion_service import get_saved_discussion

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = ROOT / "reports" / "api_cache" / "advisor"
CACHE_TTL = 24 * 60 * 60
RESEARCH_CACHE_TTL = 60 * 60
JOB_TTL = 60 * 60
MAX_RECORDS = 128
MAX_CACHE_FILES = 64
_lock = RLock()
_slots = BoundedSemaphore(2)
_executor = None
_pipeline_tag = None
_jobs = {}
_finished_at = {}
_inflight = {}

class CapacityError(RuntimeError):
    pass

class AdvisorJob(StrictModel):
    job_id: str
    request: AnalystRequest
    snapshot_sha256: SnapshotHash
    state: Literal["queued", "running", "completed", "failed"]
    cached: bool = False
    result: CheckedResponse | None = None
    error: str | None = None

def _code_tag():
    digest = hashlib.sha256(b"advisor-pipeline-v1")
    paths = [
        "src/advisor/models.py", "src/advisor/evidence.py",
        "src/advisor/decision.py", "src/advisor/match_analysis.py",
        "src/advisor/verification.py", "src/agent/llm.py",
        "src/advisor/research.py", "src/advisor/search.py", "src/agent/retrieval.py",
        "src/advisor/service.py", "src/advisor/routes.py",
    ]
    for name in paths:
        digest.update(name.encode())
        digest.update((ROOT / name).read_bytes())
    return digest.hexdigest()

def start_advisor_worker():
    global _executor, _pipeline_tag
    with _lock:
        if _executor is None:
            _pipeline_tag = _code_tag()
            _executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="advisor")

def shutdown_advisor_worker():
    global _executor
    with _lock:
        executor, _executor = _executor, None
    if executor is not None:
        executor.shutdown(wait=True)

def _preview_guard(request):
    if request.mode == "match_preview":
        now = time.time()
        if request.match_kickoff.timestamp() <= now:
            raise ValueError("This match has started; use match_review.")
        if request.evidence_cutoff.timestamp() > now:
            raise ValueError("The evidence cutoff cannot be in the future.")

def _snapshot(request):
    discussion = get_saved_discussion(request.discussion_id)
    return build_evidence_bundle(request, discussion).snapshot_sha256

def _settings():
    return {
        "endpoint": os.environ.get("LLM_BASE_URL", "").strip(),
        "analyst_model": os.environ.get("LLM_MODEL", "").strip(),
        "verifier_model": os.environ.get("ADVISOR_VERIFIER_MODEL", "").strip()
            or os.environ.get("LLM_MODEL", "").strip(),
        "temperature": 0, "analyst_tokens": 6000, "verifier_tokens": 4000,
        "timeout": 60, "retries": 1,
        "research": "discussion+knowledge+web+pages-v1",
        "web_provider": "tavily-with-ddgs-fallback" if os.environ.get("TAVILY_API_KEY", "").strip() else "ddgs",
    }

def _key(request, snapshot, settings):
    data = {
        "request": request.model_dump(mode="json"),
        "snapshot": snapshot, "models": settings, "implementation": _pipeline_tag,
    }
    raw = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()

def _cacheable(result):
    return (
        result.response.status != "failed"
        and (result.response.report is None or result.verification is not None)
        and (result.verification is None or result.verification.error is None)
    )

def _load_cache(key, request, snapshot):
    path = CACHE_DIR / f"{key}.json"
    if not path.is_file():
        return None
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
        result = CheckedResponse.model_validate(record["result"])
        if (
            record["key"] == key and record["expires_at"] > time.time()
            and result.response.request == request
            and result.response.snapshot_sha256 == snapshot
            and _cacheable(result)
        ):
            return result
    except (ValueError, KeyError, TypeError, OSError):
        logger.warning("Ignoring invalid advisor cache %s", path.name)
    return None

def _save_cache(key, request, result):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    expiry = time.time() + (RESEARCH_CACHE_TTL if result.response.research is not None else CACHE_TTL)
    if request.mode == "match_preview":
        expiry = min(expiry, request.match_kickoff.timestamp())
    record = {"key": key, "expires_at": expiry, "result": result.model_dump(mode="json")}
    temporary = None
    try:
        with NamedTemporaryFile(mode="w", encoding="utf-8", dir=CACHE_DIR,
                                prefix=".advisor-", suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(record, handle, ensure_ascii=False)
        os.replace(temporary, CACHE_DIR / f"{key}.json")
        files = sorted(CACHE_DIR.glob("*.json"), key=lambda path: path.stat().st_mtime)
        for path in files[:-MAX_CACHE_FILES]:
            path.unlink(missing_ok=True)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)

def _trim_jobs():
    now = time.monotonic()
    for job_id, finished in list(_finished_at.items()):
        if now - finished > JOB_TTL:
            _jobs.pop(job_id, None)
            _finished_at.pop(job_id, None)
    while len(_jobs) >= MAX_RECORDS and _finished_at:
        oldest = min(_finished_at, key=_finished_at.get)
        _jobs.pop(oldest, None)
        _finished_at.pop(oldest, None)

def _run(job_id, key, request, snapshot, settings):
    try:
        with _lock:
            _jobs[job_id].state = "running"
        _preview_guard(request)
        if _snapshot(request) != snapshot:
            raise RuntimeError("The saved discussion changed; submit a new request.")
        analyst = OpenAICompatibleLLM(
            model=settings["analyst_model"], base_url=settings["endpoint"],
            temperature=0, max_tokens=6000, timeout=60, max_retries=1,
        )
        verifier = OpenAICompatibleLLM(
            model=settings["verifier_model"], base_url=settings["endpoint"],
            temperature=0, max_tokens=4000, timeout=60, max_retries=1,
        )
        result = analyze_verified(request, analyst_client=analyst, verifier_client=verifier)
        if result.response.report is not None and result.verification is None:
            raise RuntimeError("The advisor returned an unaudited report.")
        if result.response.request != request:
            raise RuntimeError("The advisor returned a different request.")
        if result.response.snapshot_sha256 != snapshot or _snapshot(request) != snapshot:
            raise RuntimeError("The saved discussion changed during analysis; submit again.")
        _preview_guard(request)
        if _cacheable(result):
            try:
                _save_cache(key, request, result)
            except OSError:
                logger.exception("Advisor cache could not be saved.")
        with _lock:
            _jobs[job_id].result = result
            _jobs[job_id].state = "completed"
    except Exception:
        logger.exception("Advisor job %s failed.", job_id)
        with _lock:
            _jobs[job_id].state = "failed"
            _jobs[job_id].error = "Analysis could not finish. Retry; check server logs if it repeats."
    finally:
        with _lock:
            _inflight.pop(key, None)
            _finished_at[job_id] = time.monotonic()
        _slots.release()

def submit_job(request: AnalystRequest, force=False) -> AdvisorJob:
    from uuid import uuid4
    request = AnalystRequest.model_validate(request.model_dump())
    if len(request.question) > 4000:
        raise ValueError("Keep the question within 4,000 characters.")
    _preview_guard(request)
    snapshot = _snapshot(request)
    settings = _settings()
    with _lock:
        if _executor is None:
            raise RuntimeError("The advisor worker is not running.")
        _trim_jobs()
        key = _key(request, snapshot, settings)
        if key in _inflight:
            return _jobs[_inflight[key]].model_copy(deep=True)
        cached = None if force else _load_cache(key, request, snapshot)
        job_id = uuid4().hex
        job = AdvisorJob(
            job_id=job_id, request=request, snapshot_sha256=snapshot,
            state="completed" if cached is not None else "queued",
            cached=cached is not None, result=cached,
        )
        if cached is not None:
            _jobs[job_id] = job
            _finished_at[job_id] = time.monotonic()
            return job.model_copy(deep=True)
        if not settings["endpoint"] or not settings["analyst_model"] or not os.environ.get("LLM_API_KEY"):
            raise RuntimeError("Configure LLM_API_KEY, LLM_BASE_URL and LLM_MODEL first.")
        if not _slots.acquire(blocking=False):
            raise CapacityError("The advisor is busy. Retry shortly.")
        _jobs[job_id] = job
        _inflight[key] = job_id
        try:
            _executor.submit(_run, job_id, key, request, snapshot, settings)
        except Exception:
            _jobs.pop(job_id, None)
            _inflight.pop(key, None)
            _slots.release()
            raise
        return job.model_copy(deep=True)

def get_job(discussion_id: str, job_id: str) -> AdvisorJob:
    with _lock:
        _trim_jobs()
        job = _jobs.get(job_id)
        if job is None or job.request.discussion_id != discussion_id:
            raise FileNotFoundError("Job not found or expired. Submit the question again.")
        view = job.model_copy(deep=True)
    _preview_guard(view.request)
    if view.state == "completed" and _snapshot(view.request) != view.snapshot_sha256:
        raise RuntimeError("This result belongs to an older discussion snapshot. Submit again.")
    return view
