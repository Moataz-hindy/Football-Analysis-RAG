# Week 4 Analytics & Intelligence Layer Guide

This document specifies the complete analytics and intelligence architecture for Week 4 of the multi-agent discussion platform. It details mathematical formulas, exact commands, output locations, methodological limitations, and the integration interface for the **Week 5 Dashboard**.

---

## 1. Architectural Overview

The Week 4 analytics layer consumes persisted discussion histories from Week 3 and produces:
1. **Opinion Dynamics:** Per-agent, per-round continuous stance trajectories.
2. **Group Consensus:** Pairwise agreement and dispersion metrics across rounds.
3. **Agent Influence:** Directed correlation-based persuasion scores and distance-reduction impact.
4. **Dialogue Sentiment:** Per-message and aggregated VADER emotional/tonal scoring.
5. **Visualizations:** Opinion trajectory chart and weighted interaction network graph.
6. **Executive Reporting:** Automatically generated Markdown report.

```text
Week 3 Discussion History (outputs/*.json)
                   │
                   ▼
┌────────────────────────────────────────────────────────┐
│               Week 4 Analytics Engine                  │
│                                                        │
│  1. Stance Trajectories      3. Agent Influence        │
│  2. Round Agreement          4. Message Sentiment      │
└──────────────────────────┬─────────────────────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
   Unified JSON     Visualizations    Markdown Report
  (outputs/*.json)  (reports/*.png)   (reports/*.md)
         │                 │                 │
         └─────────────────┼─────────────────┘
                           ▼
                 Week 5 Dashboard (UI)
```

---

## 2. Mathematical Formulations

### 2.1 Stance Trajectories & Opinion Change
Each agent $a \in \mathcal{A}$ at round $r \in \{0, \dots, R\}$ is evaluated for its quantitative alignment $S_{a, r} \in [-1.0, +1.0]$ relative to declared debate poles:
* $+1.0$: Complete agreement with the declared positive pole.
* $0.0$: Neutral, balanced, or agnostic position.
* $-1.0$: Complete agreement with the declared negative pole.

Round-to-round opinion change is defined as:
$$\Delta S_{a, r} = S_{a, r} - S_{a, r-1} \quad \text{for } r \ge 1, \quad \Delta S_{a, 0} = \text{None}$$

### 2.2 Pairwise Agreement & Round Consensus
For every unique agent pair $(u, v)$ at round $r$, dyadic agreement evaluates positional proximity:
$$A(u, v, r) = 1.0 - \frac{|S_{u, r} - S_{v, r}|}{2.0} \in [0.0, 1.0]$$

Round agreement $A(r)$ is the unweighted arithmetic mean over all $\binom{N}{2}$ dyads:
$$A(r) = \frac{2}{N(N-1)} \sum_{u < v} A(u, v, r)$$

Net consensus shift:
$$\Delta A_{\text{net}} = A(R) - A(0)$$
* $\Delta A_{\text{net}} > 0.05 \implies \textbf{Convergence}$
* $\Delta A_{\text{net}} < -0.05 \implies \textbf{Divergence}$
* $|\Delta A_{\text{net}}| \le 0.05 \implies \textbf{Stable}$

### 2.3 Correlation-Based Influence Metric
Evaluates how strongly outbound communication volume from sender $s$ associates with subsequent stance change in recipient $rec$.

For each dyad $(s, rec)$ with observation pairs $(M_{s \to rec, t}, \Delta S_{rec, t+1})$:
$$r(s, rec) = \frac{\sum_{t} (M_{s \to rec, t} - \bar{M})(\Delta S_{rec, t+1} - \bar{\Delta S})}{\sqrt{\sum_{t} (M_{s \to rec, t} - \bar{M})^2 \sum_{t} (\Delta S_{rec, t+1} - \bar{\Delta S})^2}}$$

Agent influence score $I(s)$ averages valid outgoing correlation coefficients:
$$I(s) = \frac{1}{|\mathcal{R}_s|} \sum_{rec \in \mathcal{R}_s} r(s, rec)$$
Where pairs with invariant message volume, invariant recipient stances, or fewer than 2 data points produce explicit `None` with `status: "insufficient_data"`.

### 2.4 Weighted Interaction Graph
Agents form vertices $V = \mathcal{A}$. Directed edges $E = \{(u, v)\}$ carry integer message weights:
$$W(u \to v) = \sum_{m \in \mathcal{M}} \mathbb{I}(\text{sender}(m) = u \;\land\; v \in \text{recipients}(m))$$

### 2.5 Message Sentiment
VADER sentiment computes normalized valence compound score $c(m) \in [-1.0, +1.0]$ per message $m$. Categorized as:
* Positive: $c(m) \ge 0.05$
* Neutral: $-0.05 < c(m) < 0.05$
* Negative: $c(m) \le -0.05$

---

## 3. Exact Commands & CLI Usage

### 3.1 Run Full Analytics Pipeline
Executes all four metric categories, generates both visualizations, and compiles the Markdown report:
```bash
python -m src.analytics.run_analytics \
  --input outputs/demo_repro_run.json \
  --output outputs/analytics_result.json \
  --visualize \
  --report \
  --reports-dir reports
```

### 3.2 Reuse Saved Stance Scores (Zero Repeated Model Calls)
Reuses verified cached stance scores without repeating LLM requests:
```bash
python -m src.analytics.run_analytics \
  --input outputs/demo_repro_run.json \
  --scores-from outputs/saved_scores.json \
  --output outputs/analytics_result.json \
  --visualize \
  --report
```

### 3.3 Standalone Visualization Commands

**Generate Opinion Trajectory Chart:**
```bash
# From discussion or saved scores
python -m src.visualization.opinion_trajectory \
  --input outputs/demo_repro_run.json \
  --scores-from outputs/saved_scores.json \
  --output-dir reports
```

**Generate Weighted Interaction Graph:**
```bash
python -m src.visualization.interaction_graph \
  --input outputs/demo_repro_run.json \
  --output-dir reports
```

### 3.4 Standalone Markdown Report Generation
```bash
python -m src.reporting.report \
  --analytics outputs/analytics_result.json \
  --output reports/discussion_report.md
```

---

## 4. Output Artifacts & Locations

| Output Type | Canonical Path | Description |
| :--- | :--- | :--- |
| **Unified Analytics JSON** | `outputs/{discussion_id}_analytics.json` | Complete machine-readable results for all 4 categories. |
| **Markdown Report** | `reports/discussion_report_{discussion_id}.md` | Complete narrative executive brief with tables and disclosures. |
| **Opinion Trajectory Chart** | `reports/opinion_trajectory_{discussion_id}.png` | Multi-line PNG showing round-by-round agent stances. |
| **Interaction Graph** | `reports/interaction_graph_{discussion_id}.png` | Directed network PNG showing message volume weights. |

---

## 5. Methodological Limitations & Integrity Disclosures

The correlation-based influence metric implemented here remains exploratory. It uses scalar opinion scores as a simplified numerical representation of complex multi-paragraph debate content and operates across a limited observation window (typically 3–5 rounds).

1. **Content Abstraction:** Numeric stance values condense rich domain argumentation into a 1-dimensional scalar position $[-1.0, +1.0]$. Nuanced tactical qualifications or conditional agreements are necessarily compressed.
2. **Statistical Power:** Deliberations of 3 to 5 rounds yield limited time-series observations per agent dyad. Correlation coefficients ($r$) require cautious interpretation and reflect directional association rather than causal proof.
3. **Alignment vs. Correctness:** Group agreement measures internal consensus among the participating agent personas; it does not measure or guarantee factual truth or objective football correctness.
4. **Missing Data Handling:** Incomplete rounds, unclassified stances, or invariant trajectories are retained as explicit `null` / `None` values to guarantee transparency and eliminate synthetic score fabrication.

---

## 6. Week 5 Interface Contract

Downstream dashboards in Week 5 can consume outputs directly through two entry points:

### Python API Integration
```python
import json
from pathlib import Path

# 1. Load precomputed analytics
analytics_data = json.loads(Path("outputs/analytics_result.json").read_text(encoding="utf-8"))

# Category 1: Opinion Trajectories
trajectories = analytics_data["task1_opinion_trajectories"]["trajectories"]

# Category 2: Agreement Dynamics
agreement_trend = analytics_data["task2_discussion_agreement"]["overall_trend"]
round_agreements = analytics_data["task2_discussion_agreement"]["round_agreements"]

# Category 3: Influence
influences = analytics_data["task3_agent_influence"]["agent_influences"]

# Category 4: Sentiment
sentiment_summary = analytics_data["task4_sentiment"]["summary"]

# Visualizations and Report file paths
charts = analytics_data.get("visualizations", {})
trajectory_png = charts.get("opinion_trajectory")
interaction_png = charts.get("interaction_graph")
report_md = analytics_data.get("report_path")
```

### Direct File Consumption
The Week 5 dashboard frontend can load pre-rendered artifacts directly from `reports/` and `outputs/` without running the analytics engine or triggering model calls.
