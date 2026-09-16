import json

import pytest

from src.analytics.correlation_influence import compute_correlation_influence
from src.analytics.run_analytics import run_analytics_pipeline


def example(direction=1):
    # Three gaps: .2, .4, .6.
    # Recipient changes: direction * [.1, .2, .3].
    b = [0, .1 * direction, .3 * direction, .6 * direction]
    a = [.2 + b[0], .4 + b[1], .6 + b[2], .9]
    data = {
        "config": {
            "discussion_id": "test",
            "topic": "Test proposition",
            "agent_ids": ["a", "b"],
            "num_rounds": 3,
        },
        "messages": [
            {
                "sender_id": "a", "recipient_ids": ["b"],
                "round_num": r, "content": "I support the proposition.",
            }
            for r in range(4)
        ],
    }
    cached = {
        "task1_opinion_trajectories": {
            "discussion_id": "test",
            "agent_ids": ["a", "b"],
            "trajectories": {
                agent: [
                    {"round_num": r, "stance_value": value}
                    for r, value in enumerate(values)
                ]
                for agent, values in (("a", a), ("b", b))
            },
        },
    }
    return data, cached


@pytest.mark.parametrize("direction", [1, -1])
def test_known_correlation(direction):
    data, cached = example(direction)
    result = compute_correlation_influence(data, cached)["agent_influences"]
    assert result["a"]["influence_score"] == pytest.approx(direction)
    assert result["a"]["observation_count"] == 3
    assert result["b"]["status"] == "insufficient_data"


def test_missing_routes():
    data, cached = example()
    data["messages"] = []
    result = compute_correlation_influence(data, cached)
    assert all(
        row["influence_score"] is None
        for row in result["agent_influences"].values()
    )


def test_too_few_observations():
    data, cached = example()
    data["messages"] = data["messages"][:2]
    result = compute_correlation_influence(data, cached)
    assert result["agent_influences"]["a"]["status"] == "insufficient_data"


def test_constant_recipient_position():
    data, cached = example()
    for point in cached["task1_opinion_trajectories"]["trajectories"]["b"]:
        point["stance_value"] = 0
    result = compute_correlation_influence(data, cached)
    assert result["agent_influences"]["a"]["status"] == "constant_signal"
    assert result["agent_influences"]["a"]["influence_score"] is None


def test_missing_stance_is_not_zero():
    data, cached = example()
    cached["task1_opinion_trajectories"]["trajectories"]["b"][1]["stance_value"] = None
    result = compute_correlation_influence(data, cached)
    assert result["agent_influences"]["a"]["status"] == "insufficient_data"


def test_engine_reuses_scores_without_scoring(tmp_path, monkeypatch):
    data, _ = example()
    data["opinions"] = [
        {"agent_id": agent, "round_num": r,
         "stance": "I agree.", "reasoning": "Test evidence"}
        for agent in ["a", "b"] for r in range(4)
    ]
    source = tmp_path / "discussion.json"
    saved = tmp_path / "scores.json"
    output = tmp_path / "combined.json"
    source.write_text(json.dumps(data))

    run_analytics_pipeline(source, output_path=saved)

    def forbidden(*args, **kwargs):
        pytest.fail("Cached mode must not invoke the stance scorer")

    monkeypatch.setattr(
        "src.analytics.run_analytics.compute_opinion_trajectories", forbidden
    )
    result = run_analytics_pipeline(
        source, scores_from=saved, output_path=output
    )
    assert result["metadata"]["scores_reused"]
    assert len(result["task4_sentiment"]["messages"]) == len(data["messages"])
    assert result["task3_agent_influence"]["method"].startswith("pearson")
    assert json.loads(output.read_text()) == result

    with pytest.raises(ValueError, match="overwrite"):
        run_analytics_pipeline(source, scores_from=saved, output_path=saved)

    data["opinions"][0]["reasoning"] = "Changed evidence"
    source.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="changed"):
        run_analytics_pipeline(source, scores_from=saved)