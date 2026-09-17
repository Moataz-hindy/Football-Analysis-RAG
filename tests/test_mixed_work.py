"""Integration regressions across discussion features and failure handling."""
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx
import psycopg2
import pytest
from openai import APIConnectionError

from src.agent.agent import Agent, AgentTurnError
from src.agent.types import ToolCall
from src.rag import search as rag
from src.tools.web_search import WebSearchTool
from test_week3_reliability import make_agent, api_error, sdk_response


@pytest.mark.parametrize("error", [
    api_error(), api_error(503),
    APIConnectionError(request=httpx.Request("POST", "https://example.test")),
])
def test_provider_outage_uses_labeled_keyword_results_and_closes_connection(monkeypatch, error):
    conn = MagicMock()
    cursor = conn.cursor.return_value.__enter__.return_value
    cursor.fetchall.return_value = [("doc_1", 0, "Low block", "https://example.test", "Evidence", None)]
    monkeypatch.setattr(rag, "get_connection", lambda: conn)
    monkeypatch.setattr(rag, "embed_query", MagicMock(side_effect=error))
    results = rag.search("low block", client=object(), model="test")
    assert results[0]["retrieval_mode"] == "keyword"
    assert results[0]["similarity"] is None
    assert "ILIKE" in cursor.execute.call_args.args[0]
    conn.close.assert_called_once()


def test_database_query_failure_does_not_attempt_keyword_query(monkeypatch):
    conn = MagicMock()
    cursor = conn.cursor.return_value.__enter__.return_value
    cursor.execute.side_effect = psycopg2.OperationalError("database unavailable")
    monkeypatch.setattr(rag, "embed_query", lambda *args: [0.1])
    with pytest.raises(rag.RetrievalError):
        rag.search("low block", client=object(), model="test", conn=conn)
    assert cursor.execute.call_count == 1
    conn.close.assert_not_called()


@pytest.mark.parametrize("status", [400, 401, 403])
def test_embedding_configuration_errors_remain_visible(monkeypatch, status):
    conn = MagicMock()
    monkeypatch.setattr(rag, "embed_query", MagicMock(side_effect=api_error(status)))
    with pytest.raises(rag.RetrievalError):
        rag.search("low block", client=object(), model="test", conn=conn)
    conn.cursor.assert_not_called()


def test_keyword_database_failure_closes_owned_connection(monkeypatch):
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value.execute.side_effect = psycopg2.OperationalError("lost database")
    monkeypatch.setattr(rag, "get_connection", lambda: conn)
    monkeypatch.setattr(rag, "embed_query", MagicMock(side_effect=api_error()))
    with pytest.raises(rag.RetrievalError):
        rag.search("low block", client=object(), model="test")
    conn.close.assert_called_once()


def test_keyword_mode_survives_agent_evidence(monkeypatch):
    from src.agent.retrieval import RAGRetrieval
    monkeypatch.setattr("src.agent.retrieval.search", lambda *args, **kwargs: [{
        "doc_id": "doc_1", "chunk_index": 0, "title": "Low block", "text": "Evidence",
        "url": "https://example.test", "similarity": None, "retrieval_mode": "keyword",
    }])
    llm = MagicMock()
    llm.generate.return_value = {"content": "A grounded opinion"}
    result = make_agent(llm, RAGRetrieval()).run("low block")
    assert result.sources[0].score is None
    assert result.sources[0].metadata["retrieval_mode"] == "keyword"
    assert result.tool_calls[0].result[0]["metadata"]["retrieval_mode"] == "keyword"


def test_persona_query_is_the_query_recorded_in_initial_evidence():
    llm = MagicMock()
    llm.generate.return_value = {"content": "A grounded opinion"}
    agent = make_agent(llm)
    agent.persona.name = "Tactical Coach"
    task = "Discussion topic: Japan versus Spain\nGive your initial opinion."
    result = agent.run(task)
    query = result.tool_calls[0].arguments["query"]
    assert "Japan versus Spain" in query
    assert "tactical formations" in query


def test_web_errors_and_generated_summaries_are_not_sources():
    calls = [
        ToolCall("web_search", {}, "Error executing web search: unavailable"),
        ToolCall("web_search", {}, "Tavily-generated summary: An unsupported summary"),
        ToolCall("web_search", {}, "Title: Article\nURL: https://example.test\nContent: Evidence"),
    ]
    sources = Agent._sources_from_tool_calls(calls)
    assert len(sources) == 1
    assert sources[0].source == "https://example.test"
    assert sources[0].score is None


def test_failed_web_provider_raises_instead_of_returning_error_as_evidence(monkeypatch):
    factory = MagicMock()
    factory.return_value.text.side_effect = RuntimeError("provider unavailable")
    monkeypatch.setitem(sys.modules, "ddgs", SimpleNamespace(DDGS=factory))
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="Web search failed"):
        WebSearchTool().run({"query": "match report"})


def test_failed_duplicate_retry_keeps_preceding_evidence():
    llm = MagicMock()
    previous = "STANCE: Maintain. REASONING: compact lines."
    llm.generate.side_effect = [
        {"tool_calls": [{"name": "knowledge_search", "arguments": {"query": "verify"}}]},
        {"content": previous},
        RuntimeError("provider unavailable"),
    ]
    agent = make_agent(llm)
    agent.memory.add({"task": "earlier", "response": previous})
    with pytest.raises(AgentTurnError) as info:
        agent.run_discussion_turn("reply to the next round")
    assert info.value.tool_calls[0].result[0]["metadata"]["doc_id"] == "doc_demo"
    assert len(agent.memory.history) == 1


def test_provider_tool_metadata_survives_retry(monkeypatch):
    from src.agent.llm import OpenAICompatibleLLM
    llm = OpenAICompatibleLLM(api_key="fake", base_url="https://example.test", model="test", max_retries=1)
    llm._client = MagicMock()
    monkeypatch.setattr("src.agent.llm.time.sleep", lambda seconds: None)
    call = SimpleNamespace(id="call-1", function=SimpleNamespace(name="calculator", arguments='{"expression":"2+2"}'),
                           extra_content={"google": {"thought_signature": "opaque-test-value"}})
    first = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=None, tool_calls=[call]))])
    create = llm._client.chat.completions.create
    create.side_effect = [first, api_error(), sdk_response()]
    result = make_agent(llm).run_discussion_turn("calculate")
    assert result.content == "answer"
    assert len(result.tool_calls) == 1
    assert create.call_args_list[1] == create.call_args_list[2]
    assert create.call_args.kwargs["messages"][-2]["tool_calls"][0]["extra_content"] == call.extra_content
