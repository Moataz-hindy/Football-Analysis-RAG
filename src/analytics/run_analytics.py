"""Analyze a saved discussion locally; extra model calls require --use-llm."""
import argparse
import json
from pathlib import Path

import hashlib

from src.analytics.models import OpinionTrajectoryResult
from src.analytics.correlation_influence import compute_correlation_influence
from src.analytics.agreement import compute_discussion_agreement
from src.analytics.causal_influence import compute_counterfactual_influence
from src.analytics.influence import compute_agent_influence
from src.analytics.stance import compute_opinion_trajectories
from src.discussion.persistence import load_discussion
from src.analytics.sentiment import compute_discussion_sentiment
from src.analytics.validation import validate_discussion


def load_saved_trajectories(saved_path, data, source_hash):
    saved = json.loads(Path(saved_path).read_text(encoding="utf-8"))
    result = OpinionTrajectoryResult.model_validate(
        saved["task1_opinion_trajectories"]
    )
    config = data["config"]

    if (
        result.discussion_id != config["discussion_id"]
        or result.topic != config["topic"]
        or result.total_rounds != config["num_rounds"]
        or set(result.agent_ids) != set(config["agent_ids"])
        or set(result.trajectories) != set(config["agent_ids"])
    ):
        raise ValueError("Saved scores belong to a different discussion")

    previous_hash = saved.get("metadata", {}).get("source_sha256")
    if previous_hash and previous_hash != source_hash:
        raise ValueError("Discussion changed since these scores were saved")

    expected = {
        (op["agent_id"], op["round_num"]): op["stance"]
        for op in data["opinions"]
    }
    received = {}

    for agent, points in result.trajectories.items():
        for point in points:
            key = (agent, point.round_num)
            if point.agent_id != agent or key in received:
                raise ValueError("Invalid or duplicate saved stance")
            received[key] = point.stance_text

        # Derive changes from scores rather than trusting saved deltas.
        points.sort(key=lambda point: point.round_num)
        previous = None
        for point in points:
            point.opinion_change = None
            if (
                previous is not None
                and point.round_num == previous.round_num + 1
                and point.stance_value is not None
                and previous.stance_value is not None
            ):
                point.opinion_change = round(
                    point.stance_value - previous.stance_value, 4
                )
            previous = point

    if received != expected:
        raise ValueError("Saved opinion text or snapshot coverage differs")

    return result, bool(previous_hash)

def run_analytics_pipeline(
    input_path, use_llm=False, output_path=None, *,
    use_embeddings=False, positive_pole=None, negative_pole=None,
    scores_from=None,
    generate_charts=False,
    generate_report=False,
    reports_dir="reports",
    counterfactual_ablation=False,
):
    protected = set()
    if isinstance(input_path, (str, Path)):
        path = Path(input_path)
        protected.add(path.resolve())
        raw_bytes = path.read_bytes()
        source_hash = hashlib.sha256(raw_bytes).hexdigest()
        raw_data = json.loads(raw_bytes)
        discussion = load_discussion(path)
        data = discussion.to_dict()
    elif hasattr(input_path, "to_dict"):
        discussion = input_path
        data = discussion.to_dict()
        raw_bytes = json.dumps(data, sort_keys=True).encode("utf-8")
        source_hash = hashlib.sha256(raw_bytes).hexdigest()
        raw_data = data
    elif isinstance(input_path, dict):
        from src.discussion.types import DiscussionResult
        raw_bytes = json.dumps(input_path, sort_keys=True).encode("utf-8")
        source_hash = hashlib.sha256(raw_bytes).hexdigest()
        raw_data = input_path
        discussion = DiscussionResult.from_dict(input_path)
        data = input_path
    else:
        raise TypeError(f"Expected DiscussionResult, dict, or path; got {type(input_path).__name__}")
    if scores_from and isinstance(scores_from, (str, Path)):
        protected.add(Path(scores_from).resolve())

    if output_path and Path(output_path).resolve() in protected:
        raise ValueError("Analytics output must not overwrite its inputs")

    if scores_from and (
        use_llm or use_embeddings or positive_pole or negative_pole
    ):
        raise ValueError("Saved scores retain their original scoring method and poles")

    warnings = validate_discussion(raw_data)

    if scores_from:
        trajectories, fingerprint_verified = load_saved_trajectories(
            scores_from, data, source_hash
        )
        if not fingerprint_verified:
            warnings.append(
                "Legacy scores have no source fingerprint. IDs, topic, rounds "
                "and stance text match; original reasoning provenance is unverified."
            )
    else:
        trajectories = compute_opinion_trajectories(
            data, use_llm=use_llm, use_embeddings=use_embeddings,
            positive_pole=positive_pole, negative_pole=negative_pole,
        )
        fingerprint_verified = True

    agreement = compute_discussion_agreement(data, trajectories=trajectories)
    distance = compute_agent_influence(data, trajectories=trajectories)
    trajectory_data = trajectories.model_dump()
    correlation = compute_correlation_influence(
        data, {"task1_opinion_trajectories": trajectory_data}
    )

    causal = None
    if use_llm or counterfactual_ablation:
        try:
            causal = compute_counterfactual_influence(
                data,
                trajectories=trajectories,
                positive_pole=positive_pole,
                negative_pole=negative_pole,
                correlation_results=correlation,
            )
        except Exception as err:
            warnings.append(f"Counterfactual ablation evaluation error: {err}")

    points = [
        point for series in trajectories.trajectories.values()
        for point in series
    ]
    output = {
        "schema_version": 2,
        "discussion_id": discussion.config.discussion_id,
        "topic": discussion.config.topic,
        "metadata": {
            "experimental": True,
            "input_status": discussion.config.metadata.get("status", "unknown"),
            "scoring_method": trajectories.metadata.get("method", "unknown"),
            "scores_reused": bool(scores_from),
            "source_sha256": source_hash,
            "score_source_fingerprint_verified": fingerprint_verified,
            "scored_snapshots": sum(p.stance_value is not None for p in points),
            "observed_snapshots": len(points),
            "expected_snapshots": (
                len(discussion.config.agent_ids)
                * (discussion.config.num_rounds + 1)
            ),
            "validation_warnings": warnings,
            "influence_method": correlation["method"],
            "limitations": [
                "Unclassified stances remain null.",
                "Agreement measures alignment, not factual correctness.",
                *correlation["limitations"],
            ],
        },
        "task1_opinion_trajectories": trajectory_data,
        "task2_discussion_agreement": agreement.model_dump(),
        "task3_agent_influence": correlation,
        "task4_sentiment": compute_discussion_sentiment(data),
        "distance_reduction_influence": distance.model_dump(),
    }
    if causal is not None:
        output["task3_causal_influence"] = causal.model_dump()

    # Do not establish verified scoring provenance for legacy cached scores.
    if scores_from and not fingerprint_verified:
        output["metadata"].pop("source_sha256")
        output["metadata"]["analyzed_source_sha256"] = source_hash

    # Optional visualization generation reusing the exact calculated or loaded trajectories
    if generate_charts:
        from src.visualization.opinion_trajectory import generate_opinion_trajectory_from_discussion
        from src.visualization.interaction_graph import generate_interaction_graph_from_discussion

        visualizations = {}
        has_plottable = any(
            p.stance_value is not None
            for series in trajectories.trajectories.values()
            for p in series
        )
        if has_plottable:
            chart_file = generate_opinion_trajectory_from_discussion(
                data,
                output_dir=reports_dir,
                trajectories=trajectories,
            )
            visualizations["opinion_trajectory"] = str(chart_file)
            print(f"Generated opinion trajectory chart: {chart_file}")
        else:
            warnings.append("No plottable stance values; opinion trajectory chart omitted")

        graph_file = generate_interaction_graph_from_discussion(
            data,
            output_dir=reports_dir,
        )
        visualizations["interaction_graph"] = str(graph_file)
        print(f"Generated interaction graph: {graph_file}")

        output["visualizations"] = visualizations
    if generate_report:
        from src.reporting.report import generate_markdown_report

        disc_id = output["discussion_id"]
        rep_file = Path(reports_dir) / f"discussion_report_{disc_id}.md"
        chart_rel = output.get("visualizations", {}).get("opinion_trajectory")
        graph_rel = output.get("visualizations", {}).get("interaction_graph")
        generate_markdown_report(
            output,
            discussion_data=data,
            output_path=rep_file,
            chart_image_path=chart_rel,
            graph_image_path=graph_rel,
        )
        output["report_path"] = str(rep_file.resolve())
        print(f"Generated Markdown report: {rep_file}")

    print(f"Discussion: {output['discussion_id']}")
    print(f"Saved scores reused: {bool(scores_from)}")
    print(
        f"Scored {output['metadata']['scored_snapshots']}/"
        f"{len(points)} observed snapshots"
    )
    print(f"Agreement trend: {agreement.overall_trend}")
    for agent, row in correlation["agent_influences"].items():
        print(f"{agent}: {row['influence_score']} ({row['status']})")
    if causal is not None and causal.top_causal_influencer:
        print(f"Top Causal Influencer (Ablation): {causal.top_causal_influencer} (evaluated {causal.evaluated_exchanges_count} exchanges)")

    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps(output, indent=2, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        print(f"Saved analytics: {out}")

    return output


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', '-i', '--discussion', dest='input', required=True, help="Path to input discussion JSON")
    parser.add_argument('--output', '-o')
    engines = parser.add_mutually_exclusive_group()
    engines.add_argument('--use-llm', action='store_true', help='Explicitly make additional requests using your configured LLM provider')
    engines.add_argument('--use-embeddings', action='store_true', help='Use a locally cached all-MiniLM-L6-v2 model; no download')
    engines.add_argument('--no-llm', action='store_true', help='Use conservative local self-report rules (the default)')
    engines.add_argument(
        "--scores-from",
        help="Reuse stance scores from saved analytics without model calls",
    )    
    parser.add_argument('--positive-pole', help='Explicit statement represented by +1')
    parser.add_argument('--negative-pole', help='Explicit statement represented by -1')
    parser.add_argument(
        "--generate-charts", "--visualize",
        action="store_true",
        dest="generate_charts",
        help="Generate both opinion trajectory and interaction graph charts.",
    )
    parser.add_argument(
        "--generate-report", "--report",
        action="store_true",
        dest="generate_report",
        help="Generate automated Markdown report summarizing all analytics.",
    )
    parser.add_argument(
        "--reports-dir",
        default="reports",
        help="Directory where charts and reports are saved (default: reports/).",
    )
    parser.add_argument(
        "--counterfactual-ablation",
        action="store_true",
        dest="counterfactual_ablation",
        help="Perform LLM-based counterfactual ablation to calculate true causal influence",
    )
    args = parser.parse_args(argv)
    if (args.use_llm or args.use_embeddings) and not (args.positive_pole and args.negative_pole):
        parser.error('Model scoring requires --positive-pole and --negative-pole')
    return args


def main(argv=None):
    args = parse_args(argv)
    if args.use_llm or args.counterfactual_ablation:
        from dotenv import load_dotenv
        load_dotenv(Path(__file__).resolve().parents[2] / '.env')
    run_analytics_pipeline(
        args.input, args.use_llm, args.output,
        use_embeddings=args.use_embeddings,
        positive_pole=args.positive_pole,
        negative_pole=args.negative_pole,
        scores_from=args.scores_from,
        generate_charts=args.generate_charts,
        generate_report=args.generate_report,
        reports_dir=args.reports_dir,
        counterfactual_ablation=args.counterfactual_ablation,
    )


if __name__ == '__main__':
    main()
