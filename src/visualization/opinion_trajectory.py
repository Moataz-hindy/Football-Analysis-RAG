"""Week 4 §24 — Opinion Trajectory Visualization.

Generates a multi-line chart showing each agent's numeric stance across
discussion rounds.  The chart is saved as a PNG image that Week 5 can
consume directly.

Supports two input modes:
  1. Pre-computed stance data (dict[str, list[dict]]) — used when the
     analytics module has already produced numeric stances.
  2. A raw DiscussionResult scored by the shared analytics rules.
     Unclassified opinions remain missing; sentiment is not stance.
"""

from __future__ import annotations

import logging
import math
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend — no GUI window needed.
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

logger = logging.getLogger(__name__)

# ── Colour palette & style ──────────────────────────────────────────────

_AGENT_COLOURS = [
    "#E63946",  # red
    "#457B9D",  # steel blue
    "#2A9D8F",  # teal
    "#E9C46A",  # gold
    "#F4A261",  # sandy orange
    "#264653",  # dark teal
    "#8338EC",  # purple
    "#3A86FF",  # bright blue
    "#FF006E",  # hot pink
    "#06D6A0",  # mint
]

_MARKERS = ["o", "s", "D", "^", "v", "P", "X", "h", "*", "d"]


def _extract_stance_data_from_trajectories(
    trajectories_obj: Any,
) -> dict[str, list[dict[str, Any]]]:
    """Convert OpinionTrajectoryResult or serialized trajectories dict into stance_data format."""
    if hasattr(trajectories_obj, "trajectories"):
        # OpinionTrajectoryResult object
        return {
            agent: [
                {
                    "round": p.round_num,
                    "stance": p.stance_value,
                    "change": p.opinion_change,
                }
                for p in points
            ]
            for agent, points in trajectories_obj.trajectories.items()
        }
    elif isinstance(trajectories_obj, dict):
        raw = trajectories_obj.get("task1_opinion_trajectories", trajectories_obj)
        raw_trajectories = raw.get("trajectories", raw)
        stance_data = {}
        for agent, points in raw_trajectories.items():
            agent_points = []
            for p in points:
                if isinstance(p, dict):
                    r = p.get("round_num", p.get("round", 0))
                    s = p.get("stance_value", p.get("stance"))
                    c = p.get("opinion_change", p.get("change"))
                    agent_points.append({"round": r, "stance": s, "change": c})
                else:
                    agent_points.append({
                        "round": getattr(p, "round_num", getattr(p, "round", 0)),
                        "stance": getattr(p, "stance_value", getattr(p, "stance", None)),
                        "change": getattr(p, "opinion_change", getattr(p, "change", None)),
                    })
            stance_data[agent] = agent_points
        return stance_data
    raise ValueError(f"Unrecognized trajectory format: {type(trajectories_obj)}")


def _extract_stance_data_from_discussion(
    discussion_data: dict[str, Any],
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    """Use the shared analytics rules; preserve unknown stances and errors."""
    # If the input dictionary is already an analytics result, reuse task1
    if "task1_opinion_trajectories" in discussion_data:
        traj_data = discussion_data["task1_opinion_trajectories"]
        config = {
            "discussion_id": discussion_data.get("discussion_id", traj_data.get("discussion_id", "")),
            "topic": discussion_data.get("topic", traj_data.get("topic", "")),
            "num_rounds": traj_data.get("total_rounds", 3),
            "agent_ids": traj_data.get("agent_ids", list(traj_data.get("trajectories", {}).keys())),
        }
        return _extract_stance_data_from_trajectories(traj_data), config

    from src.analytics.stance import compute_opinion_trajectories

    trajectory = compute_opinion_trajectories(discussion_data)
    return {
        agent: [{"round": p.round_num, "stance": p.stance_value,
                 "change": p.opinion_change} for p in points]
        for agent, points in trajectory.trajectories.items()
    }, discussion_data.get("config", {})

# ── Core plotting function ──────────────────────────────────────────────

def plot_opinion_trajectory(
    stance_data: dict[str, list[dict[str, Any]]],
    config: dict[str, Any] | None = None,
    output_path: str | Path = "reports/opinion_trajectory.png",
    *,
    title: str | None = None,
    figsize: tuple[float, float] = (12, 7),
    dpi: int = 150,
) -> str:
    """Plot each agent's stance trajectory across discussion rounds.

    Parameters
    ----------
    stance_data : dict[str, list[dict]]
        Mapping from agent_id to a chronological list of dicts, each
        containing at minimum ``{"round": int, "stance": float | None}``.
        An optional ``"change"`` key is used for annotation.
    config : dict, optional
        Discussion config with ``topic``, ``discussion_id``, ``num_rounds``.
    output_path : str or Path
        Where to save the chart.  Parent directories are created
        automatically.
    title : str, optional
        Override the auto-generated chart title.
    figsize : tuple[float, float]
        Figure dimensions in inches (width, height).
    dpi : int
        Resolution of the saved image.

    Returns
    -------
    str
        Absolute path to the saved PNG file.

    Raises
    ------
    ValueError
        If stance_data is empty or contains no plottable values.
    """
    if not stance_data:
        raise ValueError("stance_data is empty — nothing to plot")

    config = config or {}
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # ── Collect plottable series ────────────────────────────────────────
    plottable: dict[str, tuple[list[int], list[float]]] = {}
    for agent_id, points in stance_data.items():
        rounds = []
        values = []
        for p in points:
            v = p.get("stance")
            rounds.append(int(p["round"]))
            values.append(float(v) if v is not None and math.isfinite(v) else math.nan)
        if any(math.isfinite(v) for v in values):
            plottable[agent_id] = (rounds, values)

    if not plottable:
        raise ValueError("No plottable stance values found in stance_data")

    # ── Determine axis range ────────────────────────────────────────────
    all_rounds = sorted({r for rs, _ in plottable.values() for r in rs})
    all_values = [v for _, vs in plottable.values() for v in vs if math.isfinite(v)]
    y_min = min(all_values)
    y_max = max(all_values)
    y_pad = max(0.1, (y_max - y_min) * 0.12)

    # ── Build chart title ───────────────────────────────────────────────
    if title is None:
        topic = config.get("topic", "")
        if len(topic) > 70:
            topic = topic[:67] + "..."
        disc_id = config.get("discussion_id", "")
        if topic:
            title = f"Opinion Trajectory — {topic}"
        elif disc_id:
            title = f"Opinion Trajectory — {disc_id}"
        else:
            title = "Agent Opinion Trajectory"

    # ── Plot ────────────────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=figsize)

    # Background styling
    fig.patch.set_facecolor("#FAFAFA")
    ax.set_facecolor("#FFFFFF")
    ax.grid(True, linestyle="--", linewidth=0.6, alpha=0.5, color="#CCCCCC")
    ax.set_axisbelow(True)

    sorted_agents = sorted(plottable.keys())
    for idx, agent_id in enumerate(sorted_agents):
        rounds, values = plottable[agent_id]
        colour = _AGENT_COLOURS[idx % len(_AGENT_COLOURS)]
        marker = _MARKERS[idx % len(_MARKERS)]

        # Shorten label for legend if too long
        label = agent_id if len(agent_id) <= 25 else agent_id[:22] + "..."

        ax.plot(
            rounds,
            values,
            color=colour,
            marker=marker,
            markersize=9,
            markeredgecolor="white",
            markeredgewidth=1.5,
            linewidth=2.5,
            label=label,
            zorder=3,
        )

        # Annotate the final value
        if values and math.isfinite(values[-1]):
            ax.annotate(
                f"  {values[-1]:+.2f}",
                xy=(rounds[-1], values[-1]),
                fontsize=8,
                fontweight="bold",
                color=colour,
                va="center",
            )

    # ── Find & mark the largest single-round change ─────────────────────
    max_change_abs = 0.0
    max_change_info: tuple[str, int, float, float] | None = None
    for agent_id, points in stance_data.items():
        for p in points:
            change = p.get("change")
            if change is not None and abs(change) > max_change_abs:
                r = int(p["round"])
                v = p.get("stance")
                if v is not None and math.isfinite(v):
                    max_change_abs = abs(change)
                    max_change_info = (agent_id, r, v, change)

    if max_change_info and max_change_abs > 0.05:
        agent_id, r, v, change = max_change_info
        direction = "▲" if change > 0 else "▼"
        ax.annotate(
            f" {direction} {change:+.2f}",
            xy=(r, v),
            xytext=(r + 0.15, v + (y_pad * 0.4 if change > 0 else -y_pad * 0.4)),
            fontsize=7,
            color="#888888",
            fontstyle="italic",
            arrowprops=dict(arrowstyle="->", color="#BBBBBB", lw=0.8),
        )

    # ── Axis labels & formatting ────────────────────────────────────────
    ax.set_xlabel("Discussion Round", fontsize=12, fontweight="bold", labelpad=10)
    ax.set_ylabel("Stance Score", fontsize=12, fontweight="bold", labelpad=10)
    ax.set_title(title, fontsize=14, fontweight="bold", pad=15)

    ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    ax.set_xlim(min(all_rounds) - 0.3, max(all_rounds) + 0.6)
    ax.set_ylim(y_min - y_pad, y_max + y_pad)

    # Zero reference line
    if y_min < 0 < y_max:
        ax.axhline(y=0, color="#AAAAAA", linewidth=0.8, linestyle="-", zorder=1)

    # Legend
    legend = ax.legend(
        loc="upper left",
        bbox_to_anchor=(1.02, 1.0),
        fontsize=9,
        frameon=True,
        fancybox=True,
        shadow=False,
        edgecolor="#DDDDDD",
        title="Agents",
        title_fontsize=10,
    )
    legend.get_frame().set_alpha(0.95)

    # Spine styling
    for spine in ax.spines.values():
        spine.set_color("#DDDDDD")
        spine.set_linewidth(0.8)

    ax.tick_params(axis="both", which="major", labelsize=10, colors="#555555")

    # ── Add discussion metadata as subtle footer ────────────────────────
    disc_id = config.get("discussion_id", "")
    n_agents = len(plottable)
    n_rounds = len(all_rounds)
    footer = f"Agents: {n_agents} | Rounds: {n_rounds}"
    if disc_id:
        footer = f"ID: {disc_id} | {footer}"
    fig.text(
        0.02, 0.01, footer,
        fontsize=7, color="#AAAAAA", fontstyle="italic",
    )

    # ── Save ────────────────────────────────────────────────────────────
    output_p = Path(output_path).resolve()
    output_p.parent.mkdir(parents=True, exist_ok=True)
    saved = False
    for attempt in range(3):
        try:
            with open(output_p, "wb") as f:
                fig.savefig(
                    f,
                    format="png",
                    dpi=dpi,
                    bbox_inches="tight",
                    facecolor=fig.get_facecolor(),
                )
            saved = True
            break
        except (OSError, PermissionError):
            import time
            time.sleep(0.3)

    if not saved:
        fig.savefig(
            str(output_p),
            format="png",
            dpi=dpi,
            bbox_inches="tight",
            facecolor=fig.get_facecolor(),
        )
    plt.close(fig)

    abs_path = str(output_p)
    logger.info("Opinion trajectory chart saved to %s", abs_path)
    return abs_path


# ── Convenience wrapper ─────────────────────────────────────────────────

def generate_opinion_trajectory_from_discussion(
    discussion_input: Any,
    output_dir: str | Path = "reports",
    *,
    filename: str | None = None,
    scores_from: Any | None = None,
    trajectories: Any | None = None,
) -> str:
    """Generate an opinion trajectory chart from a DiscussionResult, dict, or saved scores.

    This is the main entry point that the unified analytics engine and
    the report generator should call.

    Parameters
    ----------
    discussion_input : DiscussionResult, dict, or str/Path
        Either a DiscussionResult object, its dict representation, or a
        path to a saved discussion JSON file / analytics JSON file.
    output_dir : str or Path
        Directory where the chart will be saved.
    filename : str, optional
        Override the chart filename. Defaults to
        ``opinion_trajectory_{discussion_id}.png``.
    scores_from : str, Path, or dict, optional
        Saved analytics JSON or dict containing task1_opinion_trajectories
        to reuse without repeating scoring or model calls.
    trajectories : OpinionTrajectoryResult or dict, optional
        Directly provide precomputed trajectories object.

    Returns
    -------
    str
        Absolute path to the saved PNG file.
    """
    import json

    # ── Resolve input to a dict ─────────────────────────────────────────
    data: dict[str, Any] = {}
    if isinstance(discussion_input, (str, Path)):
        path_obj = Path(discussion_input)
        raw_content = json.loads(path_obj.read_text(encoding="utf-8"))
        if "config" in raw_content or "messages" in raw_content:
            from src.discussion.persistence import load_discussion
            discussion_obj = load_discussion(path_obj)
            data = discussion_obj.to_dict()
        else:
            data = raw_content
    elif hasattr(discussion_input, "to_dict"):
        data = discussion_input.to_dict()
    elif isinstance(discussion_input, dict):
        data = discussion_input
    else:
        raise TypeError(
            f"Expected DiscussionResult, dict, or file path; got {type(discussion_input).__name__}"
        )

    config = data.get("config", {})
    if not config:
        config = {
            "discussion_id": data.get("discussion_id", "discussion"),
            "topic": data.get("topic", ""),
            "num_rounds": data.get("total_rounds", 3),
        }

    # ── Extract stance data ─────────────────────────────────────────────
    if trajectories is not None:
        stance_data = _extract_stance_data_from_trajectories(trajectories)
    elif scores_from is not None:
        if isinstance(scores_from, (str, Path)):
            loaded_scores = json.loads(Path(scores_from).read_text(encoding="utf-8"))
        else:
            loaded_scores = scores_from
        stance_data = _extract_stance_data_from_trajectories(loaded_scores)
    elif "task1_opinion_trajectories" in data:
        stance_data = _extract_stance_data_from_trajectories(data["task1_opinion_trajectories"])
    else:
        stance_data, cfg = _extract_stance_data_from_discussion(data)
        if not config.get("topic"):
            config = cfg

    # ── Determine output path ───────────────────────────────────────────
    disc_id = config.get("discussion_id", "discussion")
    if filename is None:
        filename = f"opinion_trajectory_{disc_id}.png"
    output_path = Path(output_dir).resolve() / filename

    return plot_opinion_trajectory(stance_data, config, output_path)

# ── CLI entry point ─────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Generate an opinion trajectory chart from a Week 3 discussion."
    )
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Path to a saved discussion JSON file.",
    )
    parser.add_argument(
        "--output-dir", "-o",
        default="reports",
        help="Directory for the output chart (default: reports/).",
    )
    parser.add_argument(
        "--filename", "-f",
        default=None,
        help="Override the chart filename.",
    )
    parser.add_argument(
        "--scores-from",
        default=None,
        help="Path to saved analytics JSON with cached stance scores.",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    try:
        path = generate_opinion_trajectory_from_discussion(
            args.input,
            output_dir=args.output_dir,
            filename=args.filename,
            scores_from=args.scores_from,
        )
        print(f"Chart saved: {path}")
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
