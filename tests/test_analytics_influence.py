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
    data = {
        "config": {"discussion_id": "fixture", "topic": "Should the proposal be adopted?", "agent_ids": ["a", "b"], "num_rounds": 3},
        "messages": [{"round_num": r, "sender_id": "a", "recipient_ids": ["b"]} for r in range(3)],
        "opinions": [
            {"agent_id": aid, "round_num": r, "stance": "I support the proposal." if aid == "a" or r > 0 else "I oppose the proposal."}
            for aid in ["a", "b"] for r in range(4)
        ],
    }
    for op in data["opinions"]:
        op["stance"] = "I support the proposal."
    result = compute_agent_influence(data)
    assert result.top_influencer is None
    assert result.agent_influences["a"].status == "zero_movement"
    assert result.agent_influences["a"].influence_score is None
    assert result.agent_influences["b"].status == "insufficient_data"


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
    assert "Observed Convergence" in res.discussion_dynamic

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


def test_compute_agent_influence_on_saved_record_fixture_with_changes():
    data = {
        "config": {"discussion_id": "fixture", "topic": "Should the proposal be adopted?", "agent_ids": ["a", "b"], "num_rounds": 3},
        "messages": [{"round_num": r, "sender_id": "a", "recipient_ids": ["b"]} for r in range(3)],
        "opinions": [
            {"agent_id": aid, "round_num": r, "stance": "I support the proposal." if aid == "a" or r > 0 else "I oppose the proposal."}
            for aid in ["a", "b"] for r in range(4)
        ],
    }
    result = compute_agent_influence(data)
    assert result.top_influencer == "a"
    assert result.agent_influences["a"].status == "valid"
    assert result.get_ranked_influencers() == [("a", .3333)]


def test_compute_agent_influence_empty_discussion():
    """Verify empty input handling."""
    empty_data = {"config": {"discussion_id": "empty-run", "agent_ids": []}, "messages": [], "opinions": []}
    res = compute_agent_influence(empty_data)
    assert res.discussion_id == "empty-run"
    assert res.agent_influences == {}
    assert res.top_influencer is None
