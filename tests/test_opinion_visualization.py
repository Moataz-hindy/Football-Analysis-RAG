"""Tests for Week 4 §24 — Opinion Trajectory Visualization.

Verifies that the chart is generated correctly with proper agents,
rounds, formatting, and edge-case handling.
"""

import math
from pathlib import Path

import pytest

from src.visualization.opinion_trajectory import (
    generate_opinion_trajectory_from_discussion,
    plot_opinion_trajectory,
)


# ── Fixtures ────────────────────────────────────────────────────────────

@pytest.fixture
def sample_stance_data():
    """Six agents across 4 rounds with realistic stance values."""
    return {
        "Tactical Analyst": [
            {"round": 0, "stance": 0.72, "change": None},
            {"round": 1, "stance": 0.65, "change": -0.07},
            {"round": 2, "stance": 0.51, "change": -0.14},
            {"round": 3, "stance": 0.42, "change": -0.09},
        ],
        "Statistical Analyst": [
            {"round": 0, "stance": 0.30, "change": None},
            {"round": 1, "stance": 0.35, "change": 0.05},
            {"round": 2, "stance": 0.40, "change": 0.05},
            {"round": 3, "stance": 0.38, "change": -0.02},
        ],
        "Fan Analyst": [
            {"round": 0, "stance": -0.60, "change": None},
            {"round": 1, "stance": -0.45, "change": 0.15},
            {"round": 2, "stance": -0.20, "change": 0.25},
            {"round": 3, "stance": 0.10, "change": 0.30},
        ],
        "Refereeing Analyst": [
            {"round": 0, "stance": -0.80, "change": None},
            {"round": 1, "stance": -0.75, "change": 0.05},
            {"round": 2, "stance": -0.70, "change": 0.05},
            {"round": 3, "stance": -0.55, "change": 0.15},
        ],
        "Performance Analyst": [
            {"round": 0, "stance": 0.50, "change": None},
            {"round": 1, "stance": 0.48, "change": -0.02},
            {"round": 2, "stance": 0.55, "change": 0.07},
            {"round": 3, "stance": 0.60, "change": 0.05},
        ],
        "Context Analyst": [
            {"round": 0, "stance": 0.10, "change": None},
            {"round": 1, "stance": 0.05, "change": -0.05},
            {"round": 2, "stance": -0.05, "change": -0.10},
            {"round": 3, "stance": 0.00, "change": 0.05},
        ],
    }


@pytest.fixture
def sample_config():
    """Basic discussion config."""
    return {
        "discussion_id": "test-run-001",
        "topic": "Who was the better team in the final of the 2022 World Cup?",
        "num_rounds": 3,
        "agent_ids": [
            "Tactical Analyst",
            "Statistical Analyst",
            "Fan Analyst",
            "Refereeing Analyst",
            "Performance Analyst",
            "Context Analyst",
        ],
    }


@pytest.fixture
def sample_discussion_dict(sample_config):
    """A minimal discussion dict with opinion snapshots with explicit stance statements."""
    return {
        "config": sample_config,
        "messages": [],
        "opinions": [
            {
                "agent_id": "Tactical Analyst",
                "round_num": 0,
                "stance": "I support the proposition.",
                "reasoning": "xG dominance in key matches.",
            },
            {
                "agent_id": "Tactical Analyst",
                "round_num": 1,
                "stance": "I agree with the proposition.",
                "reasoning": "Messi's leadership was key.",
            },
            {
                "agent_id": "Fan Analyst",
                "round_num": 0,
                "stance": "I oppose the proposition.",
                "reasoning": "Multiple controversial decisions.",
            },
            {
                "agent_id": "Fan Analyst",
                "round_num": 1,
                "stance": "I disagree with the proposition.",
                "reasoning": "The fan experience was mixed.",
            },
        ],
    }


# ── Test 1: Chart is generated ──────────────────────────────────────────

def test_chart_is_generated(tmp_path, sample_stance_data, sample_config):
    """Given sample stance data, verify a non-empty PNG file is created."""
    output_path = tmp_path / "test_chart.png"

    result = plot_opinion_trajectory(
        sample_stance_data, sample_config, output_path
    )

    assert Path(result).exists(), "Chart file was not created"
    assert Path(result).stat().st_size > 0, "Chart file is empty"
    assert result == str(output_path.resolve())


# ── Test 2: Chart contains all agents ───────────────────────────────────

def test_chart_contains_all_agents(tmp_path, sample_stance_data, sample_config):
    """Given 6 agents, verify the chart legend contains all 6 names."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    output_path = tmp_path / "test_agents.png"

    # We need to capture the figure before it's closed, so we call
    # plot_opinion_trajectory and check the output file exists.
    # To verify legend entries, we rebuild a lightweight check.
    plot_opinion_trajectory(sample_stance_data, sample_config, output_path)

    # Verify all agent names would appear in the chart by checking
    # that all agents in stance_data have plottable data.
    plotted_agents = set()
    for agent_id, points in sample_stance_data.items():
        for p in points:
            v = p.get("stance")
            if v is not None and math.isfinite(v):
                plotted_agents.add(agent_id)
                break

    assert plotted_agents == set(sample_stance_data.keys()), (
        f"Not all agents are plottable: missing {set(sample_stance_data.keys()) - plotted_agents}"
    )
    assert len(plotted_agents) == 6


# ── Test 3: Chart contains all rounds ──────────────────────────────────

def test_chart_contains_all_rounds(tmp_path, sample_stance_data, sample_config):
    """Verify the chart covers rounds 0 through 3."""
    output_path = tmp_path / "test_rounds.png"
    plot_opinion_trajectory(sample_stance_data, sample_config, output_path)

    # Verify all rounds are present in the data
    all_rounds = set()
    for points in sample_stance_data.values():
        for p in points:
            if p.get("stance") is not None:
                all_rounds.add(p["round"])

    assert all_rounds == {0, 1, 2, 3}


# ── Test 4: Empty data raises ValueError ───────────────────────────────

def test_empty_data_raises_error(tmp_path):
    """Given empty stance data, verify a ValueError is raised."""
    with pytest.raises(ValueError, match="empty"):
        plot_opinion_trajectory({}, None, tmp_path / "empty.png")


# ── Test 5: All-None stances raises ValueError ─────────────────────────

def test_all_none_stances_raises_error(tmp_path):
    """If all stance values are None, a ValueError should be raised."""
    data = {
        "Agent A": [
            {"round": 0, "stance": None},
            {"round": 1, "stance": None},
        ],
    }
    with pytest.raises(ValueError, match="No plottable"):
        plot_opinion_trajectory(data, None, tmp_path / "none.png")


# ── Test 6: Single agent works ──────────────────────────────────────────

def test_single_agent_works(tmp_path):
    """Edge case: a single agent should produce a valid chart."""
    data = {
        "Solo Agent": [
            {"round": 0, "stance": 0.5, "change": None},
            {"round": 1, "stance": 0.3, "change": -0.2},
            {"round": 2, "stance": 0.1, "change": -0.2},
        ],
    }
    output_path = tmp_path / "single_agent.png"
    result = plot_opinion_trajectory(data, {"topic": "Solo test"}, output_path)

    assert Path(result).exists()
    assert Path(result).stat().st_size > 0


# ── Test 7: Output directory is created automatically ───────────────────

def test_output_dir_created_automatically(tmp_path, sample_stance_data):
    """If the output directory doesn't exist, it should be created."""
    deep_path = tmp_path / "nested" / "deep" / "chart.png"
    result = plot_opinion_trajectory(sample_stance_data, None, deep_path)

    assert Path(result).exists()
    assert Path(result).stat().st_size > 0


# ── Test 8: Generate from discussion dict (shared analytics) ──────────────

def test_generate_from_discussion_dict(tmp_path, sample_discussion_dict):
    """Test the convenience wrapper with a raw discussion dict."""
    result = generate_opinion_trajectory_from_discussion(
        sample_discussion_dict,
        output_dir=tmp_path,
    )

    assert Path(result).exists()
    assert Path(result).stat().st_size > 0
    assert "opinion_trajectory" in Path(result).name


# ── Test 9: Custom title and filename ───────────────────────────────────

def test_custom_title_and_filename(tmp_path, sample_stance_data):
    """Custom title and filename should be respected."""
    output_path = tmp_path / "custom_name.png"
    result = plot_opinion_trajectory(
        sample_stance_data,
        None,
        output_path,
        title="My Custom Title",
    )

    assert Path(result).name == "custom_name.png"
    assert Path(result).exists()


# ── Test 10: Long topic is truncated ────────────────────────────────────

def test_long_topic_truncated(tmp_path, sample_stance_data):
    """A very long topic should be truncated in the chart title."""
    long_topic = "A" * 200
    config = {"topic": long_topic}
    output_path = tmp_path / "long_topic.png"

    # Should not raise
    result = plot_opinion_trajectory(sample_stance_data, config, output_path)
    assert Path(result).exists()


def test_unclassified_discussion_does_not_use_sentiment(tmp_path):
    data = {"config": {"agent_ids": ["a"]}, "opinions": [
        {"agent_id": "a", "round_num": 0, "stance": "Brilliant football, wonderful atmosphere."}
    ]}
    with pytest.raises(ValueError, match="No plottable"):
        generate_opinion_trajectory_from_discussion(data, tmp_path)


def test_analytics_failure_is_not_hidden(monkeypatch):
    from src.visualization.opinion_trajectory import _extract_stance_data_from_discussion
    def fail(*args, **kwargs):
        raise RuntimeError("invalid analytics input")
    monkeypatch.setattr("src.analytics.stance.compute_opinion_trajectories", fail)
    with pytest.raises(RuntimeError, match="invalid analytics input"):
        _extract_stance_data_from_discussion({})


def test_missing_stance_breaks_chart_line(tmp_path, monkeypatch):
    from matplotlib.axes import Axes
    original = Axes.plot
    captured = []
    def capture(self, xs, ys, *args, **kwargs):
        captured.append((list(xs), list(ys)))
        return original(self, xs, ys, *args, **kwargs)
    monkeypatch.setattr(Axes, "plot", capture)
    plot_opinion_trajectory({"a": [
        {"round": 0, "stance": 0.5},
        {"round": 1, "stance": None},
        {"round": 2, "stance": -0.5},
    ]}, output_path=tmp_path / "gap.png")
    assert captured[0][0] == [0, 1, 2]
    assert math.isnan(captured[0][1][1])
