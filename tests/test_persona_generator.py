"""Unit tests for Dynamic 3v3 Persona Generator and Symmetrical Debate Graph."""

import json
from pathlib import Path
from unittest.mock import MagicMock
import pytest

from src.agent.persona_generator import generate_personas_for_topic
from src.discussion.graph import DiscussionGraph
from src.discussion.router import GraphRouter


def test_symmetrical_3v3_graph_connectivity():
    """Verify that create_symmetrical_3v3 builds a strongly connected digraph."""
    camp_a = {
        "coach": "england_coach",
        "fan": "england_fan",
        "pundit": "england_pundit",
    }
    camp_b = {
        "coach": "france_coach",
        "fan": "france_fan",
        "pundit": "france_pundit",
    }

    graph = DiscussionGraph.create_symmetrical_3v3(camp_a, camp_b)
    assert graph.is_strongly_connected(), "Symmetrical 3v3 graph must be strongly connected"

    # Verify reciprocal counterparts
    assert "france_coach" in graph.get_outbound_edges("england_coach")
    assert "england_coach" in graph.get_outbound_edges("france_coach")
    assert "france_fan" in graph.get_outbound_edges("england_fan")
    assert "england_fan" in graph.get_outbound_edges("france_fan")

    # Verify router works with it
    router = GraphRouter(graph=graph)
    assert set(router.get_recipients("england_coach")) == {"france_coach", "england_pundit", "france_fan"}


def test_persona_generator_with_mock_llm(tmp_path):
    """Verify that persona generator parses LLM output, writes valid YAML files, and creates manifest."""
    mock_payload_a = {
        "camp_a_name": "England",
        "camp_b_name": "France",
        "personas": [
            {
                "id": "england_coach",
                "role": "coach",
                "name": "Thomas Tuchel (England Manager)",
                "background": "Tactical pragmatist focused on fast transitions and vertical pace.",
                "stance": "Benching Kane and unleashing Saka and Eze dismantled France. Requires hard data before conceding.",
                "communication_style": "Analytical, assertive, and defiant against pundit criticism.",
                "expertise": ["Half-space overloading", "Counter-pressing"],
                "priorities": ["Defend tactical lineup", "Reject physical fatigue as the primary cause"],
            },
            {
                "id": "england_fan",
                "role": "fan",
                "name": "Passionate England Supporter",
                "background": "Follows the Three Lions through heartbreaks and triumphs.",
                "stance": "England outplayed France completely. Refuses to accept excuses.",
                "communication_style": "Fiery and proud.",
                "expertise": ["Fan sentiment", "Terrace culture"],
                "priorities": ["Celebrate historic win", "Push back against French complaints"],
            },
            {
                "id": "england_pundit",
                "role": "pundit",
                "name": "Jamie Carragher",
                "background": "Former defender and outspoken pundit.",
                "stance": "England were brave and ruthless in transition.",
                "communication_style": "Sharp and direct.",
                "expertise": ["Defensive organization", "Punditry"],
                "priorities": ["Analyze player performance", "Critique French defending"],
            },
        ],
    }

    mock_payload_b = {
        "personas": [
            {
                "id": "france_coach",
                "role": "coach",
                "name": "Didier Deschamps",
                "background": "Pragmatic tournament-winning manager.",
                "stance": "Second half showed France's true quality; first half was physical heat shock.",
                "communication_style": "Composed and authoritative.",
                "expertise": ["Tournament management", "In-game adjustments"],
                "priorities": ["Highlight second-half comeback", "Contextualize squad fatigue"],
            },
            {
                "id": "france_fan",
                "role": "fan",
                "name": "Les Bleus Fan Supporter",
                "background": "Vocal supporter of the French national team.",
                "stance": "Miami humidity and end-of-season exhaustion ruined defensive integrity.",
                "communication_style": "Passionate and aggrieved.",
                "expertise": ["French football culture", "Matchday atmosphere"],
                "priorities": ["Defend Mbappe's scoring record", "Challenge England's arrogance"],
            },
            {
                "id": "france_pundit",
                "role": "pundit",
                "name": "Thierry Henry",
                "background": "Legendary French forward and analytical coach.",
                "stance": "England took their chances, but 10 goals is exhibition-level chaos.",
                "communication_style": "Insightful and eloquent.",
                "expertise": ["Attacking movement", "High-level international football"],
                "priorities": ["Examine defensive disorganization", "Evaluate individual brilliance"],
            },
        ],
    }

    mock_llm = MagicMock()
    mock_llm.generate.side_effect = [
        json.dumps(mock_payload_a),
        json.dumps(mock_payload_b),
        json.dumps(mock_payload_a),
        json.dumps(mock_payload_b),
    ]

    topic = "England 6-4 France World Cup Playoff"
    disc_id = "test_england_france"

    personas, files, manifest = generate_personas_for_topic(
        topic=topic,
        llm=mock_llm,
        discussion_id=disc_id,
        output_dir=tmp_path,
        force_regenerate=False,
    )

    assert len(personas) == 6
    assert "england_coach" in personas
    assert "france_coach" in personas
    assert personas["england_coach"].name == "Thomas Tuchel (England Manager)"

    # Verify YAML files written
    assert (tmp_path / disc_id / "england_coach.yaml").exists()
    assert (tmp_path / disc_id / "manifest.json").exists()
    assert mock_llm.generate.call_count == 2

    # 3. Test Caching: Second call should NOT invoke mock_llm.generate
    personas_cached, files_cached, manifest_cached = generate_personas_for_topic(
        topic=topic,
        llm=mock_llm,
        discussion_id=disc_id,
        output_dir=tmp_path,
        force_regenerate=False,
    )
    assert mock_llm.generate.call_count == 2, "Cached call should not invoke LLM again"
    assert len(personas_cached) == 6

    # 4. Test Force Regenerate: should invoke mock_llm.generate again (2 more calls)
    generate_personas_for_topic(
        topic=topic,
        llm=mock_llm,
        discussion_id=disc_id,
        output_dir=tmp_path,
        force_regenerate=True,
    )
    assert mock_llm.generate.call_count == 4, "Force regenerate must call LLM"


def test_dynamic_personas_orchestration_integration(tmp_path):
    """Verify that generated 3v3 personas integrate cleanly with DiscussionOrchestrator."""
    from src.agent.types import AgentResponse
    from src.discussion.orchestrator import DiscussionOrchestrator

    class FakeAgent:
        def __init__(self, agent_id: str):
            self.agent_id = agent_id

        def run(self, task: str):
            return AgentResponse(content=f"Initial opinion from {self.agent_id}")

        def run_discussion_turn(self, task: str, received_messages=None):
            return AgentResponse(content=f"Round turn from {self.agent_id} rejecting concessions without xG data")

    camp_a = {"coach": "england_coach", "fan": "england_fan", "pundit": "england_pundit"}
    camp_b = {"coach": "france_coach", "fan": "france_fan", "pundit": "france_pundit"}

    graph = DiscussionGraph.create_symmetrical_3v3(camp_a, camp_b)
    router = GraphRouter(graph=graph)
    agents = {aid: FakeAgent(aid) for aid in router.graph.graph.nodes}

    orchestrator = DiscussionOrchestrator(agents=agents, router=router)
    state = orchestrator.run(topic="England vs France", total_rounds=3)

    assert state.total_rounds == 3
    assert len(state.messages) == 24
    initial_senders = {m.sender_id for m in state.messages if m.round_number == 0}
    assert len(initial_senders) == 6
    assert set(state.agent_ids) == set(router.graph.graph.nodes)
