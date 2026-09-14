"""Unit tests for Task 3: Per-Agent Influence Scores & Network Opinion Dynamics."""

import json
from pathlib import Path
import pytest

from src.analytics.influence import compute_agent_influence
from src.analytics.models import (
    AgentInfluence,
    AgentStancePoint,
    DiscussionInfluenceResult,
    OpinionTrajectoryResult,
)


def test_compute_agent_influence_zero_movement():
    """Verify explicit handling of discussions with zero stance movement (egy-arg7.json)."""
    live_file = Path("outputs/egy-arg7.json")
    if not live_file.exists():
        pytest.skip("outputs/egy-arg7.json not available")

    with open(live_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    res = compute_agent_influence(data)
    assert isinstance(res, DiscussionInfluenceResult)
    assert res.discussion_id == "egy-arg7"
    assert res.top_influencer is None
    assert "Zero Stance Movement" in res.discussion_dynamic

    for aid, inf in res.agent_influences.items():
        assert inf.status == "zero_movement"
        assert inf.influence_score is None
        assert "rigid" in inf.rationale.lower()


def test_compute_agent_influence_active_persuasion():
    """Verify directional pull calculation when Agent A persuades Agent B to shift."""
    mock_data = {
        "config": {
            "discussion_id": "test-persuasion",
            "agent_ids": ["agent_a", "agent_b"],
            "num_rounds": 2,
        },
        "messages": [
            {
                "round_num": 0,
                "sender_id": "agent_a",
                "recipient_ids": ["agent_b"],
                "content": "Look at the Law 12 evidence.",
            }
        ],
        "opinions": [
            {"agent_id": "agent_a", "round_num": 0, "stance": "Strong affirmative", "reasoning": "Merit"},
            {"agent_id": "agent_a", "round_num": 1, "stance": "Maintains position", "reasoning": "Merit"},
            {"agent_id": "agent_b", "round_num": 0, "stance": "Strong opposing", "reasoning": "Grievance"},
            {"agent_id": "agent_b", "round_num": 1, "stance": "Concedes tactical superiority", "reasoning": "Convinced by A"},
        ],
    }

    mock_trajectories = OpinionTrajectoryResult(
        discussion_id="test-persuasion",
        trajectories={
            "agent_a": [
                AgentStancePoint(agent_id="agent_a", round_num=0, stance_value=0.85, opinion_change=None),
                AgentStancePoint(agent_id="agent_a", round_num=1, stance_value=0.85, opinion_change=0.0),
            ],
            "agent_b": [
                AgentStancePoint(agent_id="agent_b", round_num=0, stance_value=-0.75, opinion_change=None),
                # Agent B shifts by +0.70 toward Agent A (+0.85)
                AgentStancePoint(agent_id="agent_b", round_num=1, stance_value=-0.05, opinion_change=0.70),
            ],
        },
    )

    res = compute_agent_influence(mock_data, trajectories=mock_trajectories)
    assert res.top_influencer == "agent_a"
    assert "Active Persuasion" in res.discussion_dynamic

    inf_a = res.agent_influences["agent_a"]
    assert inf_a.status == "valid"
    assert inf_a.influence_score is not None
    assert inf_a.influence_score > 0.5
    assert inf_a.recipient_pulls["agent_b"] > 0.5

    # Helper method check
    assert res.get_influence_score("agent_a") == inf_a.influence_score
    ranked = res.get_ranked_influencers()
    assert len(ranked) >= 1
    assert ranked[0][0] == "agent_a"


def test_compute_agent_influence_reactance_backfire():
    """Verify that an agent who pushes a peer further away receives negative pull."""
    mock_data = {
        "config": {
            "discussion_id": "test-backfire",
            "agent_ids": ["agent_a", "agent_b"],
            "num_rounds": 2,
        },
        "messages": [
            {
                "round_num": 0,
                "sender_id": "agent_a",
                "recipient_ids": ["agent_b"],
                "content": "Your analysis is completely wrong.",
            }
        ],
        "opinions": [],
    }

    mock_trajectories = OpinionTrajectoryResult(
        discussion_id="test-backfire",
        trajectories={
            "agent_a": [
                AgentStancePoint(agent_id="agent_a", round_num=0, stance_value=0.80, opinion_change=None),
                AgentStancePoint(agent_id="agent_a", round_num=1, stance_value=0.80, opinion_change=0.0),
            ],
            "agent_b": [
                AgentStancePoint(agent_id="agent_b", round_num=0, stance_value=-0.20, opinion_change=None),
                # Agent B is alienated and shifts further away to -0.80 (delta = -0.60)
                AgentStancePoint(agent_id="agent_b", round_num=1, stance_value=-0.80, opinion_change=-0.60),
            ],
        },
    )

    res = compute_agent_influence(mock_data, trajectories=mock_trajectories)
    inf_a = res.agent_influences["agent_a"]
    assert inf_a.influence_score is not None
    assert inf_a.influence_score < -0.3
    assert "reactance" in inf_a.rationale.lower()


def test_compute_agent_influence_on_real_discussion_with_changes():
    """Verify on real discussion output outputs/egy-arg-v3.json which contains active shifts."""
    v3_file = Path("outputs/egy-arg-v3.json")
    if not v3_file.exists():
        pytest.skip("outputs/egy-arg-v3.json not available")

    with open(v3_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    res = compute_agent_influence(data)
    assert isinstance(res, DiscussionInfluenceResult)
    assert res.discussion_id == "egy-arg-v3"
    assert len(res.agent_influences) == 6

    # In v3, multiple agents shifted, so status is valid
    valid_agents = [aid for aid, inf in res.agent_influences.items() if inf.status == "valid"]
    assert len(valid_agents) > 0

    ranked = res.get_ranked_influencers()
    assert len(ranked) > 0
    # Every ranked score is bounded in [-1.0, 1.0]
    for aid, score in ranked:
        assert -1.0 <= score <= 1.0


def test_compute_agent_influence_empty_discussion():
    """Verify empty input handling."""
    empty_data = {"config": {"discussion_id": "empty-run", "agent_ids": []}, "messages": [], "opinions": []}
    res = compute_agent_influence(empty_data)
    assert res.discussion_id == "empty-run"
    assert res.agent_influences == {}
    assert res.top_influencer is None
