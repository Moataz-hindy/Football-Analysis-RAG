"""Cost and correctness regressions; all model calls are stubs."""
import json
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.advisor import core, service
from src.advisor.routes import router
from src.discussion.types import DiscussionResult


@pytest.fixture
def discussion():
    return DiscussionResult.from_dict({
        "config": {"discussion_id": "arsenal", "topic": "Should Arsenal buy a striker?",
                   "metadata": {"status": "completed"}},
        "messages": [{"sender_id": "tactical", "round_num": 0, "content": "Consider the budget.",
                      "sources_used": [{"source": "https://example.com/report", "content": "Squad report."}]}],
    })


@pytest.fixture
def setup(monkeypatch, tmp_path, discussion):
    monkeypatch.setattr(service, "CACHE_PATH", tmp_path / "advisor.sqlite3")
    monkeypatch.setattr(service, "get_saved_discussion", lambda _: discussion)
    monkeypatch.setattr(service, "get_discussion_status_record", lambda _: SimpleNamespace(status="completed"))
    for key, value in {"LLM_API_KEY": "test", "LLM_BASE_URL": "https://example.test/v1", "LLM_MODEL": "stub"}.items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv("ADVISOR_MODEL", raising=False)
    calls = []

    class Client:
        def __init__(self, **kwargs):
            assert "max_retries" not in kwargs
            assert "pace_waits" not in kwargs
            assert kwargs["use_pacer"] is False
            assert kwargs["max_tokens"] in (700, 2500)
            self.structured = kwargs["max_tokens"] == 2500
            self.last_response = SimpleNamespace(
                choices=[SimpleNamespace(finish_reason="stop")],
                usage=SimpleNamespace(model_dump=lambda: {"prompt_tokens": 350, "completion_tokens": 80}),
            )

        def generate(self, messages, tools=None, **kwargs):
            assert tools is None
            calls.append(messages)
            if self.structured:
                assert kwargs["response_format"] == service.decision_core.decision_response_format()
                return {"content": json.dumps(decision_payload())}
            return {"content": "A striker may help, provided the fee leaves room for other needs. [S1]"}

    monkeypatch.setattr(service, "OpenAICompatibleLLM", Client)
    return calls


def test_cached_across_requests_and_read_never_generates(setup):
    assert service.get_opinion("arsenal")["state"] == "missing"
    assert not setup
    first = service.create_opinion("arsenal")
    assert first["state"] == "completed"
    assert first["usage"]["prompt_tokens"] == 350
    assert first["sources"][0]["id"] == "S1"
    assert service.create_opinion("arsenal")["cached"]
    assert service.create_opinion("arsenal", retry_failed=True)["cached"]
    assert service.get_opinion("arsenal")["opinion"] == first["opinion"]
    assert len(setup) == 1


def test_only_real_content_changes_invalidate_cache(setup, discussion):
    service.create_opinion("arsenal")
    discussion.config.metadata["analytics_ready"] = True
    service.create_opinion("arsenal")
    assert len(setup) == 1
    discussion.messages[0].content = "A different position."
    service.create_opinion("arsenal")
    assert len(setup) == 2


def test_failures_persist_but_explicit_retries_are_not_permanently_locked(setup, monkeypatch):
    def fail(*args):
        setup.append("failed")
        raise RuntimeError("provider failure")
    monkeypatch.setattr(service, "generate_opinion", fail)
    first = service.create_opinion("arsenal")
    assert first["state"] == "failed" and first["retryable"]
    service.create_opinion("arsenal")
    assert len(setup) == 1
    assert service.create_opinion("arsenal", retry_failed=True)["retryable"]
    service.create_opinion("arsenal", retry_failed=True)
    assert len(setup) == 3
    assert len(service.get_opinion("arsenal")["attempt_usage"]) == 3


def test_retry_preserves_previous_token_usage(setup, monkeypatch):
    original = service.generate_opinion
    def invalid(*args):
        return {**original(*args), "state": "failed", "opinion": None, "error": "Invalid output"}
    monkeypatch.setattr(service, "generate_opinion", invalid)
    service.create_opinion("arsenal")
    monkeypatch.setattr(service, "generate_opinion", original)
    service.create_opinion("arsenal", retry_failed=True)
    records = service.get_opinion("arsenal")["attempt_usage"]
    assert [record["usage"]["completion_tokens"] for record in records] == [80, 80]


def test_concurrent_requests_share_durable_claim(setup, monkeypatch):
    entered, release = Event(), Event()
    original = service.generate_opinion
    def slow(*args):
        entered.set()
        assert release.wait(5)
        return original(*args)
    monkeypatch.setattr(service, "generate_opinion", slow)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(service.create_opinion, "arsenal")
        try:
            assert entered.wait(5)
            assert service.create_opinion("arsenal")["state"] == "running"
            assert service.get_opinion("arsenal")["state"] == "running"
        finally:
            release.set()
        assert first.result()["state"] == "completed"
    assert len(setup) == 1


def test_incomplete_discussion_never_calls_model(setup, monkeypatch):
    monkeypatch.setattr(service, "get_discussion_status_record", lambda _: SimpleNamespace(status="running"))
    with pytest.raises(service.NotReady):
        service.create_opinion("arsenal")
    assert not setup


def test_snapshot_change_during_generation_rejects_stale_opinion(setup, monkeypatch, discussion):
    original = service.generate_opinion
    def change(*args):
        result = original(*args)
        discussion.messages[0].content += " Updated."
        return result
    monkeypatch.setattr(service, "generate_opinion", change)
    result = service.create_opinion("arsenal")
    assert result["state"] == "failed" and result["opinion"] is None


@pytest.mark.parametrize("text,finish", [("An unsupported reference [S99]", "stop"), ("Cut off", "length"), ("", "stop")])
def test_bad_output_is_rejected_without_repair(discussion, text, finish):
    calls = []
    client = SimpleNamespace(last_response=SimpleNamespace(choices=[SimpleNamespace(finish_reason=finish)]))
    def generate(*args, **kwargs):
        calls.append(1)
        return {"content": text}
    client.generate = generate
    assert core.generate_opinion(discussion, client)["state"] == "failed"
    assert len(calls) == 1


def test_input_budget_balances_agents_and_deduplicates_sources(discussion):
    raw = discussion.messages[0].to_dict()
    from src.discussion.types import DiscussionMessage
    discussion.messages = [DiscussionMessage.from_dict({**raw, "sender_id": f"a{agent}",
        "round_num": round_num, "content": "text " * 1500}) for round_num in range(10) for agent in range(6)]
    messages, sources = core.build_input(discussion)
    assert sum(len(m["content"]) for m in messages) <= core.MAX_INPUT_CHARS
    data = json.loads(messages[1]["content"])
    assert {m["speaker"] for m in data["messages"]} == {f"a{i}" for i in range(6)}
    assert data["messages_omitted"] > 0
    assert len(sources) == 1


def test_no_sources_keeps_a_tentative_opinion(setup, discussion):
    discussion.messages[0].sources_used = []
    client = SimpleNamespace(generate=lambda *a, **k: {"content": "Tentatively, a striker could help; the discussion supplies no source evidence."})
    result = core.generate_opinion(discussion, client)
    assert result["state"] == "completed"
    assert not result["evidence_available"]


def test_routes_read_and_generate_separately(setup):
    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as client:
        assert client.get("/discussions/arsenal/advisor").json()["state"] == "missing"
        assert not setup
        assert client.post("/discussions/arsenal/advisor", json={}).json()["state"] == "completed"
        assert client.post("/discussions/arsenal/advisor", json={"force": True}).status_code == 422
        assert client.get("/discussions/arsenal/advisor").json()["state"] == "completed"
        assert len(setup) == 1


def test_real_app_reads_saved_discussion_and_reuses_advisor(setup, monkeypatch, tmp_path, discussion):
    """Exercise registered routes, real persistence/status lookup and SQLite caching."""
    from src.api.main import app
    from src.api.services import discussion_service
    from src.discussion.persistence import save_discussion

    monkeypatch.setattr(discussion_service, "OUTPUTS_DIR", tmp_path)
    monkeypatch.setattr(service, "get_saved_discussion", discussion_service.get_saved_discussion)
    monkeypatch.setattr(service, "get_discussion_status_record", discussion_service.get_discussion_status_record)
    save_discussion(discussion, output_dir=tmp_path)
    with TestClient(app) as client:
        assert client.get('/discussions/arsenal').status_code == 200
        assert client.get('/discussions/arsenal/status').json()['status'] == 'completed'
        assert client.get('/discussions/arsenal/advisor').json()['state'] == 'missing'
        assert not setup
        generated = client.post('/discussions/arsenal/advisor', json={})
        assert generated.status_code == 200
        assert generated.json()['state'] == 'completed'
        assert generated.json()['sources'][0]['id'] == 'S1'
    # A new browser/API session still reads the durable result without regeneration.
    with TestClient(app) as reopened:
        assert reopened.get('/discussions/arsenal/advisor').json()['opinion'] == generated.json()['opinion']
        assert reopened.post('/discussions/arsenal/advisor', json={}).json()['cached']
        assert reopened.get('/discussions/unknown/advisor').status_code == 404
    assert len(setup) == 1


@pytest.mark.parametrize("kind", ["opinion", "decision"])
def test_advisor_recovers_after_eight_503s_and_caches_output(setup, monkeypatch, kind):
    import httpx
    from unittest.mock import MagicMock
    from openai import APIStatusError
    from src.agent import llm as llm_module

    monkeypatch.setattr(service, 'OpenAICompatibleLLM', llm_module.OpenAICompatibleLLM)
    monkeypatch.setenv('LLM_MAX_RETRIES', '8')
    monkeypatch.setenv('LLM_RETRY_DELAYS_SECONDS', '5,10,20,40,60,90,120,180')
    monkeypatch.setenv('LLM_RETRY_MAX_WAIT_SECONDS', '300')
    monkeypatch.setenv('LLM_RETRY_WAIT_BUDGET_SECONDS', '600')
    monkeypatch.setenv('LLM_PACE_WAITS', '')
    sdk = MagicMock()
    monkeypatch.setattr(llm_module, 'OpenAI', lambda **kwargs: sdk)
    sleep = MagicMock()
    monkeypatch.setattr(llm_module.time, 'sleep', sleep)
    monkeypatch.setattr(llm_module.random, 'uniform', lambda *args: 0)
    failure = APIStatusError('Unavailable', response=httpx.Response(
        503, request=httpx.Request('POST', 'https://example.test')), body=None)
    answer = SimpleNamespace(choices=[SimpleNamespace(finish_reason='stop',
        message=SimpleNamespace(content=json.dumps(decision_payload()) if kind == 'decision' else 'Consider a striker if the fee fits the budget. [S1]', tool_calls=[]))],
        usage=None)
    sdk.chat.completions.create.side_effect = [failure] * 8 + [answer]
    result = service.create_opinion('arsenal', kind=kind)
    assert result['state'] == 'completed'
    assert 'striker' in (result['opinion'] if kind == 'opinion' else result['decision']['definitive_ruling'])
    assert [call.args[0] for call in sleep.call_args_list] == [5, 10, 20, 40, 60, 90, 120, 180]
    assert service.create_opinion('arsenal', retry_failed=True, kind=kind)['cached']
    assert sdk.chat.completions.create.call_count == 9
    for call in sdk.chat.completions.create.call_args_list:
        if kind == "decision":
            assert call.kwargs["response_format"] == service.decision_core.decision_response_format()
        else:
            assert "response_format" not in call.kwargs


def test_renewed_claim_survives_old_five_minute_timeout(setup, monkeypatch):
    _, _, _, key = service._context('arsenal')
    clock = SimpleNamespace(time=lambda: 1000)
    monkeypatch.setattr(service, 'time', clock)
    conn = service._connect()
    conn.execute('INSERT INTO opinions VALUES (?, ?, ?, ?, ?)',
                 (key, 'running', 2, 600, json.dumps({'state': 'running'})))
    conn.commit()
    conn.close()
    assert service.get_opinion('arsenal')['retryable']
    service._renew_claim(key, 2)
    assert service.get_opinion('arsenal')['state'] == 'running'
    assert service.create_opinion('arsenal', retry_failed=True)['state'] == 'running'
    assert not setup
    clock.time = lambda: 1400
    # A heartbeat belonging to an older attempt cannot renew a newer claim.
    service._renew_claim(key, 1)
    assert service.get_opinion('arsenal')['state'] == 'failed'


def test_heartbeat_runs_and_stops_with_generation(setup, monkeypatch):
    from unittest.mock import MagicMock
    tick = Event()
    renew = MagicMock(side_effect=lambda *args: tick.set())
    monkeypatch.setattr(service, '_renew_claim', renew)
    monkeypatch.setattr(service, 'HEARTBEAT_SECONDS', 0.01)
    with service._keep_claim_alive('key', 3):
        assert tick.wait(2)
    renew.assert_called_with('key', 3)


def decision_payload():
    return {
        "topic_type": "Action Directive", "verdict_badge": "CONDITIONAL APPROVAL",
        "definitive_ruling": "Consider a striker if the fee fits the budget. [S1]",
        "confidence_score": None, "deciding_factor": "Check squad needs. [S1]",
        "action_plan": ["Verify the budget", "Compare profiles", "Assess availability"],
        "primary_risk": "Unknown price", "mitigation_strategy": "Set a budget first",
        "stakeholder_impacts": {"sporting_impact": "Potential depth", "squad_impact": "Review roles",
                                "strategic_impact": "Preserve flexibility"},
    }


def test_real_app_advisor_endpoints_are_distinct_and_read_only(setup):
    from src.api.main import app
    from src.api.routes import router as api_router
    paths = ["/discussions/{discussion_id}/advisor", "/discussions/{discussion_id}/advisor/decision"]
    for path in paths:
        for method in ("GET", "POST"):
            assert sum(route.path == path and method in getattr(route, "methods", set())
                       for route in [*api_router.routes, *router.routes]) == 1
    with TestClient(app) as client:
        for suffix in ("advisor", "advisor/decision"):
            assert client.get(f"/discussions/arsenal/{suffix}").json()["state"] == "missing"
        assert not setup
        opinion = client.post("/discussions/arsenal/advisor", json={}).json()
        decision = client.post("/discussions/arsenal/advisor/decision", json={}).json()
        assert opinion["state"] == decision["state"] == "completed"
        assert "striker" in decision["decision"]["definitive_ruling"]
        assert decision["sources"][0]["id"] == "S1"
        assert opinion["cache_key"] != decision["cache_key"]
        assert client.post("/discussions/arsenal/advisor/decision", json={}).json()["cached"]
        assert len(setup) == 2


@pytest.mark.parametrize("bad", ["not JSON", "{}", '{"definitive_ruling":"invented"}',
                                   json.dumps({**decision_payload(), "confidence_score": 8}),
                                   json.dumps({**decision_payload(), "deciding_factor": "Unsupported [S99]"})])
def test_invalid_structured_decision_never_becomes_a_canned_ruling(discussion, bad):
    from src.analytics.advisor import generate_advisor_decision
    result = generate_advisor_decision(discussion, SimpleNamespace(generate=lambda *a, **k: {"content": bad}))
    assert result["state"] == "failed"
    assert result["decision"] is None


def test_structured_failure_retries_explicitly_and_snapshot_invalidates(setup, monkeypatch, discussion):
    original = service.decision_core.generate_advisor_decision
    def fail(*args):
        raise RuntimeError("503 provider unavailable")
    monkeypatch.setattr(service.decision_core, "generate_advisor_decision", fail)
    failed = service.create_opinion("arsenal", kind="decision")
    assert failed["state"] == "failed" and failed["retryable"]
    assert failed["decision"] is None
    monkeypatch.setattr(service.decision_core, "generate_advisor_decision", original)
    assert service.create_opinion("arsenal", kind="decision")["state"] == "failed"
    assert not setup
    assert service.create_opinion("arsenal", retry_failed=True, kind="decision")["state"] == "completed"
    discussion.messages[0].content += " New evidence changes the premise."
    assert service.get_opinion("arsenal", kind="decision")["state"] == "missing"
    assert service.create_opinion("arsenal", kind="decision")["state"] == "completed"
    assert len(setup) == 2


@pytest.mark.parametrize('text,finish,code,field', [
    ('not JSON', 'stop', 'invalid_json', None),
    ('{}', 'stop', 'invalid_fields', 'definitive_ruling'),
    (json.dumps({**decision_payload(), 'confidence_score': 'high'}), 'stop', 'invalid_fields', 'confidence_score'),
    (json.dumps({**decision_payload(), 'deciding_factor': 'Unsupported [S99]'}), 'stop', 'unknown_citation', None),
    ('', 'stop', 'empty_response', None),
    ('{"topic_type":', 'length', 'truncated', None),
])
def test_decision_failure_explains_exact_validation_category(discussion, text, finish, code, field, caplog):
    from src.analytics.advisor import generate_advisor_decision
    client = SimpleNamespace(generate=lambda *a, **k: {'content': text},
                             last_response=SimpleNamespace(choices=[SimpleNamespace(finish_reason=finish)]))
    result = generate_advisor_decision(discussion, client)
    assert result['state'] == 'failed'
    assert result['error_code'] == code
    assert result['finish_reason'] == finish
    assert 'debate does not need to run again' in result['error']
    if field:
        assert field in [item['field'] for item in result['validation_errors']]
    assert 'Squad report.' not in caplog.text
    assert 'Should Arsenal buy' not in caplog.text


def test_structured_contract_replaces_old_failed_cache_but_preserves_opinion(setup):
    from src.analytics.advisor import decision_response_format
    schema = decision_response_format()['json_schema']['schema']
    assert schema['additionalProperties'] is False
    assert set(schema['required']) == set(schema['properties'])
    assert 'Historical Ruling' in schema['properties']['topic_type']['enum']
    assert schema['properties']['action_plan']['minItems'] == 3
    assert schema['properties']['action_plan']['maxItems'] == 3
    assert schema['$defs']['Impacts']['additionalProperties'] is False
    # Recreate the pre-fix cache key exactly: the old request had no response format.
    import os
    discussion, model, snapshot, new_key = service._context('arsenal', 'decision')
    old_key = core.fingerprint({'discussion_id': 'arsenal', 'snapshot': snapshot, 'model': model,
        'endpoint': os.environ['LLM_BASE_URL'], 'prompt': service.decision_core.ADVISOR_SYSTEM_PROMPT,
        'input_version': 1, 'output_tokens': service.decision_core.MAX_OUTPUT_TOKENS})
    conn = service._connect()
    conn.execute('INSERT INTO opinions VALUES (?, ?, ?, ?, ?)',
                 (old_key, 'failed', 2, 1000, json.dumps({'state': 'failed', 'decision': None})))
    conn.commit()
    conn.close()
    assert old_key != new_key
    assert service.get_opinion('arsenal', kind='decision')['state'] == 'missing'
    assert service.create_opinion('arsenal', kind='decision')['state'] == 'completed'
    assert service.create_opinion('arsenal', kind='decision')['cached']
    opinion = service.create_opinion('arsenal')
    assert service.create_opinion('arsenal')['cache_key'] == opinion['cache_key']
    assert len(setup) == 2
