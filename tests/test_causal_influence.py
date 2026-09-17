"""Unit tests for Analytical Counterfactual Ablation Causal Evaluator."""

import json
from unittest.mock import MagicMock
import pytest

from src.analytics.causal_influence import compute_counterfactual_influence
from src.analytics.models import (
    AgentStancePoint,
    DiscussionCausalResult,
    OpinionTrajectoryResult,
)
from src.reporting.report import generate_markdown_report


def test_causal_influence_no_exchanges():
    """Verify that discussions with no routed peer exchanges produce empty result safely."""
    data = {
        "config": {"discussion_id": "test_empty", "topic": "Debate", "agent_ids": ["a", "b"]},
        "messages": [],
    }
    traj = OpinionTrajectoryResult(
        discussion_id="test_empty",
        trajectories={
            "a": [AgentStancePoint(agent_id="a", round_num=0, stance_value=0.5)],
            "b": [AgentStancePoint(agent_id="b", round_num=0, stance_value=-0.5)],
        },
    )
    result = compute_counterfactual_influence(data, trajectories=traj)
    assert isinstance(result, DiscussionCausalResult)
    assert result.top_causal_influencer is None
    assert result.evaluated_exchanges_count == 0
    assert result.agent_causal_influences["a"].status == "no_exchanges"


def test_causal_influence_with_mock_llm():
    """Verify counterfactual shift tau calculation with a mock LLM."""
    data = {
        "config": {
            "discussion_id": "test_causal",
            "topic": "Tuchel tactics vs physical exhaustion",
            "agent_ids": ["tactical_analyst", "fan_analyst"],
        },
        "messages": [
            {
                "round_num": 0,
                "sender_id": "tactical_analyst",
                "recipient_ids": ["fan_analyst"],
                "content": "England created 4 big chances by overloading the half-spaces.",
            },
            {
                "round_num": 1,
                "sender_id": "fan_analyst",
                "recipient_ids": ["tactical_analyst"],
                "content": "I concede that England's tactics were dominant in the first half.",
            },
        ],
    }

    traj = OpinionTrajectoryResult(
        discussion_id="test_causal",
        trajectories={
            "tactical_analyst": [
                AgentStancePoint(agent_id="tactical_analyst", round_num=0, stance_value=0.8),
                AgentStancePoint(agent_id="tactical_analyst", round_num=1, stance_value=0.85),
            ],
            "fan_analyst": [
                AgentStancePoint(agent_id="fan_analyst", round_num=0, stance_value=-0.7),
                AgentStancePoint(agent_id="fan_analyst", round_num=1, stance_value=0.3),  # Factual shift to +0.3
            ],
        },
    )

    # Mock LLM returns counterfactual stance = -0.5 (had tactical analyst remained silent)
    # Causal shift = |0.3 - (-0.5)| = 0.8
    mock_llm = MagicMock()
    mock_llm.generate.return_value = json.dumps([
        {
            "exchange_id": 0,
            "counterfactual_stance": -0.5,
            "causal_shift": 0.8,
            "attribution_rationale": "Tactical evidence directly persuaded the fan analyst to concede the merit argument.",
        }
    ])

    result = compute_counterfactual_influence(
        data,
        trajectories=traj,
        llm_client=mock_llm,
        positive_pole="Tuchel tactics won on merit",
        negative_pole="Physical exhaustion and referee chaos",
    )

    assert result.evaluated_exchanges_count == 1
    assert result.top_causal_influencer == "tactical_analyst"

    tactical_inf = result.agent_causal_influences["tactical_analyst"]
    assert tactical_inf.causal_score == 0.8
    assert "Genuine Persuader" in tactical_inf.causal_classification
    assert len(tactical_inf.exchanges) == 1

    ex = tactical_inf.exchanges[0]
    assert ex.factual_stance == 0.3
    assert ex.counterfactual_stance == -0.5
    assert ex.causal_shift == 0.8
    assert "concede" in ex.attribution_rationale


def test_report_includes_causal_ablation_section(tmp_path):
    """Verify that the Markdown report includes the comparative causal table when present."""
    analytics_data = {
        "discussion_id": "test_report",
        "metadata": {"scoring_method": "llm", "scores_reused": False},
        "task1_opinion_trajectories": {
            "discussion_id": "test_report",
            "agent_ids": ["tactical_analyst", "fan_analyst"],
            "total_rounds": 1,
            "trajectories": {
                "tactical_analyst": [{"round_num": 0, "stance_value": 0.8}, {"round_num": 1, "stance_value": 0.85}],
                "fan_analyst": [{"round_num": 0, "stance_value": -0.7}, {"round_num": 1, "stance_value": 0.3}],
            },
        },
        "task2_discussion_agreement": {
            "round_agreements": [{"round_num": 0, "agreement_score": 0.4}, {"round_num": 1, "agreement_score": 0.7}],
            "overall_trend": "Converging",
        },
        "task3_agent_influence": {
            "method": "pearson_gap_change",
            "agent_influences": {
                "tactical_analyst": {"influence_score": 0.75, "status": "computed"},
                "fan_analyst": {"influence_score": -0.2, "status": "computed"},
            },
        },
        "task4_sentiment": {"summary": {"total_messages": 2, "scored_messages": 2, "mean_compound": 0.2}},
        "task3_causal_influence": {
            "top_causal_influencer": "tactical_analyst",
            "agent_causal_influences": {
                "tactical_analyst": {
                    "agent_id": "tactical_analyst",
                    "causal_score": 0.80,
                    "exchange_count": 1,
                    "causal_classification": "Genuine Persuader (High Causal Impact)",
                    "exchanges": [
                        {
                            "round_num": 0,
                            "sender_id": "tactical_analyst",
                            "recipient_id": "fan_analyst",
                            "factual_stance": 0.30,
                            "counterfactual_stance": -0.50,
                            "causal_shift": 0.80,
                            "attribution_rationale": "Tactical evidence swayed the fan.",
                        }
                    ],
                }
            },
        },
    }

    report_file = tmp_path / "test_report.md"
    content = generate_markdown_report(analytics_data, output_path=report_file)

    assert "Observational Correlation vs. Counterfactual Causal Attribution" in content
    assert "Lead Persuader (Causal)" in content
    assert "Genuine Persuader" in content
    assert "Tactical evidence swayed the fan" in content
