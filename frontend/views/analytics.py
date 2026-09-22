"""
frontend/views/analytics.py
----------------------------
Week 4 — Analytics Dashboard (Visualizations) page.

Run standalone with:
    streamlit run frontend/views/analytics.py

Or import `render()` from a multi-page Streamlit app / router and call it
from the page that owns navigation.

DATA SOURCE
-----------
By default this looks for a results file at:
    data/outputs/week4_results.json
(relative to the project root). If it isn't found yet, a small synthetic
demo dataset is generated instead so the page still renders end-to-end —
this satisfies "Opinion Trajectory chart renders" / "Interaction network
graph displays properly" even before the Week 3/4 backend output exists.
Swap in the real file (or point WEEK4_RESULTS_PATH at it) once it's ready.

EXPECTED JSON SCHEMA (adjust the `load_week4_results` parsing below if the
backend's actual output differs — the chart functions in
frontend/components/charts.py only care about the DataFrames/dicts
produced here, not this file's shape):

{
  "topic": "string",
  "agents": [{"id": "agent_1", "name": "The Pragmatist"}, ...],
  "rounds": [
    {
      "round": 1,
      "opinions": {"agent_1": 0.3, "agent_2": -0.1},
      "sentiment": {"agent_1": 0.2, "agent_2": -0.4}
    },
    ...
  ],
  "consensus": [{"round": 1, "agreement_score": 0.42}, ...],
  "influence_matrix": {"agent_1": {"agent_2": 0.75}, "agent_2": {"agent_1": 0.31}},
  "causal_impact_matrix": {"agent_1": {"agent_2": 0.42}, "agent_2": {"agent_1": 0.10}},
  "interaction_network": {
    "nodes": [{"id": "agent_1", "label": "The Pragmatist"}, ...],
    "edges": [{"source": "agent_1", "target": "agent_2", "weight": 0.8}, ...]
  }
}
"""

from __future__ import annotations

import json
import os
import random

import pandas as pd
import streamlit as st

# Support running this file directly (streamlit run ...) as well as being
# imported as part of the `frontend` package.
try:
    from frontend.components import charts
except ImportError:  # pragma: no cover - fallback for standalone execution
    import sys

    sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
    from frontend.components import charts

WEEK4_RESULTS_PATH = os.environ.get(
    "WEEK4_RESULTS_PATH",
    os.path.join("data", "outputs", "week4_results.json"),
)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
def _generate_demo_data() -> dict:
    """Small synthetic dataset with the same shape as the expected schema,
    used only when the real Week 4 results file isn't available yet."""
    random.seed(7)
    agents = [
        {"id": "agent_1", "name": "The Pragmatist"},
        {"id": "agent_2", "name": "The Purist"},
        {"id": "agent_3", "name": "The Analyst"},
    ]
    n_rounds = 6
    opinions = {a["id"]: random.uniform(-0.6, 0.6) for a in agents}
    rounds = []
    for r in range(1, n_rounds + 1):
        for a in agents:
            opinions[a["id"]] = max(-1.0, min(1.0, opinions[a["id"]] + random.uniform(-0.15, 0.25)))
        rounds.append(
            {
                "round": r,
                "opinions": dict(opinions),
                "sentiment": {a["id"]: random.uniform(-1.0, 1.0) for a in agents},
            }
        )

    consensus = [
        {"round": r, "agreement_score": min(1.0, 0.15 * r + random.uniform(0, 0.1))}
        for r in range(1, n_rounds + 1)
    ]

    influence_matrix = {
        a["id"]: {b["id"]: (0.0 if a is b else round(random.uniform(-0.2, 0.9), 2)) for b in agents}
        for a in agents
    }
    causal_impact_matrix = {
        a["id"]: {b["id"]: (0.0 if a is b else round(random.uniform(-0.2, 0.6), 2)) for b in agents}
        for a in agents
    }

    edges = []
    for a in agents:
        for b in agents:
            if a is b:
                continue
            w = influence_matrix[a["id"]][b["id"]]
            if w > 0.4:
                edges.append({"source": a["id"], "target": b["id"], "weight": w})

    return {
        "topic": "Demo topic — replace with real Week 4 results",
        "agents": agents,
        "rounds": rounds,
        "consensus": consensus,
        "influence_matrix": influence_matrix,
        "causal_impact_matrix": causal_impact_matrix,
        "interaction_network": {
            "nodes": [{"id": a["id"], "label": a["name"]} for a in agents],
            "edges": edges,
        },
    }


@st.cache_data(show_spinner=False)
def load_week4_results(path: str = WEEK4_RESULTS_PATH) -> dict:
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return _generate_demo_data()


def _agent_name_lookup(data: dict) -> dict:
    return {a["id"]: a.get("name", a["id"]) for a in data.get("agents", [])}


def _opinions_dataframe(data: dict) -> pd.DataFrame:
    names = _agent_name_lookup(data)
    rows = []
    for rnd in data.get("rounds", []):
        for agent_id, opinion in rnd.get("opinions", {}).items():
            rows.append(
                {
                    "round": rnd["round"],
                    "agent_id": agent_id,
                    "agent_name": names.get(agent_id, agent_id),
                    "opinion": opinion,
                }
            )
    return pd.DataFrame(rows)


def _sentiment_dataframe(data: dict) -> pd.DataFrame:
    names = _agent_name_lookup(data)
    rows = []
    for rnd in data.get("rounds", []):
        for agent_id, sentiment in rnd.get("sentiment", {}).items():
            rows.append(
                {
                    "round": rnd["round"],
                    "agent_id": agent_id,
                    "agent_name": names.get(agent_id, agent_id),
                    "sentiment": sentiment,
                }
            )
    return pd.DataFrame(rows)


def _consensus_dataframe(data: dict) -> pd.DataFrame:
    return pd.DataFrame(data.get("consensus", []))


def _matrix_dataframe(data: dict, key: str) -> pd.DataFrame:
    names = _agent_name_lookup(data)
    matrix = data.get(key, {})
    if not matrix:
        return pd.DataFrame()
    df = pd.DataFrame(matrix).fillna(0.0)
    df.index = [names.get(i, i) for i in df.index]
    df.columns = [names.get(c, c) for c in df.columns]
    return df


# ---------------------------------------------------------------------------
# Page render
# ---------------------------------------------------------------------------
def render() -> None:
    st.set_page_config(page_title="Analytics Dashboard — Week 4", layout="wide")
    st.title("📊 Analytics Dashboard")
    st.caption("Opinion dynamics, consensus, influence, causal impact, sentiment & interaction network")

    data = load_week4_results()
    st.markdown(f"**Topic:** {data.get('topic', '—')}")

    opinions_df = _opinions_dataframe(data)
    sentiment_df = _sentiment_dataframe(data)
    consensus_df = _consensus_dataframe(data)
    influence_df = _matrix_dataframe(data, "influence_matrix")
    causal_df = _matrix_dataframe(data, "causal_impact_matrix")
    network = data.get("interaction_network", {"nodes": [], "edges": []})

    # --- Opinion Trajectory ------------------------------------------------
    st.subheader("Opinion Trajectory")
    st.plotly_chart(charts.opinion_trajectory_chart(opinions_df), use_container_width=True)

    # --- Consensus & Agreement ----------------------------------------------
    st.subheader("Consensus & Agreement")
    col1, col2 = st.columns([2, 1])
    with col1:
        st.plotly_chart(charts.consensus_trend_chart(consensus_df), use_container_width=True)
    with col2:
        latest = consensus_df["agreement_score"].iloc[-1] if not consensus_df.empty else 0.0
        st.plotly_chart(charts.agreement_gauge(latest), use_container_width=True)

    # --- Influence & Causal Impact ------------------------------------------
    st.subheader("Influence (r) & Causal Impact (τ)")
    col3, col4 = st.columns(2)
    with col3:
        st.plotly_chart(charts.matrix_to_heatmap(influence_df, "Influence (Pearson r)"), use_container_width=True)
    with col4:
        st.plotly_chart(charts.matrix_to_heatmap(causal_df, "Causal Impact (τ)"), use_container_width=True)
    st.dataframe(
        charts.influence_causal_table(influence_df, causal_df),
        use_container_width=True,
        hide_index=True,
    )

    # --- Discourse Sentiment --------------------------------------------------
    st.subheader("Discourse Sentiment")
    st.plotly_chart(charts.sentiment_chart(sentiment_df), use_container_width=True)

    # --- Week 4 Interaction Network Graph ------------------------------------
    st.subheader("Week 4 Interaction Network")
    st.plotly_chart(
        charts.interaction_network_graph(network.get("nodes", []), network.get("edges", [])),
        use_container_width=True,
    )


if __name__ == "__main__":
    render()
