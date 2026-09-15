"""Requirement 4.8 tests: a discussion run is identifiable and reproducible.

Covers the externally observable reproducibility contract: a run can be
persisted under its discussion_id, reloaded by that identifier alone, and
the record reconstructs the participants, graph, routing, rounds, model
configuration, message order, and opinion evolution. No LLM, database, or
network is involved.
"""

from uuid import uuid4

import networkx as nx
import pytest

from src.agent.types import AgentResponse
from src.discussion import (
    load_discussion_by_id,
    save_discussion_from_state,
)
from src.discussion.orchestrator import DiscussionOrchestrator
from src.discussion.router import GraphRouter

TOTAL_ROUNDS = 3


class StubAgent:
    """Acts like a Week 2 agent with per-round structured opinions."""

    def __init__(self, agent_id: str) -> None:
        self.agent_id = agent_id
        self.calls = 0

    def run(self, task: str) -> AgentResponse:
        return self._respond()

    def run_discussion_turn(
        self,
        task: str,
        received_messages: list[dict[str, str]] | None = None,
    ) -> AgentResponse:
        return self._respond()

    def _respond(self) -> AgentResponse:
        turn = self.calls
        self.calls += 1
        content = (
            f"STANCE: {self.agent_id} stance turn {turn}\n"
            f"REASONING: {self.agent_id} reasoning for turn {turn}.\n"
            "SOURCES USED: none"
        )
        return AgentResponse(content=content)


class StubLLM:
    """Exposes the same capture surface as OpenAICompatibleLLM."""

    model = "stub-model"
    temperature = 0.15
    base_url = "http://stub.local/v1"
    max_tokens = 256


@pytest.fixture
def persisted_run(tmp_path):
    """Run a full fake discussion and persist it; return (path, result)."""
    router = GraphRouter()
    agents = {node: StubAgent(node) for node in router.graph.graph.nodes}
    orchestrator = DiscussionOrchestrator(agents=agents, router=router)

    discussion_id = "test-run-fixed-id"
    state = orchestrator.run(
        topic="Stub discussion topic",
        total_rounds=TOTAL_ROUNDS,
        discussion_id=discussion_id,
    )
    path = save_discussion_from_state(
        state=state,
        router=router,
        output_dir=tmp_path,
        llm=StubLLM(),
        config_metadata={"persona_files": {"stub_agent": "stub_agent.yaml"}},
        duration_seconds=1.0,
    )
    result = load_discussion_by_id(discussion_id, output_dir=tmp_path)
    return path, result, router


def test_run_identified_by_discussion_id(persisted_run, tmp_path):
    """The run is persisted under its identifier and reloadable by it alone."""
    path, result, _ = persisted_run

    assert path.endswith("test-run-fixed-id.json")
    assert result.config.discussion_id == "test-run-fixed-id"


def test_run_configuration_is_preserved(persisted_run):
    """Config captures topic, agents, graph, rounds, and the LLM settings."""
    _, result, router = persisted_run
    config = result.config

    assert config.topic == "Stub discussion topic"
    assert config.num_rounds == TOTAL_ROUNDS
    assert sorted(config.agent_ids) == config.agent_ids
    assert set(config.agent_ids) == set(router.graph.graph.nodes)
    assert config.llm_model == "stub-model"
    assert config.llm_temperature == 0.15
    assert config.metadata["llm_base_url"] == "http://stub.local/v1"
    # Persisted graph equals the routing graph and is strongly connected.
    assert sorted(config.graph) == sorted(router.graph.graph.nodes)
    for node in router.graph.graph.nodes:
        assert sorted(config.graph[node]) == sorted(
            router.get_recipients(node)
        )
    assert nx.is_strongly_connected(nx.DiGraph(config.graph))


def test_messages_reconstruct_in_round_order(persisted_run):
    """Messages carry round, sender, recipients, order, and identity."""
    _, result, router = persisted_run

    agents = result.config.agent_ids
    assert len(result.messages) == len(agents) * (TOTAL_ROUNDS + 1)

    ordered = sorted(
        result.messages, key=lambda m: (m.round_num, m.sender_id)
    )
    # Persisted order is append order; sorting must not change the content.
    assert [m.metadata["message_id"] for m in result.messages] == [
        m.metadata["message_id"] for m in ordered
    ]
    assert {m.round_num for m in result.messages} == set(
        range(TOTAL_ROUNDS + 1)
    )

    for message in ordered:
        assert message.sender_id in agents
        assert message.recipient_ids == router.get_recipients(message.sender_id)
        assert message.content.strip()
        assert message.metadata["message_id"]


def test_opinion_history_is_reconstructed(persisted_run):
    """Opinions exist per agent per round and change detection is populated."""
    _, result, _ = persisted_run
    agents = result.config.agent_ids

    for agent_id in agents:
        snapshots = sorted(
            (o for o in result.opinions if o.agent_id == agent_id),
            key=lambda o: o.round_num,
        )
        assert [s.round_num for s in snapshots] == list(
            range(TOTAL_ROUNDS + 1)
        )
        # Round 0 is the initial opinion; stance evolves across turns.
        assert snapshots[0].changed_from_previous is False
        assert snapshots[-1].stance == f"{agent_id} stance turn {TOTAL_ROUNDS}"
        assert snapshots[-1].changed_from_previous is True
        assert snapshots[-1].change_reason.strip()


def test_explicit_model_args_override_llm_capture(tmp_path):
    """Hand-specified llm_model/llm_temperature win over adapter capture."""
    router = GraphRouter()
    agents = {node: StubAgent(node) for node in router.graph.graph.nodes}
    orchestrator = DiscussionOrchestrator(agents=agents, router=router)
    state = orchestrator.run(
        topic="Stub discussion topic",
        total_rounds=TOTAL_ROUNDS,
    )
    save_discussion_from_state(
        state=state,
        router=router,
        output_dir=tmp_path,
        llm=StubLLM(),
        llm_model="manual-model",
        llm_temperature=0.9,
    )
    result = load_discussion_by_id(state.discussion_id, output_dir=tmp_path)
    assert result.config.llm_model == "manual-model"
    assert result.config.llm_temperature == 0.9


def test_default_discussion_ids_are_unique(tmp_path):
    """Two unnamed runs never collide in the same output directory."""
    router = GraphRouter()
    agents = {node: StubAgent(node) for node in router.graph.graph.nodes}
    orchestrator = DiscussionOrchestrator(agents=agents, router=router)

    first = orchestrator.run(topic="Stub", total_rounds=TOTAL_ROUNDS)
    second = orchestrator.run(topic="Stub", total_rounds=TOTAL_ROUNDS)
    assert first.discussion_id != second.discussion_id

    for state in (first, second):
        save_discussion_from_state(
            state=state, router=router, output_dir=tmp_path, llm=StubLLM()
        )

    saved_ids = {
        path.stem
        for path in tmp_path.glob("*.json")
    }
    assert saved_ids == {first.discussion_id, second.discussion_id}
