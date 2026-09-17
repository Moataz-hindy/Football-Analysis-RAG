"""Week 4 Acceptance Tests: Reports, Visualizations, and Full Pipeline.

Verifies:
  1. Weighted interaction graph (all agents as nodes, directed edges, message weights).
  2. Opinion trajectory chart generation from saved scores without repeating model calls.
  3. Automatic Markdown report generation with all four metric categories, findings,
     and required methodological limitations.
  4. End-to-end analytics pipeline execution producing JSON, charts, and report.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from src.analytics.run_analytics import run_analytics_pipeline
from src.reporting.report import generate_markdown_report
from src.visualization.interaction_graph import (
    extract_interaction_data,
    generate_interaction_graph_from_discussion,
    plot_interaction_graph,
)
from src.visualization.opinion_trajectory import (
    generate_opinion_trajectory_from_discussion,
    plot_opinion_trajectory,
)


@pytest.fixture
def scored_discussion_fixture():
    """Synthetic discussion with defined numeric stances across 3 rounds."""
    agent_ids = ["tactical_analyst", "statistical_analyst", "fan_analyst", "refereeing_analyst"]
    num_rounds = 2
    opinions = []
    # R0, R1, R2 for each agent with deliberate stance movement
    stances = {
        "tactical_analyst": [0.6, 0.4, 0.2],
        "statistical_analyst": [0.7, 0.7, 0.5],
        "fan_analyst": [-0.8, -0.5, -0.2],
        "refereeing_analyst": [0.1, 0.2, 0.3],
    }
    for r in range(num_rounds + 1):
        for ag in agent_ids:
            st_val = stances[ag][r]
            opinions.append({
                "agent_id": ag,
                "round_num": r,
                "stance": f"Stance {st_val:+.2f} on tactical setup",
                "reasoning": f"Reasoning round {r} for {ag}",
                "sources_used": ["IFAB Rule 12"],
            })

    messages = [
        # Round 0 messages
        {
            "round_num": 0,
            "sender_id": "tactical_analyst",
            "recipient_ids": ["statistical_analyst", "fan_analyst"],
            "content": "Defensive block must stay compact and structured.",
        },
        {
            "round_num": 0,
            "sender_id": "statistical_analyst",
            "recipient_ids": ["tactical_analyst"],
            "content": "Expected goals conceded drops significantly with low block.",
        },
        {
            "round_num": 0,
            "sender_id": "fan_analyst",
            "recipient_ids": ["refereeing_analyst"],
            "content": "That was clearly an aggressive foul in the box!",
        },
        # Round 1 messages
        {
            "round_num": 1,
            "sender_id": "tactical_analyst",
            "recipient_ids": ["statistical_analyst"],
            "content": "Agreed, empirical metrics support adjusting the line.",
        },
        {
            "round_num": 1,
            "sender_id": "refereeing_analyst",
            "recipient_ids": ["fan_analyst"],
            "content": "Contact was negligible under Law 12 guidelines.",
        },
        {
            "round_num": 1,
            "sender_id": "statistical_analyst",
            "recipient_ids": ["fan_analyst"],
            "content": "Objective tackle success rate was above 80 percent.",
        },
    ]

    return {
        "config": {
            "discussion_id": "test_acc_discussion_01",
            "topic": "Should defensive structure take precedence over attacking fluidity?",
            "num_rounds": num_rounds,
            "agent_ids": agent_ids,
            "graph": {
                "tactical_analyst": ["statistical_analyst", "fan_analyst"],
                "statistical_analyst": ["tactical_analyst", "fan_analyst"],
                "fan_analyst": ["refereeing_analyst"],
                "refereeing_analyst": ["fan_analyst"],
            },
            "llm_model": "test-model",
            "llm_temperature": 0.2,
        },
        "messages": messages,
        "opinions": opinions,
    }


# ===========================================================================
# 1. Weighted Interaction Graph Acceptance Tests
# ===========================================================================

class TestInteractionGraphAcceptance:
    def test_all_agents_represented_as_nodes(self, scored_discussion_fixture):
        graph, config = extract_interaction_data(scored_discussion_fixture)
        expected_agents = set(scored_discussion_fixture["config"]["agent_ids"])
        assert set(graph.nodes()) == expected_agents

    def test_directed_edges_and_message_weights(self, scored_discussion_fixture):
        graph, _ = extract_interaction_data(scored_discussion_fixture)

        # tactical_analyst sent to statistical_analyst twice (R0 and R1)
        assert graph.has_edge("tactical_analyst", "statistical_analyst")
        assert graph["tactical_analyst"]["statistical_analyst"]["weight"] == 2

        # tactical_analyst sent to fan_analyst once (R0)
        assert graph.has_edge("tactical_analyst", "fan_analyst")
        assert graph["tactical_analyst"]["fan_analyst"]["weight"] == 1

        # fan_analyst sent to refereeing_analyst once
        assert graph.has_edge("fan_analyst", "refereeing_analyst")
        assert graph["fan_analyst"]["refereeing_analyst"]["weight"] == 1

        # refereeing_analyst sent to fan_analyst once
        assert graph.has_edge("refereeing_analyst", "fan_analyst")
        assert graph["refereeing_analyst"]["fan_analyst"]["weight"] == 1

    def test_isolated_agent_included_in_nodes(self):
        data = {
            "config": {
                "discussion_id": "disc_isolated",
                "topic": "Solo test",
                "agent_ids": ["active_agent", "silent_agent"],
                "num_rounds": 1,
            },
            "messages": [
                {
                    "round_num": 0,
                    "sender_id": "active_agent",
                    "recipient_ids": ["active_agent"],
                    "content": "Talking to myself",
                }
            ],
            "opinions": [],
        }
        graph, _ = extract_interaction_data(data)
        assert "silent_agent" in graph.nodes()
        assert graph.nodes["silent_agent"]["sent"] == 0
        assert graph.nodes["silent_agent"]["received"] == 0

    def test_generates_valid_non_empty_png(self, tmp_path, scored_discussion_fixture):
        output_file = tmp_path / "interaction_graph.png"
        graph, config = extract_interaction_data(scored_discussion_fixture)
        saved_path = plot_interaction_graph(graph, config, output_file)

        assert Path(saved_path).exists()
        assert Path(saved_path).stat().st_size > 1000  # Non-trivial image file


# ===========================================================================
# 2. Chart Integration from Saved Scores Acceptance Tests
# ===========================================================================

class TestChartIntegrationAcceptance:
    def test_opinion_chart_generated_from_saved_scores_without_scoring(
        self, tmp_path, scored_discussion_fixture
    ):
        # First create a mock analytics output with pre-scored trajectories
        analytics_dict = {
            "discussion_id": scored_discussion_fixture["config"]["discussion_id"],
            "topic": scored_discussion_fixture["config"]["topic"],
            "task1_opinion_trajectories": {
                "discussion_id": scored_discussion_fixture["config"]["discussion_id"],
                "topic": scored_discussion_fixture["config"]["topic"],
                "total_rounds": 2,
                "agent_ids": scored_discussion_fixture["config"]["agent_ids"],
                "trajectories": {
                    "tactical_analyst": [
                        {"round_num": 0, "stance_value": 0.6, "opinion_change": None},
                        {"round_num": 1, "stance_value": 0.4, "opinion_change": -0.2},
                        {"round_num": 2, "stance_value": 0.2, "opinion_change": -0.2},
                    ],
                    "fan_analyst": [
                        {"round_num": 0, "stance_value": -0.8, "opinion_change": None},
                        {"round_num": 1, "stance_value": -0.5, "opinion_change": 0.3},
                        {"round_num": 2, "stance_value": -0.2, "opinion_change": 0.3},
                    ],
                },
            },
        }
        scores_path = tmp_path / "saved_analytics.json"
        scores_path.write_text(json.dumps(analytics_dict), encoding="utf-8")

        # Generate chart using scores_from
        chart_path = generate_opinion_trajectory_from_discussion(
            scored_discussion_fixture,
            output_dir=tmp_path,
            scores_from=scores_path,
        )

        assert Path(chart_path).exists()
        assert Path(chart_path).stat().st_size > 1000

    def test_chart_generation_directly_from_analytics_file(self, tmp_path):
        analytics_dict = {
            "discussion_id": "direct_analytics_disc",
            "topic": "Direct Analytics Rendering",
            "task1_opinion_trajectories": {
                "discussion_id": "direct_analytics_disc",
                "topic": "Direct Analytics Rendering",
                "total_rounds": 1,
                "agent_ids": ["agent_1", "agent_2"],
                "trajectories": {
                    "agent_1": [
                        {"round_num": 0, "stance_value": 0.5, "opinion_change": None},
                        {"round_num": 1, "stance_value": 0.8, "opinion_change": 0.3},
                    ],
                    "agent_2": [
                        {"round_num": 0, "stance_value": -0.4, "opinion_change": None},
                        {"round_num": 1, "stance_value": -0.1, "opinion_change": 0.3},
                    ],
                },
            },
        }
        analytics_file = tmp_path / "analytics_result.json"
        analytics_file.write_text(json.dumps(analytics_dict), encoding="utf-8")

        chart_path = generate_opinion_trajectory_from_discussion(
            analytics_file,
            output_dir=tmp_path,
        )
        assert Path(chart_path).exists()
        assert Path(chart_path).stat().st_size > 1000


# ===========================================================================
# 3. Automatic Markdown Report Acceptance Tests
# ===========================================================================

class TestMarkdownReportAcceptance:
    @pytest.fixture
    def mock_full_analytics(self):
        return {
            "schema_version": 2,
            "discussion_id": "report_acc_run_01",
            "topic": "Is low block defensive posture statistically superior in knockout tournaments?",
            "metadata": {
                "scoring_method": "llm_calibrated",
                "scores_reused": True,
                "scored_snapshots": 8,
                "observed_snapshots": 8,
            },
            "task1_opinion_trajectories": {
                "discussion_id": "report_acc_run_01",
                "topic": "Is low block defensive posture statistically superior in knockout tournaments?",
                "total_rounds": 1,
                "agent_ids": ["tactical_analyst", "statistical_analyst"],
                "trajectories": {
                    "tactical_analyst": [
                        {"round_num": 0, "stance_value": 0.75, "opinion_change": None},
                        {"round_num": 1, "stance_value": 0.50, "opinion_change": -0.25},
                    ],
                    "statistical_analyst": [
                        {"round_num": 0, "stance_value": 0.60, "opinion_change": None},
                        {"round_num": 1, "stance_value": 0.65, "opinion_change": 0.05},
                    ],
                },
            },
            "task2_discussion_agreement": {
                "discussion_id": "report_acc_run_01",
                "overall_trend": "Convergence",
                "initial_agreement": 0.85,
                "final_agreement": 0.925,
                "agreement_shift": 0.075,
                "round_agreements": [
                    {
                        "round_num": 0,
                        "agreement_score": 0.85,
                        "stance_std": 0.075,
                        "stance_min": 0.60,
                        "stance_max": 0.75,
                    },
                    {
                        "round_num": 1,
                        "agreement_score": 0.925,
                        "stance_std": 0.075,
                        "stance_min": 0.50,
                        "stance_max": 0.65,
                    },
                ],
            },
            "task3_agent_influence": {
                "method": "pearson_message_volume_correlation",
                "limitations": ["Limited observations"],
                "agent_influences": {
                    "tactical_analyst": {
                        "influence_score": 0.42,
                        "status": "computed",
                        "num_targets": 1,
                        "outbound_messages": 3,
                    },
                    "statistical_analyst": {
                        "influence_score": 0.15,
                        "status": "computed",
                        "num_targets": 1,
                        "outbound_messages": 2,
                    },
                },
                "pairwise_correlations": [
                    {
                        "sender": "tactical_analyst",
                        "recipient": "statistical_analyst",
                        "correlation": 0.42,
                        "n_observations": 2,
                        "status": "computed",
                    }
                ],
            },
            "task4_sentiment": {
                "method": "vader_compound",
                "summary": {
                    "message_count": 5,
                    "scored_messages": 5,
                    "mean_score": 0.28,
                    "label_counts": {"positive": 3, "neutral": 2, "negative": 0},
                },
                "messages": [
                    {"agent_id": "tactical_analyst", "round_num": 0, "score": 0.35, "label": "positive"},
                    {"agent_id": "statistical_analyst", "round_num": 0, "score": 0.20, "label": "neutral"},
                    {"agent_id": "tactical_analyst", "round_num": 1, "score": 0.40, "label": "positive"},
                    {"agent_id": "statistical_analyst", "round_num": 1, "score": 0.18, "label": "neutral"},
                    {"agent_id": "tactical_analyst", "round_num": 1, "score": 0.27, "label": "positive"},
                ],
            },
        }

    def test_report_is_non_empty_markdown(self, tmp_path, mock_full_analytics):
        out_path = tmp_path / "acceptance_report.md"
        report_text = generate_markdown_report(mock_full_analytics, output_path=out_path)

        assert Path(out_path).exists()
        assert Path(out_path).stat().st_size > 0
        assert len(report_text) > 500

    def test_all_four_categories_present(self, mock_full_analytics):
        report_text = generate_markdown_report(mock_full_analytics)

        # Overview
        assert "Multi-Agent Discussion Analytics Report" in report_text
        assert mock_full_analytics["discussion_id"] in report_text
        assert mock_full_analytics["topic"] in report_text

        # 1. Opinion Dynamics
        assert "1. Opinion Dynamics & Stance Evolution" in report_text
        assert "tactical_analyst" in report_text
        assert "statistical_analyst" in report_text

        # 2. Agreement
        assert "2. Agreement & Group Consensus Dynamics" in report_text
        assert "Convergence" in report_text

        # 3. Influence
        assert "3. Agent Influence & Cross-Agent Persuasion" in report_text
        assert "tactical_analyst" in report_text

        # 4. Sentiment
        assert "4. Communication Sentiment & Discourse Tone" in report_text
        assert "Total Messages Analyzed" in report_text

    def test_methodological_limitations_explicitly_stated(self, mock_full_analytics):
        report_text = generate_markdown_report(mock_full_analytics)

        # Exact disclosure requirements from specification
        assert "The correlation-based influence metric implemented here remains exploratory" in report_text
        assert "simplified numerical representation" in report_text
        assert "limited observation window" in report_text
        assert "Alignment vs. Correctness" in report_text


# ===========================================================================
# 4. Full Pipeline Integration Acceptance Tests
# ===========================================================================

class TestFullPipelineAcceptance:
    def test_pipeline_generates_json_charts_and_report_end_to_end(
        self, tmp_path, scored_discussion_fixture
    ):
        input_file = tmp_path / "discussion_input.json"
        input_file.write_text(json.dumps(scored_discussion_fixture), encoding="utf-8")

        output_json = tmp_path / "analytics_output.json"
        reports_dir = tmp_path / "reports"

        result = run_analytics_pipeline(
            input_path=str(input_file),
            output_path=str(output_json),
            generate_charts=True,
            generate_report=True,
            reports_dir=str(reports_dir),
        )

        # 1. JSON output exists and has all categories
        assert output_json.exists()
        assert output_json.stat().st_size > 0
        assert "task1_opinion_trajectories" in result
        assert "task2_discussion_agreement" in result
        assert "task3_agent_influence" in result
        assert "task4_sentiment" in result

        # 2. Interaction graph generated and non-empty
        graph_file = reports_dir / f"interaction_graph_{scored_discussion_fixture['config']['discussion_id']}.png"
        assert graph_file.exists()
        assert graph_file.stat().st_size > 1000

        # 3. Markdown report generated and non-empty
        report_file = reports_dir / f"discussion_report_{scored_discussion_fixture['config']['discussion_id']}.md"
        assert report_file.exists()
        assert report_file.stat().st_size > 500

        content = report_file.read_text(encoding="utf-8")
        assert "Multi-Agent Discussion Analytics Report" in content
        assert "Opinion Dynamics" in content
        assert "Agreement" in content
        assert "Agent Influence" in content
        assert "Sentiment" in content
        assert "Methodological Limitations" in content

    def test_analytics_engine_object_interface(
        self, tmp_path, scored_discussion_fixture
    ):
        from src.analytics import AnalyticsEngine
        from src.discussion.types import DiscussionResult

        engine = AnalyticsEngine(reports_dir=tmp_path / "engine_reports")

        # Test with direct dictionary input
        result_dict = engine.analyze(
            scored_discussion_fixture,
            generate_charts=True,
            generate_report=True,
        )
        assert "task1_opinion_trajectories" in result_dict
        assert "task2_discussion_agreement" in result_dict
        assert "task3_agent_influence" in result_dict
        assert "task4_sentiment" in result_dict
        assert "visualizations" in result_dict
        assert "report_path" in result_dict
        assert Path(result_dict["visualizations"]["interaction_graph"]).exists()
        assert Path(result_dict["report_path"]).exists()

        # Test with DiscussionResult object input
        discussion_obj = DiscussionResult.from_dict(scored_discussion_fixture)
        result_obj = engine.analyze(discussion_obj)
        assert result_obj["discussion_id"] == scored_discussion_fixture["config"]["discussion_id"]
        assert len(result_obj["task1_opinion_trajectories"]["agent_ids"]) == 4
