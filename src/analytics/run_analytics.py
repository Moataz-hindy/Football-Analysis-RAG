"""Command-line runner for Week 4 Analytics: Tasks 1, 2, and 3.

Usage:
------
    python -m src.analytics.run_analytics --input outputs/england-france.json
    python -m src.analytics.run_analytics --input outputs/england-france.json --use-llm
"""

import argparse
import json
import os
from pathlib import Path
import sys
from dotenv import load_dotenv

load_dotenv(Path(".").resolve() / ".env")

from src.analytics.agreement import compute_discussion_agreement
from src.analytics.influence import compute_agent_influence
from src.analytics.stance import compute_opinion_trajectories
from src.discussion.persistence import load_discussion


def run_analytics_pipeline(
    input_path: str | Path,
    use_llm: bool = False,
    output_path: str | Path | None = None,
) -> dict:
    path = Path(input_path)
    if not path.exists():
        raise FileNotFoundError(f"Discussion file not found: {path}")

    # Load discussion file
    with open(path, "r", encoding="utf-8") as f:
        discussion_data = json.load(f)

    topic = discussion_data.get("config", {}).get("topic", "N/A")
    agent_ids = discussion_data.get("config", {}).get("agent_ids", [])
    num_rounds = discussion_data.get("config", {}).get("num_rounds", 3)

    print("=" * 72)
    print(f"ANALYTICS PIPELINE: TASKS 1, 2 & 3")
    print("=" * 72)
    print(f"File:       {path}")
    print(f"Topic:      {topic}")
    print(f"Agents:     {', '.join(agent_ids)}")
    print(f"Engine:     {'LLM (Gemini/OpenAI)' if use_llm else 'Local Semantic Engine'}")
    print("-" * 72)

    # -------------------------------------------------------------
    # TASK 1: Opinion Trajectories & Numeric Stance
    # -------------------------------------------------------------
    print("\n>>> [TASK 1] COMPUTING OPINION TRAJECTORIES & NUMERIC STANCES...")
    traj_result = compute_opinion_trajectories(discussion_data, use_llm=use_llm)
    
    print("\nPer-Agent Stances Across Rounds (Scale: -1.0 to +1.0):")
    header = f"{'Agent ID':<24}" + "".join(f"Round {r:<8}" for r in range(num_rounds + 1))
    print(header)
    print("-" * len(header))
    
    for agent_id, points in sorted(traj_result.trajectories.items()):
        row = f"{agent_id:<24}"
        for pt in points:
            delta_str = f" ({pt.opinion_change:+.2f})" if pt.opinion_change is not None else ""
            row += f"{pt.stance_value:>5.2f}{delta_str:<5} "
        print(row)

    # -------------------------------------------------------------
    # TASK 2: Agreement & Polarization per Round
    # -------------------------------------------------------------
    print("\n>>> [TASK 2] COMPUTING PER-ROUND AGREEMENT & POLARIZATION...")
    agreement_result = compute_discussion_agreement(discussion_data, trajectories=traj_result)
    
    print(f"\nOverall Trend: {agreement_result.overall_trend.upper()}")
    for r in agreement_result.round_agreements:
        print(
            f"  Round {r.round_num}: Agreement = {r.agreement_score:.3f} | "
            f"Mean Dispersion = {r.mean_distance:.3f} | "
            f"Status: {r.interpretation}"
        )

    # -------------------------------------------------------------
    # TASK 3: Network Influence & Directional Convergence
    # -------------------------------------------------------------
    print("\n>>> [TASK 3] COMPUTING AGENT NETWORK INFLUENCE SCORES...")
    influence_result = compute_agent_influence(discussion_data, trajectories=traj_result)
    
    top_score_str = ""
    if influence_result.top_influencer:
        top_score = influence_result.get_influence_score(influence_result.top_influencer)
        if top_score is not None:
            top_score_str = f" (Score: {top_score:+.3f})"
    print(f"\nTop Influencer: {influence_result.top_influencer or 'None'}{top_score_str}")
    print(f"Dynamic:        {influence_result.discussion_dynamic}")
    print("\nRanked Agent Influence Table:")
    print(f"{'Rank':<6}{'Agent ID':<24}{'Score':<10}{'Total Pull':<14}{'Status':<14}")
    print("-" * 68)
    ranked = influence_result.get_ranked_influencers()
    for rank, (agent_id, score) in enumerate(ranked, start=1):
        inf = influence_result.agent_influences[agent_id]
        print(
            f"{rank:<6}{agent_id:<24}{score:>+6.3f}    "
            f"{inf.total_pull:>+10.3f}    {inf.status:<14}"
        )

    print("\n" + "=" * 72)
    print("ANALYTICS COMPLETE")
    print("=" * 72)

    output_data = {
        "task1_opinion_trajectories": traj_result.model_dump(),
        "task2_discussion_agreement": agreement_result.model_dump(),
        "task3_agent_influence": influence_result.model_dump(),
    }

    if output_path:
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        with open(out_p, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2)
        print(f"Saved analytics results to: {out_p}")

    return output_data


def main():
    parser = argparse.ArgumentParser(description="Run Week 4 Tasks 1, 2, and 3 on a discussion JSON.")
    parser.add_argument(
        "--input",
        "-i",
        required=True,
        help="Path to discussion JSON (e.g. outputs/england-france.json)",
    )
    has_key = bool(os.environ.get("LLM_API_KEY", "").strip())
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Disable LLM evaluation and use offline local semantic regex instead",
    )
    parser.add_argument(
        "--use-llm",
        action="store_true",
        default=has_key,
        help="Use LLM for zero-shot stance evaluation (enabled by default when LLM_API_KEY is present)",
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Optional path to save JSON analytics report",
    )
    args = parser.parse_args()

    use_llm = False if args.no_llm else args.use_llm

    run_analytics_pipeline(
        input_path=args.input,
        use_llm=use_llm,
        output_path=args.output,
    )


if __name__ == "__main__":
    main()
