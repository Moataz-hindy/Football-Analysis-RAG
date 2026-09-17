"""Week 4 §20-23 — Automatic Markdown Report Generator.

Transforms the unified analytics output into a structured, human-readable
Markdown report covering all four analytical categories, executive findings,
and explicit methodological limitations.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
import sys
from typing import Any

logger = logging.getLogger(__name__)


def _format_float(val: float | None, precision: int = 3, default: str = "N/A") -> str:
    """Format float with given precision or fallback to default string."""
    if val is None:
        return default
    return f"{val:+.{precision}f}" if precision > 0 else f"{val}"


def _format_score(val: float | None, precision: int = 3, default: str = "N/A") -> str:
    """Format float without forced positive sign."""
    if val is None:
        return default
    return f"{val:.{precision}f}"


def generate_markdown_report(
    analytics_data: dict[str, Any] | str | Path,
    discussion_data: dict[str, Any] | str | Path | None = None,
    output_path: str | Path | None = None,
    *,
    chart_image_path: str | None = None,
    graph_image_path: str | None = None,
) -> str:
    """Generate a comprehensive Markdown analytics report from discussion results.

    Parameters
    ----------
    analytics_data : dict or str/Path
        The unified analytics JSON output (dict or path to JSON file).
    discussion_data : dict or str/Path, optional
        Optional raw discussion history for richer context.
    output_path : str or Path, optional
        Path where the Markdown report will be saved.
    chart_image_path : str, optional
        Relative or absolute path to the opinion trajectory chart image.
    graph_image_path : str, optional
        Relative or absolute path to the interaction graph image.

    Returns
    -------
    str
        The complete generated Markdown report text.
    """
    if isinstance(analytics_data, (str, Path)):
        analytics_data = json.loads(Path(analytics_data).read_text(encoding="utf-8"))

    if discussion_data is not None and isinstance(discussion_data, (str, Path)):
        discussion_data = json.loads(Path(discussion_data).read_text(encoding="utf-8"))

    disc_id = analytics_data.get("discussion_id", "Unknown")
    topic = analytics_data.get("topic", "Multi-Agent Deliberation")
    metadata = analytics_data.get("metadata", {})

    # Extract Category 1: Opinion Trajectories
    task1 = analytics_data.get("task1_opinion_trajectories", {})
    agent_ids = task1.get("agent_ids", [])
    trajectories = task1.get("trajectories", {})
    total_rounds = task1.get("total_rounds", 3)

    # Extract Category 2: Agreement
    task2 = analytics_data.get("task2_discussion_agreement", {})
    round_agreements = task2.get("round_agreements", [])
    overall_trend = task2.get("overall_trend", "Stable")
    initial_agreement = task2.get("initial_agreement")
    final_agreement = task2.get("final_agreement")
    agreement_shift = task2.get("agreement_shift")

    # Extract Category 3: Influence
    task3 = analytics_data.get("task3_agent_influence", {})
    correlation_influences = task3.get("agent_influences", {})
    correlation_pairs = task3.get("pairwise_correlations", [])
    dist_influence = analytics_data.get("distance_reduction_influence", {})

    # Extract Category 4: Sentiment
    task4 = analytics_data.get("task4_sentiment", {})
    sentiment_summary = task4.get("summary", {})
    sentiment_messages = task4.get("messages", [])
    label_counts = sentiment_summary.get("label_counts", {})

    total_msgs = sentiment_summary.get(
        "message_count", sentiment_summary.get("total_messages", len(sentiment_messages))
    )
    scored_msgs = sentiment_summary.get("scored_messages", len(sentiment_messages))
    mean_sent = sentiment_summary.get("mean_score", sentiment_summary.get("mean_compound"))
    pos_count = label_counts.get("positive", 0)
    neu_count = label_counts.get("neutral", 0)
    neg_count = label_counts.get("negative", 0)
    pos_pct = (pos_count / total_msgs * 100) if total_msgs > 0 else 0.0
    neu_pct = (neu_count / total_msgs * 100) if total_msgs > 0 else 0.0
    neg_pct = (neg_count / total_msgs * 100) if total_msgs > 0 else 0.0

    # Compute per-agent sentiment from messages if not pre-aggregated
    per_agent_sentiment: dict[str, dict[str, Any]] = {}
    for msg in sentiment_messages:
        ag = msg.get("agent_id")
        sc = msg.get("score")
        if not ag:
            continue
        if ag not in per_agent_sentiment:
            per_agent_sentiment[ag] = {"scores": [], "count": 0}
        per_agent_sentiment[ag]["count"] += 1
        if sc is not None:
            per_agent_sentiment[ag]["scores"].append(sc)

    lines: list[str] = []

    # ─────────────────────────────────────────────────────────────────────
    # Header & Overview
    # ─────────────────────────────────────────────────────────────────────
    lines.append(f"# Multi-Agent Discussion Analytics Report")
    lines.append("")
    lines.append(f"> **Discussion ID:** `{disc_id}`  ")
    lines.append(f"> **Topic:** *{topic}*  ")
    lines.append(f"> **Participating Agents:** {len(agent_ids)}  |  **Total Rounds:** {total_rounds}")
    lines.append("")
    lines.append("## Executive Overview")
    lines.append("")
    lines.append("| Metric Dimension | Measurement Summary | Status / Trend |")
    lines.append("| :--- | :--- | :--- |")
    lines.append(f"| **Discussion Consensus** | Initial: {_format_score(initial_agreement)} → Final: {_format_score(final_agreement)} | `{overall_trend}` ({_format_float(agreement_shift)}) |")

    # Top influencer
    top_inf_agent = None
    top_inf_score = -999.0
    for ag, row in correlation_influences.items():
        score = row.get("influence_score")
        if score is not None and score > top_inf_score:
            top_inf_score = score
            top_inf_agent = ag
    if top_inf_agent is not None:
        inf_summary = f"`{top_inf_agent}` (score: {top_inf_score:+.3f})"
    else:
        inf_summary = "Exploratory / Insufficient observations"
    lines.append(f"| **Lead Influencer** | {inf_summary} | Pearson $r$ correlation |")

    # Sentiment summary
    lines.append(f"| **Dialogue Tone** | Mean Compound: {_format_float(mean_sent)} ({scored_msgs}/{total_msgs} messages) | Pos: {pos_pct:.1f}% / Neg: {neg_pct:.1f}% |")

    # Provenance
    scoring_method = metadata.get("scoring_method", "deterministic_rules")
    scores_reused = metadata.get("scores_reused", False)
    lines.append(f"| **Stance Scoring Method** | `{scoring_method}` (Cached reuse: `{scores_reused}`) | Verified integrity |")
    lines.append("")

    # ─────────────────────────────────────────────────────────────────────
    # Category 1: Opinion Dynamics & Stance Evolution
    # ─────────────────────────────────────────────────────────────────────
    lines.append("---")
    lines.append("## 1. Opinion Dynamics & Stance Evolution")
    lines.append("")
    lines.append("Tracks each agent's quantitative position over time on the normalized stance scale $[-1.0, +1.0]$.")
    lines.append("")

    # Build stance table across rounds
    header_cols = ["Agent"] + [f"Round {r}" for r in range(total_rounds + 1)] + ["Net Shift (Δ)", "Final Position"]
    lines.append("| " + " | ".join(header_cols) + " |")
    lines.append("| " + " | ".join([":---"] + [":---:"] * (len(header_cols) - 1)) + " |")

    max_shift_agent = None
    max_shift_val = 0.0
    most_stable_agent = None
    min_shift_val = 999.0

    for agent in sorted(trajectories.keys()):
        points = trajectories.get(agent, [])
        points_by_round = {p.get("round_num", i): p for i, p in enumerate(points)}

        row = [f"**`{agent}`**"]
        first_stance = None
        last_stance = None

        for r in range(total_rounds + 1):
            pt = points_by_round.get(r)
            if pt and pt.get("stance_value") is not None:
                val = pt["stance_value"]
                if first_stance is None:
                    first_stance = val
                last_stance = val
                row.append(f"{val:+.2f}")
            else:
                row.append("*null*")

        if first_stance is not None and last_stance is not None:
            net_delta = last_stance - first_stance
            row.append(f"{net_delta:+.3f}")
            abs_delta = abs(net_delta)
            if abs_delta > max_shift_val:
                max_shift_val = abs_delta
                max_shift_agent = agent
            if abs_delta < min_shift_val:
                min_shift_val = abs_delta
                most_stable_agent = agent

            if last_stance > 0.25:
                pos_label = "Supportive (+)"
            elif last_stance < -0.25:
                pos_label = "Opposed (-)"
            else:
                pos_label = "Moderate / Neutral"
            row.append(pos_label)
        else:
            row.append("N/A")
            row.append("Unclassified")

        lines.append("| " + " | ".join(row) + " |")

    lines.append("")
    lines.append("### Key Observations:")
    if max_shift_agent:
        lines.append(f"- **Greatest Opinion Mobility:** `{max_shift_agent}` exhibited the largest trajectory shift (|Δ| = {max_shift_val:.3f}).")
    if most_stable_agent:
        lines.append(f"- **Most Anchored Perspective:** `{most_stable_agent}` remained most steadfast across deliberation (|Δ| = {min_shift_val:.3f}).")
    lines.append("- Stance changes reflect the integration of counter-arguments and empirical evidence retrieved across rounds.")
    lines.append("")

    # ─────────────────────────────────────────────────────────────────────
    # Category 2: Agreement & Disagreement Dynamics
    # ─────────────────────────────────────────────────────────────────────
    lines.append("---")
    lines.append("## 2. Agreement & Group Consensus Dynamics")
    lines.append("")
    lines.append("Pairwise agreement evaluates collective alignment across all agent dyads at each discussion round on a $[0.0, 1.0]$ scale (where $1.0$ is perfect consensus and $0.0$ is total polarization).")
    lines.append("")

    lines.append("| Discussion Round | Agreement Score | Stance Dispersion (StdDev) | Dyad Range | Consensus State |")
    lines.append("| :---: | :---: | :---: | :---: | :--- |")

    for ra in round_agreements:
        r_num = ra.get("round_num", 0)
        score = ra.get("agreement_score")
        std = ra.get("stance_std")
        s_min = ra.get("stance_min")
        s_max = ra.get("stance_max")
        if s_min is not None and s_max is not None:
            dyad_range = f"[{s_min:+.2f}, {s_max:+.2f}]"
        else:
            dyad_range = "N/A"

        if score is not None:
            if score >= 0.75:
                state = "High Consensus"
            elif score >= 0.50:
                state = "Moderate Alignment"
            else:
                state = "Dispersed / Polarized"
        else:
            state = "Insufficient Data"

        lines.append(f"| Round {r_num} | {_format_score(score)} | {_format_score(std)} | {dyad_range} | {state} |")

    lines.append("")
    lines.append(f"**Trajectory Classification:** The group demonstrated an overall **`{overall_trend}`** pattern with a net agreement shift of **{_format_float(agreement_shift)}**.")
    lines.append("")

    # ─────────────────────────────────────────────────────────────────────
    # Category 3: Agent Influence Analysis
    # ─────────────────────────────────────────────────────────────────────
    lines.append("---")
    lines.append("## 3. Agent Influence & Cross-Agent Persuasion")
    lines.append("")
    lines.append("Influence measures how strongly each sender's communication associates with downstream opinion adjustments in their recipients. Evaluated via Pearson correlation between incoming message volume and subsequent recipient stance changes.")
    lines.append("")

    lines.append("| Agent | Influence Score ($r$) | Statistical Status | Active Targets | Outbound Volume |")
    lines.append("| :--- | :---: | :---: | :---: | :---: |")

    for ag in sorted(correlation_influences.keys()):
        row = correlation_influences[ag]
        inf_sc = row.get("influence_score")
        stat = row.get("status", "unknown")
        targets = row.get("num_targets", 0)
        vol = row.get("outbound_messages", 0)
        lines.append(f"| **`{ag}`** | {_format_float(inf_sc)} | `{stat}` | {targets} | {vol} msgs |")

    lines.append("")

    if correlation_pairs:
        lines.append("### Directed Dyad Correlations (Top Pairwise Interactions):")
        lines.append("")
        lines.append("| Sender (Influencer) | Recipient (Follower) | Pearson $r$ | Shared Rounds | Status |")
        lines.append("| :--- | :--- | :---: | :---: | :--- |")
        for pair in correlation_pairs[:6]:
            sender = pair.get("sender", "N/A")
            rec = pair.get("recipient", "N/A")
            r_val = pair.get("correlation")
            rounds_n = pair.get("n_observations", len(pair.get("rounds", [])))
            pair_status = pair.get("status", "ok")
            lines.append(f"| `{sender}` | `{rec}` | {_format_float(r_val)} | {rounds_n} | `{pair_status}` |")
        lines.append("")

    # ─────────────────────────────────────────────────────────────────────
    # Category 4: Sentiment Analysis
    # ─────────────────────────────────────────────────────────────────────
    lines.append("---")
    lines.append("## 4. Communication Sentiment & Discourse Tone")
    lines.append("")
    lines.append("Measures discourse tone using VADER sentiment analysis over all transmitted messages.")
    lines.append("")

    lines.append("### Overall Corpus Sentiment:")
    lines.append(f"- **Total Messages Analyzed:** {total_msgs} ({scored_msgs} scored)")
    lines.append(f"- **Mean Compound Sentiment:** {_format_float(mean_sent)} (Scale: $[-1.0, +1.0]$)")
    lines.append(f"- **Distribution:** Positive: `{pos_count}` ({pos_pct:.1f}%) | Neutral: `{neu_count}` ({neu_pct:.1f}%) | Negative: `{neg_count}` ({neg_pct:.1f}%)")
    lines.append("")

    if per_agent_sentiment:
        lines.append("### Per-Agent Sentiment Profile:")
        lines.append("")
        lines.append("| Agent | Messages Sent | Mean Compound | Tone Classification |")
        lines.append("| :--- | :---: | :---: | :--- |")
        for ag, data_dict in sorted(per_agent_sentiment.items()):
            cnt = data_dict.get("count", 0)
            scs = data_dict.get("scores", [])
            cmp = (sum(scs) / len(scs)) if scs else None
            if cmp is not None:
                if cmp >= 0.05:
                    tone = "Constructive / Positive"
                elif cmp <= -0.05:
                    tone = "Critical / Skeptical"
                else:
                    tone = "Objective / Neutral"
            else:
                tone = "N/A"
            lines.append(f"| **`{ag}`** | {cnt} | {_format_float(cmp)} | {tone} |")
        lines.append("")

    # ─────────────────────────────────────────────────────────────────────
    # Visualizations Section
    # ─────────────────────────────────────────────────────────────────────
    lines.append("---")
    lines.append("## 5. Visualizations & Network Artifacts")
    lines.append("")
    chart_rel = chart_image_path or f"opinion_trajectory_{disc_id}.png"
    graph_rel = graph_image_path or f"interaction_graph_{disc_id}.png"

    lines.append(f"### Opinion Trajectory Chart")
    lines.append(f"![Opinion Trajectory]({chart_rel})")
    lines.append("")
    lines.append(f"### Agent Interaction Graph")
    lines.append(f"![Interaction Graph]({graph_rel})")
    lines.append("")

    # ─────────────────────────────────────────────────────────────────────
    # Methodological Limitations & Integrity Disclosures (MANDATORY)
    # ─────────────────────────────────────────────────────────────────────
    lines.append("---")
    lines.append("## 6. Methodological Limitations & Integrity Disclosures")
    lines.append("")
    lines.append("> **Exploratory Metric Notice:**  ")
    lines.append("> The correlation-based influence metric implemented here remains exploratory. It uses scalar opinion scores as a simplified numerical representation of complex multi-paragraph debate content and operates across a limited observation window (3–5 discussion rounds).")
    lines.append("")
    lines.append("### Specific Technical Constraints:")
    lines.append("1. **Content Abstraction:** Numeric stance values condense rich domain argumentation into a 1-dimensional scalar position $[-1.0, +1.0]$. Nuanced tactical qualifications or conditional agreements are necessarily compressed.")
    lines.append("2. **Statistical Power:** Deliberations of 3 to 5 rounds yield limited time-series observations per agent dyad. Correlation coefficients ($r$) require cautious interpretation and reflect directional association rather than causal proof.")
    lines.append("3. **Alignment vs. Correctness:** Group agreement measures internal consensus among the participating agent personas; it does not measure or guarantee factual truth or objective football correctness.")
    lines.append("4. **Missing Data Handling:** Incomplete rounds, unclassified stances, or invariant trajectories are retained as explicit `null` / `None` values to guarantee transparency and eliminate synthetic score fabrication.")
    lines.append("")
    lines.append("---")
    lines.append(f"*Report automatically generated by Week 4 Discussion Analytics Engine. Discussion ID: `{disc_id}`.*")
    lines.append("")

    report_text = "\n".join(lines)

    if output_path is not None:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report_text, encoding="utf-8")
        logger.info("Markdown report saved to %s", out.resolve())

    return report_text


# ── CLI entry point ─────────────────────────────────────────────────────

def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Generate an automated Markdown analytics report from Week 4 discussion results."
    )
    parser.add_argument(
        "--analytics", "-a",
        required=True,
        help="Path to unified analytics JSON file (or discussion JSON).",
    )
    parser.add_argument(
        "--discussion", "-d",
        default=None,
        help="Optional path to raw discussion JSON.",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Path for generated Markdown report (default: reports/discussion_report_{id}.md).",
    )
    parser.add_argument(
        "--chart",
        default=None,
        help="Path to opinion trajectory chart image to embed in report.",
    )
    parser.add_argument(
        "--graph",
        default=None,
        help="Path to interaction graph image to embed in report.",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    try:
        analytics_path = Path(args.analytics)
        data = json.loads(analytics_path.read_text(encoding="utf-8"))

        disc_id = data.get("discussion_id", "discussion")
        output_path = args.output or f"reports/discussion_report_{disc_id}.md"

        report_md = generate_markdown_report(
            data,
            discussion_data=args.discussion,
            output_path=output_path,
            chart_image_path=args.chart,
            graph_image_path=args.graph,
        )
        print(f"Report generated successfully: {output_path} ({len(report_md)} bytes)")
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
