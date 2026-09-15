"""Analyze a saved discussion locally; extra model calls require --use-llm."""
import argparse
import json
from pathlib import Path

from src.analytics.agreement import compute_discussion_agreement
from src.analytics.influence import compute_agent_influence
from src.analytics.stance import compute_opinion_trajectories
from src.discussion.persistence import load_discussion


def run_analytics_pipeline(input_path, use_llm=False, output_path=None, *,
                           use_embeddings=False, positive_pole=None, negative_pole=None):
    path = Path(input_path)
    if output_path and Path(output_path).resolve() == path.resolve():
        raise ValueError('Analytics output must not overwrite its input discussion')
    discussion = load_discussion(path)
    data = discussion.to_dict()
    trajectories = compute_opinion_trajectories(
        data, use_llm=use_llm, use_embeddings=use_embeddings,
        positive_pole=positive_pole, negative_pole=negative_pole,
    )
    agreement = compute_discussion_agreement(data, trajectories=trajectories)
    influence = compute_agent_influence(data, trajectories=trajectories)
    scored = sum(p.stance_value is not None for pts in trajectories.trajectories.values() for p in pts)
    observed = sum(len(pts) for pts in trajectories.trajectories.values())
    output = {
        'metadata': {'experimental': True, 'input_status': discussion.config.metadata.get('status', 'unknown'),
                     'scored_snapshots': scored, 'observed_snapshots': observed,
                     'expected_snapshots': len(discussion.config.agent_ids) * (discussion.config.num_rounds + 1)},
        'task1_opinion_trajectories': trajectories.model_dump(),
        'task2_discussion_agreement': agreement.model_dump(),
        'task3_agent_influence': influence.model_dump(),
    }
    print(f'Discussion: {discussion.config.discussion_id}')
    print(f'Scoring method: {trajectories.metadata["method"]}; scored {scored}/{observed} observed snapshots')
    print(f'Agreement trend: {agreement.overall_trend}')
    print(f'Top associated convergence: {influence.top_influencer or "unavailable"}')
    print('Experimental analytics: review classifications and missing data before interpreting scores.')
    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(output, indent=2, allow_nan=False) + '\n', encoding='utf-8')
        print(f'Saved analytics: {out}')
    return output


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', '-i', required=True)
    parser.add_argument('--output', '-o')
    engines = parser.add_mutually_exclusive_group()
    engines.add_argument('--use-llm', action='store_true', help='Explicitly make additional requests using your configured LLM provider')
    engines.add_argument('--use-embeddings', action='store_true', help='Use a locally cached all-MiniLM-L6-v2 model; no download')
    engines.add_argument('--no-llm', action='store_true', help='Use conservative local self-report rules (the default)')
    parser.add_argument('--positive-pole', help='Explicit statement represented by +1')
    parser.add_argument('--negative-pole', help='Explicit statement represented by -1')
    args = parser.parse_args(argv)
    if (args.use_llm or args.use_embeddings) and not (args.positive_pole and args.negative_pole):
        parser.error('Model scoring requires --positive-pole and --negative-pole')
    return args


def main(argv=None):
    args = parse_args(argv)
    if args.use_llm:
        from dotenv import load_dotenv
        load_dotenv(Path(__file__).resolve().parents[2] / '.env')
    run_analytics_pipeline(args.input, args.use_llm, args.output,
                           use_embeddings=args.use_embeddings,
                           positive_pole=args.positive_pole, negative_pole=args.negative_pole)


if __name__ == '__main__':
    main()
