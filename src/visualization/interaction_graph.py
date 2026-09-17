"""Week 4 §25 — Weighted Interaction Graph Visualization.

Generates a directed, weighted graph visualization of the agent interaction
network from a Week 3 discussion.

Visual components:
  * Agents as nodes (with consistent persona color coding matching opinion trajectory)
  * Directed communication relationships as edges (sender -> recipient)
  * Edge weights reflecting message volume (count of messages exchanged)
  * Curved bidirectional arrows to distinguish reciprocal communication paths
  * Edge labels indicating exact message counts
"""

from __future__ import annotations

import argparse
import logging
import math
from pathlib import Path
import sys
from typing import Any

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import networkx as nx

logger = logging.getLogger(__name__)

# Color palette aligned with src.visualization.opinion_trajectory
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


def _format_agent_label(agent_id: str) -> str:
    """Format agent identifier into a multi-line title-case label."""
    words = agent_id.replace("-", "_").split("_")
    if len(words) <= 1:
        return agent_id.title()
    if len(words) == 2:
        return f"{words[0].title()}\n{words[1].title()}"
    return f"{words[0].title()} {words[1].title()}\n" + " ".join(w.title() for w in words[2:])


def extract_interaction_data(
    discussion_input: Any,
) -> tuple[nx.DiGraph, dict[str, Any]]:
    """Extract directed communication graph with message-count weights.

    Parameters
    ----------
    discussion_input : DiscussionResult, dict, or str/Path
        Either a DiscussionResult object, its dict representation, or a
        path to a saved discussion JSON file.

    Returns
    -------
    tuple[nx.DiGraph, dict[str, Any]]
        The populated NetworkX DiGraph and the discussion configuration dict.

    Raises
    ------
    ValueError
        If no agents are found in the discussion data.
    """
    if isinstance(discussion_input, (str, Path)):
        from src.discussion.persistence import load_discussion
        discussion_input = load_discussion(discussion_input)

    if hasattr(discussion_input, "to_dict"):
        data = discussion_input.to_dict()
    elif isinstance(discussion_input, dict):
        data = discussion_input
    else:
        raise TypeError(
            f"Expected DiscussionResult, dict, or file path; got {type(discussion_input).__name__}"
        )

    config = data.get("config", {})
    agent_ids = list(config.get("agent_ids", []))
    messages = data.get("messages", [])

    # If agent_ids not in config, infer from messages and opinions
    if not agent_ids:
        found_agents = set()
        for m in messages:
            sender = m.get("sender_id") or m.get("sender")
            if sender:
                found_agents.add(str(sender))
            for r in m.get("recipient_ids", []) or m.get("recipients", []):
                found_agents.add(str(r))
        for op in data.get("opinions", []):
            agent = op.get("agent_id")
            if agent:
                found_agents.add(str(agent))
        agent_ids = sorted(found_agents)

    if not agent_ids:
        raise ValueError("No agents found in discussion data — cannot build interaction graph")

    graph = nx.DiGraph()
    # Add all participating agents as nodes so even isolated agents appear
    for agent_id in agent_ids:
        graph.add_node(agent_id, sent=0, received=0)

    # Accumulate message-count weights along directed edges
    for m in messages:
        sender = m.get("sender_id") or m.get("sender")
        recipients = m.get("recipient_ids") or m.get("recipients", [])
        if not sender or not recipients:
            continue

        sender = str(sender)
        if sender not in graph:
            graph.add_node(sender, sent=0, received=0)

        for rec in recipients:
            rec = str(rec)
            if rec not in graph:
                graph.add_node(rec, sent=0, received=0)

            if graph.has_edge(sender, rec):
                graph[sender][rec]["weight"] += 1
            else:
                graph.add_edge(sender, rec, weight=1)

    # Record total sent and received per agent
    for node in graph.nodes():
        graph.nodes[node]["sent"] = sum(
            graph[node][succ]["weight"] for succ in graph.successors(node)
        )
        graph.nodes[node]["received"] = sum(
            graph[pred][node]["weight"] for pred in graph.predecessors(node)
        )

    return graph, config


def plot_interaction_graph(
    graph: nx.DiGraph,
    config: dict[str, Any] | None = None,
    output_path: str | Path = "reports/interaction_graph.png",
    *,
    title: str | None = None,
    figsize: tuple[float, float] = (12, 10),
    dpi: int = 150,
) -> str:
    """Plot the weighted interaction graph and save as PNG.

    Parameters
    ----------
    graph : nx.DiGraph
        Directed graph containing agent nodes and weighted edges.
    config : dict, optional
        Discussion configuration with metadata (topic, discussion_id).
    output_path : str or Path
        Destination filepath for the saved PNG.
    title : str, optional
        Optional custom title.
    figsize : tuple[float, float]
        Figure size in inches.
    dpi : int
        Image resolution.

    Returns
    -------
    str
        Absolute path to the saved PNG file.
    """
    if len(graph.nodes) == 0:
        raise ValueError("Graph has no nodes to plot")

    config = config or {}
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=figsize, dpi=dpi, facecolor="#F8FAFC")
    ax.set_facecolor("#F8FAFC")

    # Consistent layout: circular layout ensures symmetry and readable arrows
    nodes = list(graph.nodes())
    pos = nx.circular_layout(graph)

    # Color mapping consistent with opinion trajectory
    color_map = {
        node: _AGENT_COLOURS[i % len(_AGENT_COLOURS)]
        for i, node in enumerate(nodes)
    }

    # Draw nodes
    node_colors = [color_map[n] for n in nodes]
    nx.draw_networkx_nodes(
        graph,
        pos,
        nodelist=nodes,
        node_size=3200,
        node_color=node_colors,
        edgecolors="#1E293B",
        linewidths=2.5,
        ax=ax,
    )

    # Draw node labels
    labels = {n: _format_agent_label(n) for n in nodes}
    nx.draw_networkx_labels(
        graph,
        pos,
        labels=labels,
        font_size=9.5,
        font_weight="bold",
        font_color="#FFFFFF",
        ax=ax,
    )

    # Edge weights and drawing
    edges = list(graph.edges(data=True))
    total_messages = sum(d.get("weight", 1) for _, _, d in edges)
    max_weight = max((d.get("weight", 1) for _, _, d in edges), default=1)

    if edges:
        for u, v, d in edges:
            weight = d.get("weight", 1)
            # Width scales with message volume: 1.5 to 5.0
            width = 1.5 + 3.5 * (weight / max(max_weight, 1))
            # Alpha scales with weight
            alpha = min(0.45 + 0.5 * (weight / max(max_weight, 1)), 0.95)
            # Arrow size
            arrow_size = 18 + int(8 * (weight / max(max_weight, 1)))

            # Curved connection prevents bidirectional edge overlap
            nx.draw_networkx_edges(
                graph,
                pos,
                edgelist=[(u, v)],
                width=width,
                edge_color="#334155",
                alpha=alpha,
                arrows=True,
                arrowsize=arrow_size,
                arrowstyle="-|>",
                connectionstyle="arc3,rad=0.14",
                node_size=3200,
                ax=ax,
            )

        # Draw edge weight labels
        # Compute positions along the curved arc
        for u, v, d in edges:
            weight = d.get("weight", 1)
            p1 = pos[u]
            p2 = pos[v]
            # Midpoint with perpendicular offset for curved arc
            mx = (p1[0] + p2[0]) / 2.0
            my = (p1[1] + p2[1]) / 2.0
            dx = p2[0] - p1[0]
            dy = p2[1] - p1[1]
            dist = math.hypot(dx, dy)
            if dist > 1e-6:
                # Perpendicular unit vector (-dy, dx)
                offset = 0.08
                lx = mx - (dy / dist) * offset
                ly = my + (dx / dist) * offset
            else:
                lx, ly = mx, my

            ax.text(
                lx,
                ly,
                str(weight),
                fontsize=8.5,
                fontweight="bold",
                color="#0F172A",
                bbox=dict(
                    boxstyle="round,pad=0.22",
                    facecolor="#FFFFFF",
                    edgecolor="#94A3B8",
                    alpha=0.9,
                    linewidth=0.8,
                ),
                ha="center",
                va="center",
                zorder=10,
            )

    # Titles & Metadata
    disc_id = config.get("discussion_id", "N/A")
    raw_topic = config.get("topic", "")
    if len(raw_topic) > 70:
        topic_display = raw_topic[:67] + "..."
    else:
        topic_display = raw_topic

    if title:
        chart_title = title
    else:
        chart_title = "Agent Interaction Graph (Communication Volume)"

    ax.set_title(
        chart_title,
        fontsize=15,
        fontweight="bold",
        pad=24,
        color="#0F172A",
    )

    # Subtitle with discussion metadata
    subtitle = (
        f"Topic: \"{topic_display}\"  |  ID: {disc_id}\n"
        f"Agents: {len(nodes)}  |  Directed Edges: {len(edges)}  |  Total Messages Exchanged: {total_messages}"
    )
    fig.text(
        0.5,
        0.915,
        subtitle,
        ha="center",
        fontsize=9.5,
        color="#475569",
        linespacing=1.4,
    )

    # Explanatory Legend / Footnote
    legend_elements = [
        mpatches.Patch(
            facecolor="#E2E8F0",
            edgecolor="#1E293B",
            label="Agent Node (Colored by Persona)",
        ),
        mpatches.Patch(
            facecolor="#334155",
            edgecolor="none",
            label="Directed Edge (Curved Arrow: Sender → Recipient)",
        ),
        mpatches.Patch(
            facecolor="#FFFFFF",
            edgecolor="#94A3B8",
            label="Badge Number: Message Count (Edge Weight)",
        ),
    ]
    ax.legend(
        handles=legend_elements,
        loc="lower center",
        bbox_to_anchor=(0.5, -0.06),
        ncol=3,
        fontsize=8.5,
        frameon=True,
        facecolor="#FFFFFF",
        edgecolor="#E2E8F0",
    )

    ax.axis("off")
    plt.tight_layout(rect=[0.02, 0.05, 0.98, 0.90])

    output_p = Path(output_path).resolve()
    output_p.parent.mkdir(parents=True, exist_ok=True)
    saved = False
    for attempt in range(3):
        try:
            with open(output_p, "wb") as f:
                fig.savefig(f, format="png", dpi=dpi, facecolor=fig.get_facecolor(), bbox_inches="tight")
            saved = True
            break
        except (OSError, PermissionError):
            import time
            time.sleep(0.3)

    if not saved:
        fig.savefig(str(output_p), format="png", dpi=dpi, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)

    abs_path = str(output_p)
    logger.info("Saved interaction graph to %s", abs_path)
    return abs_path


def generate_interaction_graph_from_discussion(
    discussion_input: Any,
    output_dir: str | Path = "reports",
    *,
    filename: str | None = None,
    title: str | None = None,
) -> str:
    """Generate a weighted interaction graph PNG from a discussion.

    Parameters
    ----------
    discussion_input : DiscussionResult, dict, or str/Path
        Discussion data or path to saved discussion JSON.
    output_dir : str or Path
        Output directory (default: reports/).
    filename : str, optional
        Filename override. Defaults to interaction_graph_{discussion_id}.png.
    title : str, optional
        Optional chart title override.

    Returns
    -------
    str
        Absolute path to the saved image file.
    """
    graph, config = extract_interaction_data(discussion_input)

    disc_id = config.get("discussion_id", "discussion")
    if filename is None:
        filename = f"interaction_graph_{disc_id}.png"

    output_path = Path(output_dir).resolve() / filename
    return plot_interaction_graph(graph, config, output_path, title=title)


# ── CLI entry point ─────────────────────────────────────────────────────

def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Generate an agent interaction graph from a Week 3 discussion."
    )
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Path to a saved discussion JSON file.",
    )
    parser.add_argument(
        "--output-dir", "-o",
        default="reports",
        help="Directory for output chart (default: reports/).",
    )
    parser.add_argument(
        "--filename", "-f",
        default=None,
        help="Override output filename (default: interaction_graph_{id}.png).",
    )
    parser.add_argument(
        "--title", "-t",
        default=None,
        help="Optional custom chart title.",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    try:
        path = generate_interaction_graph_from_discussion(
            args.input,
            output_dir=args.output_dir,
            filename=args.filename,
            title=args.title,
        )
        print(f"Interaction graph saved: {path}")
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
