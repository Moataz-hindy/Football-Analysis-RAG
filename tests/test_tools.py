"""Unit tests for ToolRegistry and concrete Tool implementations."""

import pytest
from unittest.mock import MagicMock
from src.agent.tool_registery import ToolRegistry
from src.tools.calculator import CalculatorTool
from src.tools.knowledge_search import KnowledgeSearchTool
from src.agent.types import RetrievedSource


def test_tool_registry_register_and_get():
    calc = CalculatorTool()
    search_tool = KnowledgeSearchTool()
    registry = ToolRegistry()
    registry.register(calc)
    registry.register(search_tool)

    assert len(registry) == 2
    assert "calculator" in registry
    assert "knowledge_search" in registry
    assert registry.get_tools() == [calc, search_tool]


def test_calculator_tool_execution():
    calc = CalculatorTool()
    
    # Simple addition
    result = calc.run({"expression": "10 + 5"})
    assert result == 15

    # Complex expression
    result_complex = calc.run({"expression": "(20 - 5) * 2 / 3"})
    assert result_complex == 10.0


def test_calculator_tool_invalid_expression():
    calc = CalculatorTool()
    with pytest.raises(ValueError):
        calc.run({"expression": "invalid_math_op()"})


def test_knowledge_search_tool_properties():
    search_tool = KnowledgeSearchTool()
    assert search_tool.name == "knowledge_search"
    assert "football intelligence knowledge base" in search_tool.description


def test_knowledge_search_tool_execution():
    # Mock retrieval to test tool execution without requiring live database
    mock_retrieval = MagicMock()
    mock_retrieval.retrieve.return_value = [
        RetrievedSource(content="Real Madrid won 3-1", source="https://news.com", score=0.92)
    ]
    search_tool = KnowledgeSearchTool(retrieval=mock_retrieval)
    
    results = search_tool.run({"query": "Real Madrid"})
    assert len(results) == 1
    assert results[0]["content"] == "Real Madrid won 3-1"
    assert results[0]["score"] == 0.92


def test_tool_registry_execute():
    calc = CalculatorTool()
    registry = ToolRegistry([calc])

    res = registry.execute("calculator", {"expression": "5 * 4"})
    assert res == 20


def test_web_search_tool_properties():
    from src.tools.web_search import WebSearchTool
    tool = WebSearchTool()
    assert tool.name == "web_search"
    assert "query" in tool.parameters["properties"]


def test_web_search_tool_duckduckgo_fallback(monkeypatch):
    from src.tools.web_search import WebSearchTool
    tool = WebSearchTool(api_key="")
    monkeypatch.setattr(
        tool,
        "_duckduckgo_search",
        lambda q: "Title: Test Title\nURL: https://test.com\nContent: Test Snippet",
    )
    res = tool.run({"query": "Argentina Egypt 2026"})
    assert "Test Title" in res
    assert "https://test.com" in res


def test_agent_sources_from_web_search_tool_call():
    from src.agent.agent import Agent
    from src.agent.types import ToolCall

    call = ToolCall(
        name="web_search",
        arguments={"query": "test"},
        result="Title: VAR Disallowed Goal\nURL: https://athletic.com/var\nContent: Ziko goal ruled out for foul.",
    )
    sources = Agent._sources_from_tool_calls([call])
    assert len(sources) == 1
    assert sources[0].source == "https://athletic.com/var"
    assert "Ziko goal ruled out" in sources[0].content
    assert sources[0].metadata["title"] == "VAR Disallowed Goal"

