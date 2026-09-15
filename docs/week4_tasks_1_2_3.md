# Week 4: Tasks 1, 2 & 3 — Opinion Dynamics, Agreement & Influence

This document defines the mathematical models, schemas, and architecture for **Tasks 1, 2, and 3** of the Week 4 Analytics Layer:
1. **Task 1**: Per-Agent Opinion Change Across Rounds
2. **Task 2**: Per-Round Agreement / Disagreement Metric
3. **Task 3**: Per-Agent Correlation & Network Influence Scores

---

## 1. Architectural Role & Pipeline

```text
       Week 3 Discussion Output (outputs/*.json)
                         │
                         ▼
        ┌──────────────────────────────────┐
        │ Task 1: Stance Extraction        │ ──► Numeric Stances: S(agent, round)
        │ (src/analytics/stance.py)        │ ──► Opinion Changes: ΔS(agent, round)
        └────────────────┬─────────────────┘
                         │
         ┌───────────────┴───────────────┐
         ▼                               ▼
┌───────────────────────────────┐ ┌───────────────────────────────────┐
│ Task 2: Agreement Metric      │ │ Task 3: Influence Scoring         │
│ (src/analytics/agreement.py)  │ │ (src/analytics/influence.py)      │
│ ──► One score A(r) per round  │ │ ──► Influence score I(agent)      │
└───────────────────────────────┘ └───────────────────────────────────┘
```

---

## 2. Task 1: Per-Agent Opinion Change Across Rounds (Universal Dual-Engine)

### Objective
Convert each agent's textual `OpinionSnapshot` from Week 3 into a standardized, numeric stance series $S_{a, r}$ and compute round-to-round movement $\Delta S_{a, r}$, engineered to be **universal for any debate topic**.

### Universal Scale Definition
For any given debate topic and its core proposition, stance value $S \in [-1.0, 1.0]$:
- **$+1.0$ (Strong Affirmation / Support)**: Complete agreement with the central topic proposition (e.g. sporting merit, rule change approval, retaining a manager, affirmative thesis).
- **$0.0$ (Neutral / Balanced / Agnostic)**: Balanced 50/50 attribution, high variance / statistical outlier, uncommitted, or agnostic position.
- **$-1.0$ (Strong Opposition / Rejection)**: Complete disagreement with the central proposition (e.g. officiating robbery, rule rejection, sacking a manager, counter-thesis).

### Dual-Engine Universal Scoring Architecture

To guarantee accuracy on arbitrary topics without domain-specific hardcoding:

1. **Primary Engine: Universal Batched LLM Evaluator (`score_snapshots_with_llm`)**:
   - Uses `OpenAICompatibleLLM` (Gemini Flash Lite, Groq, or OpenAI).
   - Ingests the discussion's actual `topic` and passes all agent snapshots across all rounds in a **single batched prompt**.
   - Output: Strict JSON array `[{"agent_id": str, "round_num": int, "stance_value": float}]`.
   - **Performance**: Takes only ~1.5 seconds and ~500 tokens for an entire 4-round, 6-agent debate (24 snapshots) while achieving deep semantic comprehension of any topic (football, ethics, technology, governance).

2. **Secondary Engine: Universal Local Semantic Polarity Fallback (`extract_numeric_stance`)**:
   - Used when offline, during automated `pytest` test suites, or when no LLM API key is present.
   - Evaluates affirmative semantic signals (*agree, concur, support, affirm, justified, legitimate, deserved, correct, valid, merit*) vs. opposing signals (*disagree, oppose, refute, reject, unjust, undeserved, robbed, flawed, corrupt, tainted, failure*).
   - **Persistence Anchor**: If `changed_from_previous == False` or an agent explicitly maintains position, the engine anchors the stance to prevent opponent quotation or noise from drifting the score.

### Opinion Trajectory & Velocity Formula
For agent $a$ in round $r$:
$$\text{Trajectory}_a = \left( S_{a, 0}, S_{a, 1}, S_{a, 2}, \dots, S_{a, R} \right)$$
$$\Delta S_{a, r} = \begin{cases} \text{null} & \text{if } r = 0 \text{ (baseline)} \\ S_{a, r} - S_{a, r-1} & \text{if } r \ge 1 \end{cases}$$

- $\Delta S > 0$: Shifted toward topic affirmation / proposition support.
- $\Delta S < 0$: Shifted toward counter-proposition / opposition.
- $\Delta S = 0$: Maintained position without ideological drift.

### Output Schema
```python
class AgentStancePoint(BaseModel):
    agent_id: str
    round_num: int
    stance_value: float  # [-1.0, 1.0]
    opinion_change: float | None  # Delta from previous round
    stance_text: str
    changed_from_previous: bool
    change_reason: str

class OpinionTrajectoryResult(BaseModel):
    discussion_id: str
    topic: str
    total_rounds: int
    agent_ids: list[str]
    trajectories: dict[str, list[AgentStancePoint]]  # agent_id -> points across rounds
```

---

## 3. Task 2: Per-Round Agreement / Disagreement Metric

### Objective
Measure how unified or polarized the studio panel is during each round $r$, outputting exactly one scalar score $A_r \in [0.0, 1.0]$ per round.

### Mathematical Formulation
For a discussion round $r$ with $N$ active agents:
1. **Pairwise Stance Distance**:
   For each pair of distinct agents $(i, j)$ where $i < j$:
   $$D_{ij, r} = |S_{i, r} - S_{j, r}|$$

2. **Mean Pairwise Dispersion**:
   $$\bar{D}_r = \frac{1}{\binom{N}{2}} \sum_{i < j} |S_{i, r} - S_{j, r}|$$

3. **Normalized Agreement Score ($A_r$)**:
   Since stances are bounded in $[-1.0, 1.0]$, the maximum possible pairwise distance is $D_{\max} = 2.0$:
   $$A_r = 1.0 - \frac{\bar{D}_r}{2.0}$$

### Score Interpretation
- **$A_r = 1.0$ (Complete Consensus)**: All 6 agents hold identical stances ($\bar{D}_r = 0.0$).
- **$A_r \approx 0.70$–$0.85$ (High Alignment)**: Strong convergence with minor peripheral dissent.
- **$A_r \approx 0.40$–$0.60$ (Moderate Debate)**: Realistic television studio panel with healthy divergence.
- **$A_r = 0.0$ (Maximum Polarization)**: Half the panel at $+1.0$ and half at $-1.0$.

### Output Schema
```python
class RoundAgreement(BaseModel):
    round_num: int
    agreement_score: float  # [0.0, 1.0]
    mean_distance: float    # Dispersion [0.0, 2.0]
    variance: float         # Stance variance
    agent_count: int
    interpretation: str     # e.g. "Unanimous Consensus", "Moderate Debate", "Extreme Polarization"
    pairwise_distances: dict[str, float]  # Detailed breakdown for every agent pair

class DiscussionAgreementResult(BaseModel):
    discussion_id: str
    total_rounds: int
    round_agreements: list[RoundAgreement]
    mean_discussion_agreement: float
    overall_trend: str      # "Converging", "Diverging", or "Stable"
```

---

## 4. Task 3: Per-Agent Influence Scores

### Objective
Estimate how much each agent's arguments moved the opinions of other agents across rounds using message routing and stance change correlations (network DeGroot influence modeling).

### Mathematical Formulation
Let $M_{a \to b, r-1}$ indicate that agent $a$ sent a message to agent $b$ in round $r-1$.
In round $r$, agent $b$ updates its stance by $\Delta S_{b, r}$.

1. **Directional Convergence Pull**:
   Did agent $b$ move toward agent $a$'s previous stance $S_{a, r-1}$?
   $$\text{Target Direction} = \text{sign}(S_{a, r-1} - S_{b, r-1})$$
   $$\text{Pull}_{a \to b, r} = \Delta S_{b, r} \times \text{Target Direction}$$
   - If $\text{Pull} > 0$: Agent $b$ moved closer to agent $a$ after receiving $a$'s message.
   - If $\text{Pull} < 0$: Agent $b$ was pushed further away (backfire / reactance).
   - If $\text{Pull} = 0$: No movement.

2. **Per-Agent Influence Aggregation**:
   Sum the positive convergence pulls across all recipients and rounds, normalized by recipient opportunities:
   $$I_a = \frac{\sum_{r=1}^{R} \sum_{b \in \text{Recipients}(a)} \max(0, \text{Pull}_{a \to b, r})}{\sum_{r=1}^{R} |\text{Recipients}(a)|}$$

3. **Handling Zero Stance Movement / Insufficient Data**:
   As required by Week 4 Section 16, when a discussion exhibits zero opinion change across all agents (e.g. all agents maintain their stances with $\Delta S = 0$):
   - The metric explicitly returns `status: "insufficient_variance"` or `status: "rigid_consensus"` with score `0.0` or `null`, rather than emitting confabulated numbers.

### Output Schema
```python
class AgentInfluence(BaseModel):
    agent_id: str
    influence_score: float | None  # [-1.0, 1.0] or None if zero movement
    status: str                    # "valid", "zero_movement", or "insufficient_data"
    total_pull: float
    interaction_count: int
    recipient_pulls: dict[str, float]  # Detailed pull per recipient
    rationale: str

class DiscussionInfluenceResult(BaseModel):
    discussion_id: str
    agent_influences: dict[str, AgentInfluence]
    top_influencer: str | None
    discussion_dynamic: str        # e.g. "Active Persuasion & Convergence", "Rigid Deliberation"
    causation_disclaimer: str      # Statistical association disclaimer
```

---

## 5. Verification & Testing Strategy

Each task will have dedicated automated unit tests:
1. `tests/test_analytics_stance.py`:
   - Validates numeric scale bounds $[-1.0, 1.0]$.
   - Validates delta calculations: $\Delta S_{a, 0} = \text{None}$, $\Delta S_{a, 1} = S_{a, 1} - S_{a, 0}$.
   - Tests on real discussion output `outputs/egy-arg7.json`.
2. `tests/test_analytics_agreement.py`:
   - Validates identical stances yield $A_r = 1.0$.
   - Validates opposing poles yield $A_r = 0.0$.
   - Validates exactly one agreement score per round.
3. `tests/test_analytics_influence.py`:
   - Validates that when Agent B moves toward Agent A, Agent A receives positive influence.
   - Validates explicit handling of zero-movement debates.
