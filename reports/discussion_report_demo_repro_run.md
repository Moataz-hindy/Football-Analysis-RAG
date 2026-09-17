# Multi-Agent Discussion Analytics Report

> **Discussion ID:** `demo_repro_run`  
> **Topic:** *Should VAR intervene on subjective penalty box contact in high-stakes matches?*  
> **Participating Agents:** 6  |  **Total Rounds:** 3

## Executive Overview

| Metric Dimension | Measurement Summary | Status / Trend |
| :--- | :--- | :--- |
| **Discussion Consensus** | Initial: N/A → Final: N/A | `Insufficient Data` (N/A) |
| **Lead Influencer** | Exploratory / Insufficient observations | Pearson $r$ correlation |
| **Dialogue Tone** | Mean Compound: -0.036 (24/24 messages) | Pos: 50.0% / Neg: 25.0% |
| **Stance Scoring Method** | `self_report_rules` (Cached reuse: `False`) | Verified integrity |

---
## 1. Opinion Dynamics & Stance Evolution

Tracks each agent's quantitative position over time on the normalized stance scale $[-1.0, +1.0]$.

| Agent | Round 0 | Round 1 | Round 2 | Round 3 | Net Shift (Δ) | Final Position |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **`context_analyst`** | *null* | *null* | *null* | *null* | N/A | Unclassified |
| **`fan_analyst`** | *null* | *null* | *null* | *null* | N/A | Unclassified |
| **`performance_analyst`** | *null* | *null* | *null* | *null* | N/A | Unclassified |
| **`refereeing_analyst`** | *null* | *null* | *null* | *null* | N/A | Unclassified |
| **`statistical_analyst`** | *null* | *null* | *null* | *null* | N/A | Unclassified |
| **`tactical_analyst`** | *null* | *null* | *null* | *null* | N/A | Unclassified |

### Key Observations:
- Stance changes reflect the integration of counter-arguments and empirical evidence retrieved across rounds.

---
## 2. Agreement & Group Consensus Dynamics

Pairwise agreement evaluates collective alignment across all agent dyads at each discussion round on a $[0.0, 1.0]$ scale (where $1.0$ is perfect consensus and $0.0$ is total polarization).

| Discussion Round | Agreement Score | Stance Dispersion (StdDev) | Dyad Range | Consensus State |
| :---: | :---: | :---: | :---: | :--- |

**Trajectory Classification:** The group demonstrated an overall **`Insufficient Data`** pattern with a net agreement shift of **N/A**.

---
## 3. Agent Influence & Cross-Agent Persuasion

Influence measures how strongly each sender's communication associates with downstream opinion adjustments in their recipients. Evaluated via Pearson correlation between incoming message volume and subsequent recipient stance changes.

| Agent | Influence Score ($r$) | Statistical Status | Active Targets | Outbound Volume |
| :--- | :---: | :---: | :---: | :---: |
| **`context_analyst`** | N/A | `insufficient_data` | 0 | 0 msgs |
| **`fan_analyst`** | N/A | `insufficient_data` | 0 | 0 msgs |
| **`performance_analyst`** | N/A | `insufficient_data` | 0 | 0 msgs |
| **`refereeing_analyst`** | N/A | `insufficient_data` | 0 | 0 msgs |
| **`statistical_analyst`** | N/A | `insufficient_data` | 0 | 0 msgs |
| **`tactical_analyst`** | N/A | `insufficient_data` | 0 | 0 msgs |

---
## 4. Communication Sentiment & Discourse Tone

Measures discourse tone using VADER sentiment analysis over all transmitted messages.

### Overall Corpus Sentiment:
- **Total Messages Analyzed:** 24 (24 scored)
- **Mean Compound Sentiment:** -0.036 (Scale: $[-1.0, +1.0]$)
- **Distribution:** Positive: `12` (50.0%) | Neutral: `6` (25.0%) | Negative: `6` (25.0%)

### Per-Agent Sentiment Profile:

| Agent | Messages Sent | Mean Compound | Tone Classification |
| :--- | :---: | :---: | :--- |
| **`context_analyst`** | 4 | -0.036 | Objective / Neutral |
| **`fan_analyst`** | 4 | -0.036 | Objective / Neutral |
| **`performance_analyst`** | 4 | -0.036 | Objective / Neutral |
| **`refereeing_analyst`** | 4 | -0.036 | Objective / Neutral |
| **`statistical_analyst`** | 4 | -0.036 | Objective / Neutral |
| **`tactical_analyst`** | 4 | -0.036 | Objective / Neutral |

---
## 5. Visualizations & Network Artifacts

### Opinion Trajectory Chart
![Opinion Trajectory](opinion_trajectory_demo_repro_run.png)

### Agent Interaction Graph
![Interaction Graph](C:\tmp\Football-Analysis-RAG-v2\reports\interaction_graph_demo_repro_run.png)

---
## 6. Methodological Limitations & Integrity Disclosures

> **Exploratory Metric Notice:**  
> The correlation-based influence metric implemented here remains exploratory. It uses scalar opinion scores as a simplified numerical representation of complex multi-paragraph debate content and operates across a limited observation window (3–5 discussion rounds).

### Specific Technical Constraints:
1. **Content Abstraction:** Numeric stance values condense rich domain argumentation into a 1-dimensional scalar position $[-1.0, +1.0]$. Nuanced tactical qualifications or conditional agreements are necessarily compressed.
2. **Statistical Power:** Deliberations of 3 to 5 rounds yield limited time-series observations per agent dyad. Correlation coefficients ($r$) require cautious interpretation and reflect directional association rather than causal proof.
3. **Alignment vs. Correctness:** Group agreement measures internal consensus among the participating agent personas; it does not measure or guarantee factual truth or objective football correctness.
4. **Missing Data Handling:** Incomplete rounds, unclassified stances, or invariant trajectories are retained as explicit `null` / `None` values to guarantee transparency and eliminate synthetic score fabrication.

---
*Report automatically generated by Week 4 Discussion Analytics Engine. Discussion ID: `demo_repro_run`.*
