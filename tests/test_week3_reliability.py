"""Regression checks for real failure paths, using no live API or database."""
import json
from dataclasses import asdict
from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx
import psycopg2
import pytest
from openai import APIConnectionError, APIStatusError, RateLimitError

from src.agent.agent import Agent, AgentTurnError
from src.agent.llm import OpenAICompatibleLLM
from src.agent.memory import ConversationMemory
from src.agent.retrieval import RAGRetrieval
from src.agent.tool_registery import ToolRegistry
from src.agent.types import RetrievedSource
from src.discussion import run_discussion as runner
from src.discussion.persistence import load_discussion, save_discussion_from_state
from src.rag import search as search_module
from src.tools.calculator import CalculatorTool
from src.tools.knowledge_search import KnowledgeSearchTool


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    # Fail instead of accidentally using credentials from the developer's .env.
    def blocked(*args, **kwargs):
        raise AssertionError("Live I/O is forbidden in these regression tests")
    monkeypatch.setattr(psycopg2, "connect", blocked)
    monkeypatch.setattr(httpx.Client, "send", blocked)


def source():
    return RetrievedSource("Compact lines deny space", "https://example.test/low-block", .9,
                           {"doc_id": "doc_demo", "chunk_index": 2, "title": "Low block"})


def make_agent(llm, retrieval=None):
    retrieval = retrieval or SimpleNamespace(retrieve=lambda query: [source()])
    return Agent(SimpleNamespace(
        persona=SimpleNamespace(name="Analyst", background="Coach", stance="Support",
                                communication_style="Clear", expertise=["Tactics"], priorities=["Evidence"]),
        memory=ConversationMemory(llm=llm), llm=llm, retrieval=retrieval,
        tools=ToolRegistry([KnowledgeSearchTool(retrieval=retrieval), CalculatorTool()]),
    ))


def test_missing_embedding_config_is_a_catchable_error(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(search_module.RetrievalError):
        search_module.get_client()


def test_database_login_failure_is_catchable(monkeypatch):
    def fail(**kwargs):
        raise psycopg2.OperationalError("authentication rejected")
    monkeypatch.setattr(psycopg2, "connect", fail)
    with pytest.raises(search_module.RetrievalError, match="connect to Postgres"):
        search_module.get_connection()


def test_vector_initialization_failure_closes_connection(monkeypatch):
    conn = MagicMock()
    monkeypatch.setattr(psycopg2, "connect", lambda **kwargs: conn)
    monkeypatch.setattr(search_module, "register_vector", MagicMock(side_effect=RuntimeError("extension missing")))
    with pytest.raises(search_module.RetrievalError):
        search_module.get_connection()
    conn.close.assert_called_once()


@pytest.mark.parametrize("failure", [None, "embedding", "query"])
def test_search_closes_owned_connection_on_success_and_failure(monkeypatch, failure):
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value.fetchall.return_value = []
    monkeypatch.setattr(search_module, "get_connection", lambda: conn)
    embed = MagicMock(return_value=[.1])
    if failure == "embedding":
        embed.side_effect = RuntimeError("provider unavailable")
    if failure == "query":
        conn.cursor.return_value.__enter__.return_value.execute.side_effect = psycopg2.OperationalError("lost database")
    monkeypatch.setattr(search_module, "embed_query", embed)
    if failure:
        with pytest.raises(search_module.RetrievalError):
            search_module.search("low block", client=object(), model="test")
    else:
        assert search_module.search("low block", client=object(), model="test") == []
    conn.close.assert_called_once()


def test_caller_owned_connection_is_not_closed(monkeypatch):
    conn = MagicMock()
    monkeypatch.setattr(search_module, "embed_query", MagicMock(side_effect=RuntimeError("failed")))
    with pytest.raises(search_module.RetrievalError):
        search_module.search("q", client=object(), model="test", conn=conn)
    conn.close.assert_not_called()


def test_no_results_and_failed_retrieval_are_different(monkeypatch):
    monkeypatch.setattr("src.agent.retrieval.search", lambda *a, **k: [])
    assert RAGRetrieval().retrieve("q") == []
    def fail(*args, **kwargs):
        raise search_module.RetrievalError("database unavailable")
    monkeypatch.setattr("src.agent.retrieval.search", fail)
    with pytest.raises(search_module.RetrievalError):
        RAGRetrieval().retrieve("q")


def test_initial_search_and_tool_search_keep_all_source_metadata():
    llm = MagicMock()
    llm.generate.side_effect = [
        {"tool_calls": [{"name": "knowledge_search", "arguments": {"query": "verify"}}]},
        {"content": "STANCE: support\nREASONING: compact lines\nSOURCES USED: doc_demo"},
    ]
    result = make_agent(llm).run("low block")
    assert [call.arguments["query"] for call in result.tool_calls] == ["low block", "verify"]
    assert result.tool_calls[0].metadata["mode"] == "automatic_initial"
    assert len(result.sources) == 2
    assert all(s.metadata["chunk_index"] == 2 for s in result.sources)
    assert result.tool_calls[1].result[0]["metadata"]["doc_id"] == "doc_demo"


@pytest.mark.parametrize("initial", [True, False])
def test_failed_search_preserves_attempt_and_stops_agent(initial):
    retrieval = MagicMock()
    retrieval.retrieve.side_effect = search_module.RetrievalError("database unavailable")
    llm = MagicMock()
    llm.generate.return_value = {"tool_calls": [{"name": "knowledge_search", "arguments": {"query": "verify claim"}}]}
    agent = make_agent(llm, retrieval)
    with pytest.raises(AgentTurnError) as info:
        if initial:
            agent.run("initial question")
        else:
            agent.run_discussion_turn("respond", [{"sender": "other", "content": "claim"}])
    event = info.value.tool_calls[-1]
    assert event.status == "failed"
    assert event.error == "database unavailable"
    assert event.result is None
    assert event.timestamp
    assert agent.memory.history == []
    assert llm.generate.call_count == (0 if initial else 1)


def test_memory_uses_chat_adapter_and_keeps_history_until_success(monkeypatch):
    llm = MagicMock()
    llm.generate.side_effect = [RuntimeError("rate limit"), {"content": "Combined older opinions"}]
    factory = MagicMock(return_value=llm)
    monkeypatch.setattr("src.agent.memory.OpenAICompatibleLLM", factory)
    memory = ConversationMemory(max_turns=1)
    a, b, c = ({"task": x, "response": x} for x in ["a", "b", "c"])
    memory.add(a)
    memory.add(b)
    assert memory.history == [a, b]
    assert memory.summary == "No previous context."
    memory.add(c)
    assert memory.history == [c]
    assert memory.summary == "Combined older opinions"
    factory.assert_called_once()
    assert "'task': 'a'" in llm.generate.call_args.kwargs["messages"][1]["content"]
    assert "'task': 'b'" in llm.generate.call_args.kwargs["messages"][1]["content"]
    assert llm.generate.call_args.kwargs["tools"] is None


@pytest.mark.parametrize("response", [{"content": " "}, {"content": "text", "tool_calls": [{}]}])
def test_invalid_memory_summary_retains_originals(response):
    llm = MagicMock()
    llm.generate.return_value = response
    memory = ConversationMemory(max_turns=1, llm=llm)
    for name in ["a", "b"]:
        memory.add({"task": name, "response": name})
    assert len(memory.history) == 2
    assert memory.summary == "No previous context."


def sdk_response():
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="answer", tool_calls=[]))])


def api_error(status=429, headers=None, message="rate limit"):
    response = httpx.Response(status, headers=headers, request=httpx.Request("POST", "https://example.test/v1"))
    cls = RateLimitError if status == 429 else APIStatusError
    return cls(message, response=response, body=None)


@pytest.fixture
def adapter(monkeypatch):
    monkeypatch.setenv("LLM_RETRY_MAX_WAIT_SECONDS", "120")
    llm = OpenAICompatibleLLM(api_key="fake", base_url="https://example.test/v1", model="fake", max_retries=2)
    llm._client = MagicMock()
    return llm


@pytest.mark.parametrize("error,delay", [
    (api_error(headers={"Retry-After": "4"}), 5),
    (api_error(headers={"retry-after-ms": "1500"}), 2.5),
    (api_error(message="Please try again in 13.9s"), 14.9),
    (api_error(status=503), 2),
    (APIConnectionError(request=httpx.Request("POST", "https://example.test")), 2),
])
def test_transient_failure_retries_same_request(adapter, monkeypatch, error, delay):
    sleep = MagicMock()
    monkeypatch.setattr("src.agent.llm.time.sleep", sleep)
    create = adapter._client.chat.completions.create
    create.side_effect = [error, sdk_response()]
    assert adapter.generate([{"role": "user", "content": "q"}])["content"] == "answer"
    sleep.assert_called_once_with(delay)
    assert create.call_count == 2
    assert create.call_args_list[0] == create.call_args_list[1]


def test_exhausted_retries_stop(adapter, monkeypatch):
    sleep = MagicMock()
    monkeypatch.setattr("src.agent.llm.time.sleep", sleep)
    adapter._client.chat.completions.create.side_effect = api_error()
    with pytest.raises(RateLimitError):
        adapter.generate([{"role": "user", "content": "q"}])
    assert adapter._client.chat.completions.create.call_count == 3
    assert sleep.call_count == 2


@pytest.mark.parametrize("error", [api_error(400), api_error(401), api_error(headers={"retry-after": "3600"})])
def test_permanent_error_or_long_quota_wait_stops_immediately(adapter, monkeypatch, error):
    sleep = MagicMock()
    monkeypatch.setattr("src.agent.llm.time.sleep", sleep)
    adapter._client.chat.completions.create.side_effect = error
    with pytest.raises(APIStatusError):
        adapter.generate([{"role": "user", "content": "q"}])
    sleep.assert_not_called()
    assert adapter._client.chat.completions.create.call_count == 1


class ScriptedLLM:
    """Real Agent orchestration with fake model responses and local fake evidence."""
    model, temperature, base_url, max_tokens = "offline", 0, "https://example.test", 256

    def __init__(self, fail_at=None, interrupt=False):
        self.finished = 0
        self.fail_at = fail_at
        self.interrupt = interrupt

    def generate(self, messages, tools=None):
        if self.finished == self.fail_at:
            if self.interrupt:
                raise KeyboardInterrupt()
            raise RuntimeError("model unavailable")
        if messages[-1]["role"] != "tool":
            return {"tool_calls": [
                {"name": "knowledge_search", "arguments": {"query": "verify low block"}},
                {"name": "calculator", "arguments": {"expression": "2+2"}},
            ]}
        self.finished += 1
        return {"content": "STANCE: support\nREASONING: compact lines deny space\nSOURCES USED: doc_demo"}


@pytest.mark.parametrize("fail_at,interrupt,status,count", [
    (None, False, "completed", 24),
    (8, False, "failed_partial", 8),
    (8, True, "interrupted", 8),
])
def test_full_runner_checkpoints_and_roundtrips_evidence(tmp_path, monkeypatch, fail_at, interrupt, status, count):
    monkeypatch.setattr(runner, "OpenAICompatibleLLM", lambda: ScriptedLLM(fail_at, interrupt))
    monkeypatch.setattr(runner, "RAGRetrieval", lambda **kwargs: SimpleNamespace(retrieve=lambda query: [source()]))
    checkpoints = []
    original = runner.save_discussion_from_state
    def record(**kwargs):
        path = original(**kwargs)
        data = json.loads(open(path).read())
        checkpoints.append((data["config"]["metadata"]["status"], len(data["messages"])))
        return path
    monkeypatch.setattr(runner, "save_discussion_from_state", record)
    result = runner.main(["--discussion-id", "offline-demo", "--output-dir", str(tmp_path)])
    assert result == (0 if fail_at is None else 1)
    history = load_discussion(tmp_path / "offline-demo.json")
    assert history.config.metadata["status"] == status
    assert len(history.messages) == count
    assert len(history.opinions) == count
    assert checkpoints[:-1] == [("running", n) for n in range(1, count + 1)]
    assert history.config.metadata["last_completed_round"] == (3 if fail_at is None else 0)
    assert sum(len(m.retrieval_events) for m in history.messages) == count + 6
    for message in history.messages:
        tools = message.metadata["tool_events"]
        assert any(t["name"] == "calculator" and t["result"] == 4 for t in tools)
        assert all(e.metadata["tool_name"] == "knowledge_search" for e in message.retrieval_events)
        assert message.retrieval_events[-1].metadata["results"][0]["metadata"]["doc_id"] == "doc_demo"
        assert message.sources_used[-1].metadata["chunk_index"] == 2
    if fail_at is not None:
        assert history.metadata.extra["failed_turns"][0]["round_num"] == 1


def test_failed_tool_event_survives_partial_save(tmp_path):
    from src.discussion.models import DiscussionState
    from src.discussion.orchestrator import DiscussionOrchestrator, DiscussionRunError
    from src.discussion.router import GraphRouter
    retrieval = MagicMock()
    retrieval.retrieve.side_effect = search_module.RetrievalError("database unavailable")
    graph = GraphRouter()
    agents = {name: make_agent(MagicMock(), retrieval) for name in graph.graph.graph.nodes}
    with pytest.raises(DiscussionRunError) as info:
        DiscussionOrchestrator(agents, graph).run("topic")
    path = save_discussion_from_state(info.value.state, graph, output_dir=tmp_path)
    history = load_discussion(path)
    event = history.metadata.extra["failed_turns"][0]["tool_events"][0]
    assert event["status"] == "failed"
    assert "topic" in event["arguments"]["query"]
    assert event["error"] == "database unavailable"
    assert history.messages == []


def test_runner_refuses_to_overwrite_previous_run(tmp_path, monkeypatch):
    path = tmp_path / "existing.json"
    path.write_text("old history")
    with pytest.raises(ValueError, match="already exists"):
        runner.main(["--discussion-id", "existing", "--output-dir", str(tmp_path)])
    assert path.read_text() == "old history"


def test_retry_does_not_execute_a_successful_tool_twice(adapter, monkeypatch):
    monkeypatch.setattr("src.agent.llm.time.sleep", MagicMock())
    call = SimpleNamespace(id="search-1", function=SimpleNamespace(
        name="knowledge_search", arguments='{"query": "low block"}'))
    first = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=None, tool_calls=[call]))])
    adapter._client.chat.completions.create.side_effect = [first, api_error(), sdk_response()]
    retrieval = MagicMock()
    retrieval.retrieve.return_value = [source()]
    response = make_agent(adapter, retrieval).run_discussion_turn("respond")
    retrieval.retrieve.assert_called_once_with(query="low block")
    assert response.content == "answer"
    assert len(response.tool_calls) == 1
    calls = adapter._client.chat.completions.create.call_args_list
    assert calls[1] == calls[2]
    assert calls[2].kwargs["messages"][-1]["tool_call_id"] == "search-1"


def test_explicit_zero_temperature_survives_save(tmp_path):
    from src.discussion.models import DiscussionState
    state = DiscussionState(topic="q", agent_ids=["a", "b"])
    path = save_discussion_from_state(state, output_dir=tmp_path,
                                      llm=SimpleNamespace(temperature=.8), llm_temperature=0)
    assert load_discussion(path).config.llm_temperature == 0


def test_partial_run_keeps_last_checkpoint_when_disk_save_fails(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "OpenAICompatibleLLM", lambda: ScriptedLLM())
    monkeypatch.setattr(runner, "RAGRetrieval", lambda **kwargs: SimpleNamespace(retrieve=lambda query: [source()]))
    import src.discussion.persistence as persistence
    original = persistence.os.replace
    writes = []
    def disk_failure(src, dst):
        writes.append(dst)
        if len(writes) == 8:
            raise OSError("disk unavailable")
        original(src, dst)
    monkeypatch.setattr(persistence.os, "replace", disk_failure)
    with pytest.raises(OSError, match="disk unavailable"):
        runner.main(["--discussion-id", "disk-demo", "--output-dir", str(tmp_path)])
    saved = load_discussion(tmp_path / "disk-demo.json")
    assert len(saved.messages) == 7
    assert saved.config.metadata["last_completed_round"] == 0
    assert saved.config.metadata["status"] == "running"
    assert not list(tmp_path.glob(".*.tmp.*"))


def test_zero_tool_budget_does_not_execute_requested_tool():
    llm = MagicMock()
    llm.generate.return_value = {"tool_calls": [{"name": "calculator", "arguments": {"expression": "2+2"}}]}
    agent = make_agent(llm)
    agent.max_tool_rounds = 0
    agent.tools.execute = MagicMock()
    with pytest.raises(AgentTurnError, match="maximum number"):
        agent.run_discussion_turn("respond")
    agent.tools.execute.assert_not_called()


def test_zero_retries_preserves_external_retry_control(adapter, monkeypatch):
    adapter._max_retries = 0
    sleep = MagicMock()
    monkeypatch.setattr("src.agent.llm.time.sleep", sleep)
    adapter._client.chat.completions.create.side_effect = api_error()
    with pytest.raises(RateLimitError):
        adapter.generate([{"role": "user", "content": "q"}])
    assert adapter._client.chat.completions.create.call_count == 1
    sleep.assert_not_called()


def test_empty_search_has_an_explicit_message(capsys):
    search_module.print_results("q", [])
    assert "No passages found" in capsys.readouterr().out


def test_search_loads_project_env_explicitly(monkeypatch):
    import runpy
    from pathlib import Path
    load = MagicMock()
    monkeypatch.setattr("dotenv.load_dotenv", load)
    runpy.run_path(search_module.__file__, run_name="offline_env_check")
    load.assert_called_once_with(Path(search_module.__file__).resolve().parents[2] / ".env")


def test_model_failure_retains_preceding_tool_results():
    llm = MagicMock()
    llm.generate.side_effect = [
        {"tool_calls": [{"name": "knowledge_search", "arguments": {"query": "verify"}}]},
        RuntimeError("model unavailable"),
    ]
    with pytest.raises(AgentTurnError) as info:
        make_agent(llm).run_discussion_turn("respond")
    assert info.value.tool_calls[0].status == "success"
    assert info.value.tool_calls[0].result[0]["metadata"]["doc_id"] == "doc_demo"
