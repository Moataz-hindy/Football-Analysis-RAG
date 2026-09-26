"""Job and HTTP contracts using local stubs; no model or network calls."""

import json
from datetime import datetime, timezone
from threading import BoundedSemaphore, Event

import pytest
from fastapi import HTTPException, Response

from src.advisor import routes, service
from src.advisor.models import (
    AnalystRequest,
    AnalystResponse,
    DecisionReport,
    EvidenceItem,
    Finding,
    ResearchAttempt,
    ResearchTrace,
)
from src.advisor.verification import CheckedResponse, VerificationReport


SNAPSHOT = "a" * 64
OTHER_SNAPSHOT = "b" * 64
NOW = 1_800_000_000.0


class ManualExecutor:
    """Accept jobs without racing assertions; execute their real worker later."""

    def __init__(self):
        self.tasks = []

    def submit(self, function, *args):
        self.tasks.append((function, args))

    def run_next(self):
        function, args = self.tasks.pop(0)
        function(*args)


class NoNetworkModel:
    def __init__(self, **kwargs):
        self.settings = kwargs

    def generate(self, *args, **kwargs):
        raise AssertionError("Service tests must not call a provider.")


def request(question="Should Arsenal recruit an attacker?", **kwargs):
    return AnalystRequest(
        discussion_id="discussion-1", mode="decision", question=question,
        **kwargs,
    )


def preview(cutoff=NOW - 300, kickoff=NOW + 300):
    return AnalystRequest(
        discussion_id="discussion-1", mode="match_preview",
        question="How should the teams approach the match?",
        team_a="France", team_b="Argentina",
        evidence_cutoff=datetime.fromtimestamp(cutoff, timezone.utc),
        match_kickoff=datetime.fromtimestamp(kickoff, timezone.utc),
    )


def insufficient(req, snapshot=SNAPSHOT):
    return CheckedResponse(response=AnalystResponse(
        request=req, status="insufficient_evidence", snapshot_sha256=snapshot,
        missing_information=["No eligible source establishes this conclusion."],
    ))


def partial(req, audit_error=None, audited=True):
    response = AnalystResponse(
        request=req, status="partial", snapshot_sha256=SNAPSHOT,
        missing_information=["Transfer costs are not established."],
        report=DecisionReport(
            action="Recruit an attacker",
            evidence=[EvidenceItem(
                id="S001", kind="source", message_ref="M001",
                source="https://example.test/scouting", excerpt="Depth is limited.",
            )],
            findings=[Finding(
                claim="Depth is limited.", evidence_ids=["S001"],
                support="source_backed",
            )],
        ),
    )
    audit = VerificationReport(
        input_sha256="c" * 64, claims=[], checks=[], error=audit_error,
    ) if audited else None
    return CheckedResponse(response=response, verification=audit)


@pytest.fixture
def worker(monkeypatch, tmp_path):
    executor = ManualExecutor()
    clock = {"now": NOW, "monotonic": 1000.0}
    monkeypatch.setattr(service, "_executor", executor)
    monkeypatch.setattr(service, "_pipeline_tag", "test-pipeline")
    monkeypatch.setattr(service, "_slots", BoundedSemaphore(2))
    monkeypatch.setattr(service, "_jobs", {})
    monkeypatch.setattr(service, "_finished_at", {})
    monkeypatch.setattr(service, "_inflight", {})
    monkeypatch.setattr(service, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(service, "_snapshot", lambda req: SNAPSHOT)
    monkeypatch.setattr(service, "OpenAICompatibleLLM", NoNetworkModel)
    monkeypatch.setattr(service, "analyze_verified", lambda req, **kw: insufficient(req))
    monkeypatch.setattr(service.time, "time", lambda: clock["now"])
    monkeypatch.setattr(service.time, "monotonic", lambda: clock["monotonic"])
    monkeypatch.setenv("LLM_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("LLM_MODEL", "test-analyst")
    monkeypatch.setenv("LLM_API_KEY", "test-only-key")
    monkeypatch.delenv("ADVISOR_VERIFIER_MODEL", raising=False)
    return executor, clock


def test_duplicate_jobs_share_capacity_and_return_detached_views(worker):
    executor, _ = worker
    first = service.submit_job(request())
    duplicate = service.submit_job(request(), force=True)
    assert duplicate.job_id == first.job_id
    assert len(executor.tasks) == 1
    first.request.question = "Changed by caller"
    assert service.get_job("discussion-1", first.job_id).request.question != first.request.question

    second = service.submit_job(request("Should the team keep its budget?"))
    with pytest.raises(service.CapacityError):
        service.submit_job(request("A third distinct question"))

    executor.run_next()
    assert service.get_job("discussion-1", duplicate.job_id).state == "completed"
    third = service.submit_job(request("A third distinct question"))
    assert third.job_id not in {first.job_id, second.job_id}


def test_cached_result_skips_work_and_force_recomputes(worker):
    executor, _ = worker
    first = service.submit_job(request())
    executor.run_next()
    cached = service.submit_job(request())
    assert cached.cached and cached.state == "completed"
    assert cached.result == service.get_job("discussion-1", first.job_id).result
    assert executor.tasks == []

    fresh = service.submit_job(request(), force=True)
    assert not fresh.cached and fresh.state == "queued"
    assert len(executor.tasks) == 1


def test_completed_cached_result_is_available_without_provider_credentials(worker, monkeypatch):
    executor, _ = worker
    service.submit_job(request())
    executor.run_next()
    monkeypatch.delenv("LLM_API_KEY")
    assert service.submit_job(request()).cached


def test_executor_submission_failure_rolls_back_job_and_capacity(worker, monkeypatch):
    executor, _ = worker

    class RefusingExecutor:
        def submit(self, *args):
            raise RuntimeError("Executor closed")

    monkeypatch.setattr(service, "_executor", RefusingExecutor())
    with pytest.raises(RuntimeError, match="closed"):
        service.submit_job(request())
    assert not service._jobs and not service._inflight

    monkeypatch.setattr(service, "_executor", executor)
    assert service.submit_job(request()).state == "queued"
    assert service.submit_job(request("Another question")).state == "queued"


def test_real_worker_lifecycle_keeps_running_request_deduplicated(worker, monkeypatch):
    started = Event()
    release = Event()

    def controlled_analysis(req, **kwargs):
        started.set()
        assert release.wait(3), "Test failed to release the controlled worker"
        return insufficient(req)

    monkeypatch.setattr(service, "_executor", None)
    monkeypatch.setattr(service, "analyze_verified", controlled_analysis)
    service.start_advisor_worker()
    first_executor = service._executor
    service.start_advisor_worker()
    assert service._executor is first_executor

    try:
        job = service.submit_job(request())
        assert started.wait(3), "Worker did not start"
        assert service.get_job("discussion-1", job.job_id).state == "running"
        assert service.submit_job(request()).job_id == job.job_id
    finally:
        release.set()
        service.shutdown_advisor_worker()

    assert service._executor is None
    assert service.get_job("discussion-1", job.job_id).state == "completed"
    with pytest.raises(RuntimeError, match="not running"):
        service.submit_job(request("After shutdown"))


@pytest.mark.parametrize("change", ["question", "snapshot", "model", "verifier", "code"])
def test_cache_does_not_cross_question_snapshot_model_or_code(worker, monkeypatch, change):
    executor, _ = worker
    service.submit_job(request())
    executor.run_next()
    req = request()
    if change == "question":
        req = request("A different question")
    elif change == "snapshot":
        monkeypatch.setattr(service, "_snapshot", lambda req: OTHER_SNAPSHOT)
    elif change == "model":
        monkeypatch.setenv("LLM_MODEL", "different-analyst")
    elif change == "verifier":
        monkeypatch.setenv("ADVISOR_VERIFIER_MODEL", "different-verifier")
    else:
        monkeypatch.setattr(service, "_pipeline_tag", "changed-code")
    result = service.submit_job(req)
    assert result.state == "queued" and not result.cached
    assert len(executor.tasks) == 1


def test_cache_roundtrip_expires_and_preview_lifetime_stops_at_kickoff(worker):
    _, clock = worker
    req = preview()
    result = insufficient(req)
    service._save_cache("preview-key", req, result)
    path = service.CACHE_DIR / "preview-key.json"
    assert json.loads(path.read_text())["expires_at"] == NOW + 300
    assert service._load_cache("preview-key", req, SNAPSHOT) == result
    clock["now"] = NOW + 300
    assert service._load_cache("preview-key", req, SNAPSHOT) is None
    assert not list(service.CACHE_DIR.glob("*.tmp"))


def test_researched_result_keeps_provenance_and_expires_after_one_hour(worker):
    _, clock = worker
    req = request()
    result = partial(req)
    result.response.research = ResearchTrace(
        evidence=[EvidenceItem(
            id="R001", kind="source", origin="web_page",
            source="https://example.test/article", excerpt="Depth is limited.",
            title="Squad analysis", content_kind="page_excerpt",
            retrieved_at=datetime.fromtimestamp(NOW, timezone.utc),
        )],
        attempts=[ResearchAttempt(
            tool="read_web_page", url="https://example.test/article",
            status="success", source_ids=["R001"],
        )],
    )
    service._save_cache("researched", req, result)
    clock["now"] = NOW + 3599
    restored = service._load_cache("researched", req, SNAPSHOT)
    assert restored == result
    assert restored.response.research.evidence[0].message_ref is None
    clock["now"] = NOW + 3600
    assert service._load_cache("researched", req, SNAPSHOT) is None


def test_cache_file_retention_is_bounded(worker, monkeypatch):
    monkeypatch.setattr(service, "MAX_CACHE_FILES", 2)
    for index in range(4):
        req = request(f"Question {index}")
        service._save_cache(f"key-{index}", req, insufficient(req))
    assert len(list(service.CACHE_DIR.glob("*.json"))) == 2
    assert not list(service.CACHE_DIR.glob("*.tmp"))


@pytest.mark.parametrize("contents", ["not JSON", "[]", "{}", '{"result": null}'])
def test_bad_cache_records_are_ignored(worker, contents):
    service.CACHE_DIR.mkdir()
    (service.CACHE_DIR / "bad.json").write_text(contents)
    assert service._load_cache("bad", request(), SNAPSHOT) is None


@pytest.mark.parametrize("change", ["request", "snapshot", "expiry", "key"])
def test_cache_metadata_mismatch_is_ignored(worker, change):
    req = request()
    service._save_cache("saved", req, insufficient(req))
    path = service.CACHE_DIR / "saved.json"
    record = json.loads(path.read_text())
    if change == "request":
        record["result"]["response"]["request"]["question"] = "Another question"
    elif change == "snapshot":
        record["result"]["response"]["snapshot_sha256"] = OTHER_SNAPSHOT
    elif change == "expiry":
        record["expires_at"] = NOW
    else:
        record["key"] = "another-key"
    path.write_text(json.dumps(record))
    assert service._load_cache("saved", req, SNAPSHOT) is None


@pytest.mark.parametrize("result_kind", ["analysis_failure", "audit_failure"])
def test_failed_analysis_or_audit_is_not_cached(worker, monkeypatch, result_kind):
    executor, _ = worker
    req = request()
    if result_kind == "analysis_failure":
        result = CheckedResponse(response=AnalystResponse(
            request=req, status="failed", snapshot_sha256=SNAPSHOT,
            error="Provider could not produce a draft.",
        ))
    else:
        result = partial(req, audit_error="Verifier failed.")
    monkeypatch.setattr(service, "analyze_verified", lambda req, **kw: result)
    job = service.submit_job(req)
    executor.run_next()
    finished = service.get_job(req.discussion_id, job.job_id)
    assert finished.state == "completed" and finished.result == result
    assert not list(service.CACHE_DIR.glob("*.json"))
    assert service.submit_job(req).state == "queued"


@pytest.mark.parametrize("defect", ["request", "result_snapshot", "before_snapshot", "after_snapshot", "unaudited"])
def test_worker_rejects_mismatched_or_unaudited_results(worker, monkeypatch, defect):
    executor, _ = worker
    req = request()
    job = service.submit_job(req)
    if defect == "request":
        monkeypatch.setattr(service, "analyze_verified", lambda req, **kw: insufficient(request("Wrong question")))
    elif defect == "result_snapshot":
        monkeypatch.setattr(service, "analyze_verified", lambda req, **kw: insufficient(req, OTHER_SNAPSHOT))
    elif defect == "before_snapshot":
        monkeypatch.setattr(service, "_snapshot", lambda req: OTHER_SNAPSHOT)
    elif defect == "after_snapshot":
        def changed_during_analysis(req, **kwargs):
            monkeypatch.setattr(service, "_snapshot", lambda req: OTHER_SNAPSHOT)
            return insufficient(req)
        monkeypatch.setattr(service, "analyze_verified", changed_during_analysis)
    else:
        monkeypatch.setattr(service, "analyze_verified", lambda req, **kw: partial(req, audited=False))
    executor.run_next()
    finished = service.get_job(req.discussion_id, job.job_id)
    assert finished.state == "failed" and finished.result is None and finished.error
    assert not list(service.CACHE_DIR.glob("*.json"))
    # The failed job releases capacity and is not reused as an active job.
    assert service.submit_job(req, force=True).job_id != job.job_id


def test_cache_write_failure_still_delivers_result(worker, monkeypatch):
    executor, _ = worker
    def fail_cache(*args):
        raise OSError("Disk full")
    monkeypatch.setattr(service, "_save_cache", fail_cache)
    job = service.submit_job(request())
    executor.run_next()
    assert service.get_job("discussion-1", job.job_id).state == "completed"


def test_job_lookup_protects_discussion_and_expires_terminal_jobs(worker):
    executor, clock = worker
    job = service.submit_job(request())
    with pytest.raises(FileNotFoundError):
        service.get_job("another-discussion", job.job_id)
    with pytest.raises(FileNotFoundError):
        service.get_job("discussion-1", "missing")
    executor.run_next()
    clock["monotonic"] += service.JOB_TTL + 1
    with pytest.raises(FileNotFoundError):
        service.get_job("discussion-1", job.job_id)


def test_completed_job_refuses_stale_snapshot(worker, monkeypatch):
    executor, _ = worker
    job = service.submit_job(request())
    executor.run_next()
    monkeypatch.setattr(service, "_snapshot", lambda req: OTHER_SNAPSHOT)
    with pytest.raises(RuntimeError, match="older discussion snapshot"):
        service.get_job("discussion-1", job.job_id)


@pytest.mark.parametrize("req", [preview(kickoff=NOW), preview(cutoff=NOW + 1)])
def test_preview_submission_rejects_started_matches_and_future_cutoff(worker, req):
    executor, _ = worker
    with pytest.raises(ValueError):
        service.submit_job(req)
    assert not executor.tasks


def test_preview_expiring_during_analysis_is_not_published(worker, monkeypatch):
    executor, clock = worker
    req = preview()
    def finish_after_kickoff(req, **kwargs):
        clock["now"] = NOW + 301
        return insufficient(req)
    monkeypatch.setattr(service, "analyze_verified", finish_after_kickoff)
    job = service.submit_job(req)
    executor.run_next()
    assert service._jobs[job.job_id].state == "failed"
    assert not list(service.CACHE_DIR.glob("*.json"))
    with pytest.raises(ValueError, match="started"):
        service.get_job("discussion-1", job.job_id)


def test_completed_preview_cannot_be_read_after_kickoff(worker):
    executor, clock = worker
    job = service.submit_job(preview())
    executor.run_next()
    assert service.get_job("discussion-1", job.job_id).state == "completed"
    clock["now"] = NOW + 301
    with pytest.raises(ValueError, match="started"):
        service.get_job("discussion-1", job.job_id)


def test_unconfigured_model_does_not_accept_uncached_jobs(worker, monkeypatch):
    executor, _ = worker
    monkeypatch.delenv("LLM_API_KEY")
    with pytest.raises(RuntimeError, match="Configure"):
        service.submit_job(request())
    assert not executor.tasks and not service._jobs


def test_route_submission_and_cache_status(worker):
    executor, _ = worker
    body = routes.SubmitAdvisorRequest(request=request())
    response = Response()
    first = routes.create_advisor_job("discussion-1", body, response)
    assert response.status_code == 202 and first.state == "queued"
    executor.run_next()
    cached = routes.create_advisor_job("discussion-1", body, response)
    assert response.status_code == 200 and cached.cached
    assert routes.read_advisor_job("discussion-1", first.job_id).state == "completed"
    with pytest.raises(HTTPException) as caught:
        routes.create_advisor_job("different", body, Response())
    assert caught.value.status_code == 422


@pytest.mark.parametrize("failure, status", [
    (FileNotFoundError("Missing discussion"), 404),
    (ValueError("Invalid evidence"), 422),
    (service.CapacityError("Busy"), 429),
    (RuntimeError("Worker unavailable"), 503),
])
def test_submit_route_maps_failures(monkeypatch, failure, status):
    def fail(*args, **kwargs):
        raise failure
    monkeypatch.setattr(routes, "submit_job", fail)
    with pytest.raises(HTTPException) as caught:
        routes.create_advisor_job(
            "discussion-1", routes.SubmitAdvisorRequest(request=request()), Response(),
        )
    assert caught.value.status_code == status
    assert caught.value.detail == str(failure)
    if status == 429:
        assert caught.value.headers == {"Retry-After": "3"}


@pytest.mark.parametrize("failure, status", [
    (FileNotFoundError("Job missing"), 404),
    (ValueError("Match started"), 409),
    (RuntimeError("Snapshot changed"), 409),
])
def test_lookup_route_maps_failures(monkeypatch, failure, status):
    def fail(*args):
        raise failure
    monkeypatch.setattr(routes, "get_job", fail)
    with pytest.raises(HTTPException) as caught:
        routes.read_advisor_job("discussion-1", "job-id")
    assert caught.value.status_code == status
    assert caught.value.detail == str(failure)
