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
