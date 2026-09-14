"""Unit tests for persona-specific RAG query formulation and anti-hallucination guardrails."""

import pytest
from unittest.mock import MagicMock

from src.agent.agent import Agent
from src.agent.config import AgentConfig
from src.agent.persona import Persona
from src.agent.retrieval import RAGRetrieval
from src.agent.tool_registery import ToolRegistry
from src.discussion.orchestrator import DiscussionOrchestrator
from src.discussion.router import GraphRouter


def test_rag_retrieval_default_k_is_six():
    retrieval = RAGRetrieval()
    assert retrieval.k == 6


@pytest.mark.parametrize(
    ("persona_name", "expertise", "expected_keyword"),
    [
        ("VAR & Refereeing Expert", ["Law 12", "VAR protocol"], "VAR"),
        ("Tactical Coach", ["low block", "pressing triggers"], "tactical formations"),
        ("Data & Statistical Analyst", ["xG", "Opta data"], "Opta stats"),
        ("Egyptian & African Football Supporter", ["fan culture"], "controversy"),
        ("Performance & Athletic Analyst", ["fatigue", "intensity"], "physical fatigue"),
        ("Historical & Tournament Context Expert", ["tournament history"], "tournament context"),
    ],
)
def test_build_persona_query_augments_topic(persona_name, expertise, expected_keyword):
    persona = Persona(
        _name=persona_name,
        _background="Test background",
        _stance="Test stance",
        _communication_style="Direct",
        _expertise=expertise,
        _priorities=["Test priority"],
    )
    config = AgentConfig(
        persona=persona,
        memory=MagicMock(),
        retrieval=MagicMock(),
        tools=ToolRegistry([]),
        llm=MagicMock(),
    )
    agent = Agent(config)

    task = "Discussion topic: Argentina vs Egypt World Cup 2026\n\nGive your initial opinion."
    query = agent._build_persona_query(task)

    assert "Argentina vs Egypt World Cup 2026" in query
    assert expected_keyword in query


def test_build_persona_query_falls_back_for_unknown_persona():
    persona = Persona(
        _name="Generic Pundit",
        _background="Pundit",
        _stance="Neutral",
        _communication_style="Casual",
        _expertise=["General punditry"],
        _priorities=["Entertainment"],
    )
    config = AgentConfig(
        persona=persona,
        memory=MagicMock(),
        retrieval=MagicMock(),
        tools=ToolRegistry([]),
        llm=MagicMock(),
    )
    agent = Agent(config)

    task = "Discussion topic: Argentina vs Egypt World Cup 2026\n\nGive your initial opinion."
    query = agent._build_persona_query(task)

    assert query == "Argentina vs Egypt World Cup 2026"


def test_orchestrator_initial_prompt_contains_metric_grounding():
    # Setup mock router and agent
    router = GraphRouter()
    agents = {}
    for node in router.graph.graph.nodes:
        stub = MagicMock()
        stub.run.return_value = MagicMock(content="STANCE: test", sources=[], tool_calls=[])
        agents[node] = stub

    orchestrator = DiscussionOrchestrator(agents=agents, router=router)
    state = orchestrator.initialize_discussion("Argentina vs Egypt World Cup 2026")

    # Check the task passed to the first agent
    first_agent_id = state.agent_ids[0]
    call_args = agents[first_agent_id].run.call_args[0][0]
    assert "Do NOT confabulate tracking metrics, exact distance measurements" in call_args
    assert "Base your position strictly on concrete match facts" in call_args


def test_is_duplicate_response_detects_copies():
    text1 = (
        "STANCE: I maintain my position that the result was determined by sporting performance.\n\n"
        "The argument presented by the fan relies on narrative bias rather than Law 12. "
        "The VAR review showed a clear foul in the build-up by Marwan Attia on Lisandro Martinez.\n\n"
        "Furthermore, Argentina created 1.51 xG in the first half alone, proving sustained pressure.\n\n"
        "SOURCES USED:\n- Fox Sports"
    )
    # Exact match
    assert Agent._is_duplicate_response(text1, text1) is True

    # Paragraph-level copy
    text2 = (
        "STANCE: Maintain.\n\n"
        "The argument presented by the fan relies on narrative bias rather than Law 12. "
        "The VAR review showed a clear foul in the build-up by Marwan Attia on Lisandro Martinez.\n\n"
        "Furthermore, Argentina created 1.51 xG in the first half alone, proving sustained pressure.\n\n"
        "SOURCES USED:\n- The Athletic"
    )
    assert Agent._is_duplicate_response(text2, text1) is True

    # Truly different content
    text3 = (
        "STANCE: Final Verdict.\n\n"
        "In this conclusive synthesis, while the fan's frustration regarding the 100-yard distance of the foul is understandable, "
        "the IFAB protocol for the Attacking Possession Phase explicitly mandates intervention.\n\n"
        "Ultimately, Egypt's inability to withstand the sustained physical attrition in the final 15 minutes decided the match.\n\n"
        "SOURCES USED:\n- Opta Analyst"
    )
    assert Agent._is_duplicate_response(text3, text1) is False


def test_conversation_memory_labels_rounds():
    from src.agent.memory import ConversationMemory
    mem = ConversationMemory()
    mem.add({
        "task": "Discussion topic: Argentina vs Egypt\nGive your initial opinion.",
        "response": "Round 0 response"
    })
    mem.add({
        "task": "Discussion topic: Argentina vs Egypt\nRound: 1 of 3\nCross examine.",
        "response": "Round 1 response"
    })

    messages = mem.get_messages()
    assert len(messages) == 4
    assert messages[0]["content"] == "Discussion Turn (Round 0: Initial Opinion)"
    assert messages[2]["content"] == "Discussion Turn (Round 1 of 3)"


def test_agent_retries_on_duplicate_response():
    prev_text = (
        "STANCE: Maintain.\n\n"
        "This is paragraph one explaining the VAR decision in detail and citing Law 12.\n\n"
        "This is paragraph two explaining Egypt structural fatigue and rest defence breakdown.\n\n"
        "SOURCES USED:\n- ESPN"
    )
    fresh_text = (
        "STANCE: Conclusive Verdict.\n\n"
        "This is a fresh synthesis addressing the final debate points without recycling previous arguments.\n\n"
        "SOURCES USED:\n- Independent"
    )

    llm_mock = MagicMock()
    # First response returns the duplicate text, second response (retry) returns fresh text
    llm_mock.generate.side_effect = [
        {"content": prev_text, "tool_calls": []},
        {"content": fresh_text, "tool_calls": []},
    ]

    mem = MagicMock()
    mem.history = [{"task": "Round 1", "response": prev_text}]
    mem.get_messages.return_value = []
    mem.get_relevant.return_value = ""

    config = AgentConfig(
        persona=MagicMock(),
        memory=mem,
        retrieval=MagicMock(),
        tools=ToolRegistry([]),
        llm=llm_mock,
    )
    agent = Agent(config)
    resp = agent.run_discussion_turn("Round 2 task", [])

    assert resp.content == fresh_text
    assert llm_mock.generate.call_count == 2
