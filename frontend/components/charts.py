"""
frontend/components/charts.py
------------------------------
Reusable, stateless chart-building functions for the Week 4 Analytics
Dashboard (Opinion Dynamics / Multi-Agent Discussion visualizations).

Every function here takes plain pandas DataFrames / dicts (no Streamlit
session logic, no file I/O) and returns a Plotly figure, so it can be
unit-tested and reused across pages.

Data shapes expected (documented so the backend/data team can match it,
or `frontend/views/analytics.py` can be adapted if the real Week 3/4
output schema differs):

opinions_df        columns: ["round", "agent_id", "agent_name", "opinion"]
                    "opinion" is a float in [-1.0, +1.0]

consensus_df        columns: ["round", "agreement_score"]
                    "agreement_score" is a float in [0.0, 1.0]

influence_df         square matrix (pandas DataFrame) of Pearson r values,
                    index & columns = agent names/ids

causal_df           square matrix (pandas DataFrame) of causal-impact
                    (tau) values, index & columns = agent names/ids

sentiment_df        columns: ["round", "agent_id", "agent_name", "sentiment"]
                    "sentiment" is a float, typically in [-1.0, +1.0]

network_nodes       list[dict]: [{"id": "...", "label": "...", "group": "..."}]
network_edges       list[dict]: [{"source": "...", "target": "...", "weight": 0.0}]
"""

from __future__ import annotations

import math
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# A small, consistent palette so an agent keeps the same color across charts
PALETTE = px.colors.qualitative.Set2


def _color_for(index: int) -> str:
    return PALETTE[index % len(PALETTE)]


# ---------------------------------------------------------------------------
# 1. Opinion Trajectory line chart
# ---------------------------------------------------------------------------
def opinion_trajectory_chart(opinions_df: pd.DataFrame) -> go.Figure:
    """Line chart of each agent's opinion (y in [-1, 1]) across rounds."""
    fig = go.Figure()

    if opinions_df is None or opinions_df.empty:
        fig.update_layout(title="Opinion Trajectory — no data yet")
        return fig

    for i, (agent_id, group) in enumerate(opinions_df.groupby("agent_id")):
        group = group.sort_values("round")
        label = group["agent_name"].iloc[0] if "agent_name" in group else agent_id
        fig.add_trace(
            go.Scatter(
                x=group["round"],
                y=group["opinion"],
                mode="lines+markers",
                name=label,
                line=dict(width=2, color=_color_for(i)),
                marker=dict(size=6),
                hovertemplate="Round %{x}<br>Opinion: %{y:.2f}<extra>" + label + "</extra>",
            )
        )

    fig.add_hline(y=0, line_dash="dot", line_color="gray", opacity=0.5)
    fig.update_layout(
        title="Opinion Trajectory Over Rounds",
        xaxis_title="Round",
        yaxis_title="Opinion",
        yaxis=dict(range=[-1.0, 1.0]),
        legend_title="Agent",
        template="plotly_white",
        hovermode="x unified",
    )
    return fig


# ---------------------------------------------------------------------------
# 2. Consensus & Agreement trend card / gauge
# ---------------------------------------------------------------------------
def consensus_trend_chart(consensus_df: pd.DataFrame) -> go.Figure:
    """Line chart of the agreement score across rounds."""
    fig = go.Figure()
    if consensus_df is None or consensus_df.empty:
        fig.update_layout(title="Consensus Trend — no data yet")
        return fig

    fig.add_trace(
        go.Scatter(
            x=consensus_df["round"],
            y=consensus_df["agreement_score"],
            mode="lines+markers",
            fill="tozeroy",
            line=dict(width=3, color="#2E86AB"),
        )
    )
    fig.update_layout(
        title="Consensus / Agreement Trend",
        xaxis_title="Round",
        yaxis_title="Agreement Score",
        yaxis=dict(range=[0, 1]),
        template="plotly_white",
    )
    return fig


def agreement_gauge(value: float, title: str = "Current Agreement") -> go.Figure:
    """A single gauge (0-1) showing the latest consensus/agreement level."""
    value = 0.0 if value is None or math.isnan(value) else float(value)
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=value,
            number={"valueformat": ".0%"},
            title={"text": title},
            gauge={
                "axis": {"range": [0, 1]},
                "bar": {"color": "#2E86AB"},
                "steps": [
                    {"range": [0, 0.33], "color": "#F6DDCC"},
                    {"range": [0.33, 0.66], "color": "#FAE5D3"},
                    {"range": [0.66, 1.0], "color": "#D5F5E3"},
                ],
            },
        )
    )
    fig.update_layout(height=260, margin=dict(l=20, r=20, t=60, b=10))
    return fig


# ---------------------------------------------------------------------------
# 3. Influence (r) & Causal impact (tau) comparison tables
# ---------------------------------------------------------------------------
def matrix_to_heatmap(matrix_df: pd.DataFrame, title: str, colorscale: str = "RdBu") -> go.Figure:
    """Render a square influence/causal matrix as an annotated heatmap."""
    fig = go.Figure()
    if matrix_df is None or matrix_df.empty:
        fig.update_layout(title=f"{title} — no data yet")
        return fig

    fig.add_trace(
        go.Heatmap(
            z=matrix_df.values,
            x=list(matrix_df.columns),
            y=list(matrix_df.index),
            colorscale=colorscale,
            zmid=0,
            text=matrix_df.round(2).values,
            texttemplate="%{text}",
            hovertemplate="%{y} → %{x}: %{z:.2f}<extra></extra>",
        )
    )
    fig.update_layout(title=title, template="plotly_white", xaxis_title="Target agent", yaxis_title="Source agent")
    return fig


def influence_causal_table(influence_df: pd.DataFrame, causal_df: pd.DataFrame) -> pd.DataFrame:
    """
    Flatten the influence (r) and causal-impact (tau) matrices into a single
    long-format comparison table for a Streamlit dataframe / st.table.

    Returns columns: ["source", "target", "influence_r", "causal_tau"]
    """
    if influence_df is None or influence_df.empty:
        return pd.DataFrame(columns=["source", "target", "influence_r", "causal_tau"])

    rows = []
    for source in influence_df.index:
        for target in influence_df.columns:
            if source == target:
                continue
            r_val = influence_df.loc[source, target]
            tau_val = causal_df.loc[source, target] if (causal_df is not None and source in causal_df.index and target in causal_df.columns) else None
            rows.append({"source": source, "target": target, "influence_r": r_val, "causal_tau": tau_val})
    return pd.DataFrame(rows).sort_values("influence_r", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# 4. Discourse Sentiment chart
# ---------------------------------------------------------------------------
def sentiment_chart(sentiment_df: pd.DataFrame) -> go.Figure:
    """Grouped bar/line chart of discourse sentiment per agent, per round."""
    fig = go.Figure()
    if sentiment_df is None or sentiment_df.empty:
        fig.update_layout(title="Discourse Sentiment — no data yet")
        return fig

    for i, (agent_id, group) in enumerate(sentiment_df.groupby("agent_id")):
        group = group.sort_values("round")
        label = group["agent_name"].iloc[0] if "agent_name" in group else agent_id
        fig.add_trace(
            go.Bar(
                x=group["round"],
                y=group["sentiment"],
                name=label,
                marker_color=_color_for(i),
            )
        )

    fig.update_layout(
        title="Discourse Sentiment by Round",
        xaxis_title="Round",
        yaxis_title="Sentiment",
        barmode="group",
        template="plotly_white",
    )
    return fig


# ---------------------------------------------------------------------------
# 5. Week 4 Interaction Network Graph
# ---------------------------------------------------------------------------
def interaction_network_graph(nodes: list, edges: list) -> go.Figure:
    """
    Force-directed style network graph of agent interactions.
    nodes: [{"id","label","group"}]
    edges: [{"source","target","weight"}]

    Uses a simple circular/spring layout without requiring networkx,
    so it has no extra hard dependency beyond plotly + math.
    """
    fig = go.Figure()
    if not nodes:
        fig.update_layout(title="Interaction Network — no data yet")
        return fig

    try:
        import networkx as nx

        G = nx.DiGraph()
        for n in nodes:
            G.add_node(n["id"], label=n.get("label", n["id"]))
        for e in edges:
            G.add_edge(e["source"], e["target"], weight=e.get("weight", 1.0))
        pos = nx.spring_layout(G, seed=42)
    except ImportError:
        # Fallback: even circular layout, no external dependency
        n = len(nodes)
        pos = {
            node["id"]: (math.cos(2 * math.pi * i / n), math.sin(2 * math.pi * i / n))
            for i, node in enumerate(nodes)
        }

    # Edges
    edge_x, edge_y = [], []
    for e in edges:
        if e["source"] not in pos or e["target"] not in pos:
            continue
        x0, y0 = pos[e["source"]]
        x1, y1 = pos[e["target"]]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]

    fig.add_trace(
        go.Scatter(
            x=edge_x, y=edge_y, mode="lines",
            line=dict(width=1, color="#B0B0B0"),
            hoverinfo="none", showlegend=False,
        )
    )

    # Nodes
    node_x = [pos[n["id"]][0] for n in nodes if n["id"] in pos]
    node_y = [pos[n["id"]][1] for n in nodes if n["id"] in pos]
    node_labels = [n.get("label", n["id"]) for n in nodes if n["id"] in pos]
    degree = {n["id"]: 0 for n in nodes}
    for e in edges:
        degree[e["source"]] = degree.get(e["source"], 0) + 1
        degree[e["target"]] = degree.get(e["target"], 0) + 1
    node_size = [18 + 6 * degree.get(n["id"], 0) for n in nodes if n["id"] in pos]

    fig.add_trace(
        go.Scatter(
            x=node_x, y=node_y, mode="markers+text",
            text=node_labels, textposition="top center",
            marker=dict(size=node_size, color=[_color_for(i) for i in range(len(node_x))], line=dict(width=1, color="white")),
            hovertemplate="%{text}<extra></extra>",
            showlegend=False,
        )
    )

    fig.update_layout(
        title="Week 4 Interaction Network",
        template="plotly_white",
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        margin=dict(l=10, r=10, t=50, b=10),
    )
    return fig
