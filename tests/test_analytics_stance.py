"""Unit tests for Task 1: Opinion Change & Numeric Stance Trajectories."""

import json
from pathlib import Path
import pytest

from src.analytics.models import AgentStancePoint, OpinionTrajectoryResult
from src.analytics.stance import compute_opinion_trajectories, extract_numeric_stance
from src.discussion.types import OpinionSnapshot


def test_extract_numeric_stance_merit_vs_grievance():
    # Sporting merit stance
    merit_snap = OpinionSnapshot(
        agent_id="tactical_analyst",
        round_num=0,
        stance="Argentina's victory was a deserved triumph of tactical superiority and rest defense.",
        reasoning="Physical exhaustion of the low block led to sustainable xG chance creation.",
    )
    score_merit = extract_numeric_stance(merit_snap)
    assert score_merit > 0.6
    assert score_merit <= 1.0

    # Officiating grievance stance
    ref_snap = OpinionSnapshot(
        agent_id="fan_analyst",
        round_num=0,
        stance="Argentina did not deserve to win; this match was a robbery gifted by the referee.",
        reasoning="The disallowed goal was an injustice and destroyed momentum.",
    )
    score_ref = extract_numeric_stance(ref_snap)
    assert score_ref < -0.6
    assert score_ref >= -1.0


def test_extract_numeric_stance_neutral_variance():
    stat_snap = OpinionSnapshot(
        agent_id="statistical_analyst",
        round_num=0,
        stance="Argentina's victory was a statistical outlier driven by high-variance events.",
        reasoning="Field tilt was balanced and both sides had equal expected threat.",
    )
    score_stat = extract_numeric_stance(stat_snap)
    assert -0.2 <= score_stat <= 0.2


def test_compute_opinion_trajectories_math():
    mock_data = {
        "config": {
            "discussion_id": "test-math-run",
            "topic": "Test Topic",
            "num_rounds": 2,
            "agent_ids": ["agent_a"],
        },
        "opinions": [
            {
                "agent_id": "agent_a",
                "round_num": 0,
                "stance": "Argentina deserved the win through tactical superiority.",
                "reasoning": "Dominant play.",
                "changed_from_previous": False,
            },
            {
                "agent_id": "agent_a",
                "round_num": 1,
                "stance": "I maintain my position.",
                "reasoning": "Still dominant.",
                "changed_from_previous": False,
            },
            {
                "agent_id": "agent_a",
                "round_num": 2,
                "stance": "I concede that the referee influenced the match and it was a robbery.",
                "reasoning": "The fan convinced me.",
                "changed_from_previous": True,
            },
        ],
    }

    res = compute_opinion_trajectories(mock_data)
    assert isinstance(res, OpinionTrajectoryResult)
    assert "agent_a" in res.trajectories
    points = res.trajectories["agent_a"]
    assert len(points) == 3

    # Round 0 check
    assert points[0].round_num == 0
    assert points[0].opinion_change is None
    assert points[0].stance_value > 0.5

    # Round 1 check (maintained)
    assert points[1].round_num == 1
    assert points[1].opinion_change is not None
    assert abs(points[1].opinion_change) <= 0.1  # minimal movement on maintenance

    # Round 2 check (concession to robbery)
    assert points[2].round_num == 2
    assert points[2].stance_value < 0.0
    assert points[2].opinion_change < -0.5  # sharp negative drop


def test_compute_opinion_trajectories_on_real_discussion():
    live_file = Path("outputs/egy-arg7.json")
    if not live_file.exists():
        pytest.skip("outputs/egy-arg7.json not available")

    with open(live_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    res = compute_opinion_trajectories(data)
    assert res.discussion_id == "egy-arg7"
    assert len(res.trajectories) == 6

    for agent_id, points in res.trajectories.items():
        assert len(points) == 4  # R0, R1, R2, R3
        # Round 0 delta is None
        assert points[0].opinion_change is None
        # Subsequent rounds have numeric delta
        for p in points[1:]:
            assert p.opinion_change is not None
            assert -2.0 <= p.opinion_change <= 2.0
            assert -1.0 <= p.stance_value <= 1.0

    # Helper methods
    series = res.get_stance_series("context_analyst")
    assert len(series) == 4
    round_stances = res.get_round_stances(0)
    assert len(round_stances) == 6
    assert "fan_analyst" in round_stances
    assert round_stances["fan_analyst"] < 0.0
    assert round_stances["context_analyst"] > 0.0


def test_empty_discussion_handling():
    empty_data = {"config": {"discussion_id": "empty-run"}, "opinions": []}
    res = compute_opinion_trajectories(empty_data)
    assert res.trajectories == {}
    assert res.get_stance_series("missing_agent") == []
    assert res.get_round_stances(0) == {}


def test_universal_topic_scoring_arbitrary_topic():
    """Verify that scoring works universally on non-Egypt/Argentina topics."""
    topic = "Should the offside rule be changed to Arsene Wenger's daylight proposal?"
    
    pro_snap = {
        "agent_id": "innovator",
        "round_num": 0,
        "stance": "I strongly agree with this proposal; it is completely justified and effective.",
        "reasoning": "Attacking football will thrive.",
    }
    score_pro = extract_numeric_stance(pro_snap, topic=topic)
    assert score_pro > 0.6

    anti_snap = {
        "agent_id": "traditionalist",
        "round_num": 0,
        "stance": "I firmly oppose this rule change; it is a total failure and completely flawed.",
        "reasoning": "Defending low blocks will become impossible.",
    }
    score_anti = extract_numeric_stance(anti_snap, topic=topic)
    assert score_anti < -0.6

    neutral_snap = {
        "agent_id": "pragmatist",
        "round_num": 0,
        "stance": "The pilot data is mixed and inconclusive; statistical variance is too high.",
        "reasoning": "Need more trials before forming a judgment.",
    }
    score_neutral = extract_numeric_stance(neutral_snap, topic=topic)
    assert -0.2 <= score_neutral <= 0.2


def test_compute_opinion_trajectories_with_mocked_llm():
    """Verify batched LLM scoring path when an LLM client returns structured scores."""
    class MockLLM:
        def generate(self, messages, tools=None):
            return {
                "content": json.dumps([
                    {"agent_id": "agent_x", "round_num": 0, "stance_value": 0.88},
                    {"agent_id": "agent_x", "round_num": 1, "stance_value": 0.25},
                ])
            }

    mock_data = {
        "config": {
            "discussion_id": "mock-llm-run",
            "topic": "Arbitrary Topic",
            "num_rounds": 1,
            "agent_ids": ["agent_x"],
        },
        "opinions": [
            {"agent_id": "agent_x", "round_num": 0, "stance": "Initial thought"},
            {"agent_id": "agent_x", "round_num": 1, "stance": "Shifted thought"},
        ],
    }

    res = compute_opinion_trajectories(mock_data, use_llm=True, llm_client=MockLLM())
    pts = res.trajectories["agent_x"]
    assert len(pts) == 2
    assert pts[0].stance_value == 0.88
    assert pts[1].stance_value == 0.25
    assert pts[1].opinion_change == -0.63

