"""Unit tests for Task 2: Per-Round Agreement / Disagreement Metric Analysis."""

import json
from pathlib import Path
import pytest

from src.analytics.agreement import (
    compute_discussion_agreement,
    compute_round_agreement,
    interpret_agreement,
)
from src.analytics.models import (
    AgentStancePoint,
    DiscussionAgreementResult,
    OpinionTrajectoryResult,
    RoundAgreement,
)


def test_compute_round_agreement_perfect_consensus():
    """All agents hold identical stances -> distance=0, agreement=1.0."""
    stances = {"agent_1": 0.85, "agent_2": 0.85, "agent_3": 0.85, "agent_4": 0.85}
    res = compute_round_agreement(round_num=0, stances=stances)

    assert isinstance(res, RoundAgreement)
    assert res.round_num == 0
    assert res.agreement_score == 1.0
    assert res.mean_distance == 0.0
    assert res.variance == 0.0
    assert res.agent_count == 4
    assert res.interpretation == "Unanimous Consensus"


def test_compute_round_agreement_maximum_polarization():
    """Two agents at opposite poles (+1.0 and -1.0) -> distance=2.0, agreement=0.0."""
    stances = {"pro": 1.0, "anti": -1.0}
    res = compute_round_agreement(round_num=1, stances=stances)

    assert res.agreement_score == 0.0
    assert res.mean_distance == 2.0
    assert res.agent_count == 2
    assert res.interpretation == "Extreme Polarization"


def test_compute_round_agreement_mathematical_precision():
    """Test exact mathematical formula against manual hand calculation."""
    # 4 agents: [0.8, 0.6, -0.2, -0.8]
    # Pairs (6):
    # |0.8 - 0.6| = 0.2
    # |0.8 - (-0.2)| = 1.0
    # |0.8 - (-0.8)| = 1.6
    # |0.6 - (-0.2)| = 0.8
    # |0.6 - (-0.8)| = 1.4
    # |-0.2 - (-0.8)| = 0.6
    # Sum = 5.6 -> Mean = 5.6 / 6 = 0.93333...
    # Agreement = 1 - (0.93333... / 2.0) = 0.5333...
    stances = {"a": 0.8, "b": 0.6, "c": -0.2, "d": -0.8}
    res = compute_round_agreement(round_num=2, stances=stances)

    assert pytest.approx(res.mean_distance, rel=1e-3) == 0.9333
    assert pytest.approx(res.agreement_score, rel=1e-3) == 0.5333
    assert res.interpretation == "Significant Polarization" or res.interpretation == "Moderate Debate"
    assert len(res.pairwise_distances) == 6
    assert res.pairwise_distances["a vs b"] == 0.2
    assert res.pairwise_distances["a vs d"] == 1.6


def test_compute_round_agreement_edge_cases():
    # Empty
    empty_res = compute_round_agreement(round_num=0, stances={})
    assert empty_res.agreement_score is None
    assert empty_res.agent_count == 0

    # Single agent
    single_res = compute_round_agreement(round_num=0, stances={"solo": 0.5})
    assert single_res.agreement_score is None
    assert single_res.mean_distance is None
    assert single_res.agent_count == 1

    # List input
    list_res = compute_round_agreement(round_num=0, stances=[0.5, 0.5])
    assert list_res.agreement_score == 1.0


def test_compute_discussion_agreement_on_saved_record_fixture():
    data = {
        "config": {"discussion_id": "fixture", "topic": "Should the proposal be adopted?", "agent_ids": ["a", "b"], "num_rounds": 3},
        "messages": [{"round_num": r, "sender_id": "a", "recipient_ids": ["b"]} for r in range(3)],
        "opinions": [
            {"agent_id": aid, "round_num": r, "stance": "I support the proposal." if aid == "a" or r > 0 else "I oppose the proposal."}
            for aid in ["a", "b"] for r in range(4)
        ],
    }
    result = compute_discussion_agreement(data)
    assert len(result.round_agreements) == 4
    assert result.overall_trend == "Converging"
    assert result.get_round_agreement(0).agreement_score == .2
    assert result.get_round_agreement(1).agreement_score == 1


def test_compute_discussion_agreement_trends():
    # Test Converging trend
    traj_converging = OpinionTrajectoryResult(
        discussion_id="converging-test",
        trajectories={
            "a": [
                AgentStancePoint(agent_id="a", round_num=0, stance_value=1.0),
                AgentStancePoint(agent_id="a", round_num=1, stance_value=0.5),
                AgentStancePoint(agent_id="a", round_num=2, stance_value=0.2),
            ],
            "b": [
                AgentStancePoint(agent_id="b", round_num=0, stance_value=-1.0),
                AgentStancePoint(agent_id="b", round_num=1, stance_value=-0.3),
                AgentStancePoint(agent_id="b", round_num=2, stance_value=0.1),
            ],
        },
    )
    res_conv = compute_discussion_agreement(traj_converging)
    assert res_conv.overall_trend == "Converging"
    assert res_conv.round_agreements[0].agreement_score < res_conv.round_agreements[-1].agreement_score

    # Test Diverging trend
    traj_diverging = OpinionTrajectoryResult(
        discussion_id="diverging-test",
        trajectories={
            "a": [
                AgentStancePoint(agent_id="a", round_num=0, stance_value=0.1),
                AgentStancePoint(agent_id="a", round_num=1, stance_value=0.9),
            ],
            "b": [
                AgentStancePoint(agent_id="b", round_num=0, stance_value=0.0),
                AgentStancePoint(agent_id="b", round_num=1, stance_value=-0.9),
            ],
        },
    )
    res_div = compute_discussion_agreement(traj_diverging)
    assert res_div.overall_trend == "Diverging"
    assert res_div.round_agreements[0].agreement_score > res_div.round_agreements[-1].agreement_score
