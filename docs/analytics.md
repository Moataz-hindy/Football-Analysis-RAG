# Analytics

How the platform turns a saved discussion (`outputs/{discussion_id}.json`) into
stance trajectories, agreement, influence, sentiment, charts and reports.

Code: `src/analytics/`, `src/visualization/`, `src/reporting/`.
Every result is **experimental** and says so in its `metadata`.

---

## 1. Pipeline at a glance

```text
outputs/{discussion_id}.json  (saved transcript, never modified)
        │
        ▼
 Stance scoring (task 1) ──► Agreement (task 2)
        │                └─► Influence (task 3: correlation + distance reduction)
        │                └─► Counterfactual influence (optional, LLM)
        ▼
 Sentiment (task 4, VADER — independent of stance)
        │
        ▼
 Analytics JSON  ·  PNG charts  ·  Markdown report  ·  optional LLM extras
```

| Module | Responsibility |
|---|---|
| `stance.py` | Scores every opinion snapshot on a −1…+1 scale; builds per-agent trajectories |
| `agreement.py` | Pairwise agreement per round and the overall trend |
| `correlation_influence.py` | Default influence metric (Pearson association) |
| `influence.py` | Distance-reduction ("pull") influence, kept for comparison |
| `causal_influence.py` | Optional counterfactual ablation via the LLM |
| `sentiment.py` | Aggregates the per-message VADER scores |
| `key_insights.py` | Optional LLM summary of evidence-based disagreements |
| `synthesis.py`, `advisor.py` | LLM executive narrative and final decision (served by the API) |
| `engine.py` | `AnalyticsEngine` used by the API service |
| `run_analytics.py` | Command-line entry point |

---

## 2. Stance scoring (task 1)

Each snapshot `S(a, r)` — agent `a` after round `r` — is a number in [−1, +1]
relative to two explicit statements, the **positive pole** (+1) and the
**negative pole** (−1). Round-to-round change is `ΔS(a, r) = S(a, r) − S(a, r−1)`;
round 0 has no change.

Three scoring methods exist. Exactly one is used per run and it is recorded in
`metadata.scoring_method`.

| Method | Flag | Needs | Behaviour |
|---|---|---|---|
| `self_report_rules` | *(default)* / `--no-llm` | nothing | Recognises explicit *agree / support / oppose / reject…* statements with simple negation. Everything else stays `null`. Makes no network calls, even if an API key exists. |
| `llm` | `--use-llm` | LLM provider, both poles | Scores snapshots in batches of up to 8. Invalid, duplicate or out-of-range answers raise an error rather than falling back silently. |
| `embedding_projection` | `--use-embeddings` | `sentence-transformers` + a **locally cached** `all-MiniLM-L6-v2`, both poles | Score = (cos(text, +pole) − cos(text, −pole)) / 2. Never downloads weights. |

Rules that apply to every method:

- An unclassifiable stance is `null`, **not** 0. A neutral self-report is 0.
- Missing rounds do not get invented deltas, and charts break the line there.
- `--scores-from FILE` reuses scores from an earlier analytics file (no model
  calls). It cannot be combined with a scoring flag or poles, because saved
  scores keep their original method.

**Scoring in the web app.** The API (`src/api/services/analytics_service.py`)
uses `llm` scoring. It takes the poles from the debate camps when they exist,
otherwise from a "`A` vs `B`" topic, otherwise
`Affirming: <topic>` / `Contesting: <topic>`. If the LLM call fails it retries
with `embedding_projection`. A discussion that still cannot be scored is
returned unscored rather than filled with guesses.

---

## 3. Agreement (task 2)

For every pair of agents with a score in round `r`:

```text
A(u, v, r) = 1 − |S(u, r) − S(v, r)| / 2          (1 = identical, 0 = opposite poles)
A(r)       = mean of A(u, v, r) over all pairs
ΔA         = A(last measured round) − A(first measured round)
```

| ΔA | `overall_trend` |
|---|---|
| ≥ +0.05 | `Converging` |
| ≤ −0.05 | `Diverging` |
| otherwise | `Stable` |
| fewer than two measured rounds, or the set of scored agents differs between measured rounds | `Insufficient Comparable Data` |
| no round has an agreement value | `Insufficient Data` |

Notes:
- Rounds with 0 or 1 scored agent have no agreement value; empty data is not
  "perfect consensus".
- For more than two agents, 0 is not the floor: six agents split evenly
  between −1 and +1 score 0.4.
- Agreement measures alignment between personas, not whether they are right.

---

## 4. Influence (task 3)

### 4.1 Correlation influence (default, `task3_agent_influence`)

For every recorded route sender → recipient in round `r` where all three
scores exist, the pipeline collects one observation:

```text
x = S(sender, r) − S(recipient, r)          # how far the sender was from the recipient
y = S(recipient, r+1) − S(recipient, r)     # how the recipient then moved
influence(sender) = Pearson(x, y) over that sender's observations
```

A positive score means recipients tended to move *toward* this sender.

| `status` | Meaning |
|---|---|
| `computed` | Score available |
| `insufficient_data` | Fewer than 3 observations or fewer than 2 distinct rounds |
| `constant_signal` | No variation, so the correlation is undefined (`null`) |

`metadata.influence_method` is `pearson_stance_gap_vs_next_round_change`.

### 4.2 Distance-reduction influence (`distance_reduction_influence`)

The earlier metric, kept alongside for comparison: the "pull" of a message is
how much the recipient's distance to the sender's previous stance shrank,
clipped to [−1, 1]. Moving past or away from the sender gives negative pull.
No route or no stance gives `insufficient_data`; observed recipients that did
not move give `zero_movement` with no score.

### 4.3 Counterfactual influence (optional, `task3_causal_influence`)

With `--counterfactual-ablation` the LLM estimates what each recipient's
next-round stance would have been without a given sender's message:

```text
τ(A → B, r) = | S_factual(B, r+1) − S_counterfactual(B, r+1, without A) |
```

This is a model's estimate of a counterfactual, not an experiment, and it
costs extra LLM requests. The API exposes it as
`POST /discussions/{id}/causal-analysis`.

### 4.4 What influence scores do and do not show

All three are **associations over a handful of rounds**. They share agents and
rounds, inherit every stance-scoring error, and cannot separate one sender's
effect from shared evidence or other senders. Each result carries a
`limitations` list; read it before quoting a number.

---

## 5. Sentiment (task 4)

VADER scores each final agent message once, when it is created (the trailing
`SOURCES USED` block is excluded). Compound ≥ 0.05 is positive, ≤ −0.05 is
negative, otherwise neutral. `task4_sentiment` aggregates by agent and round.

Sentiment is **emotional tone, not agreement**. It is never substituted for a
missing stance.

---

## 6. Command-line usage

Run from the repository root. `--input` must be a saved discussion.
**Without `--output`, nothing is written:** the command only prints a
summary.

```bash
# Default: local rules only, no network calls
python -m src.analytics.run_analytics \
  --input outputs/DISCUSSION_ID.json \
  --output outputs/analytics-DISCUSSION_ID.json

# LLM scoring (poles are required), plus charts and a Markdown report
python -m src.analytics.run_analytics \
  --input outputs/DISCUSSION_ID.json \
  --output outputs/analytics-DISCUSSION_ID.json \
  --use-llm \
  --positive-pole "Japan's low block was tactically effective" \
  --negative-pole "Japan's low block was tactically ineffective" \
  --generate-charts --generate-report --reports-dir reports

# Reuse saved scores: no model calls
python -m src.analytics.run_analytics \
  --input outputs/DISCUSSION_ID.json \
  --scores-from outputs/analytics-DISCUSSION_ID.json \
  --output outputs/analytics-DISCUSSION_ID-v2.json
```

| Flag | Purpose |
|---|---|
| `--input / -i / --discussion` | Discussion JSON (required) |
| `--output / -o` | Where to save the analytics JSON; must differ from every input |
| `--no-llm` · `--use-llm` · `--use-embeddings` · `--scores-from` | Scoring method (mutually exclusive; default is rules) |
| `--positive-pole`, `--negative-pole` | Required by `--use-llm` and `--use-embeddings` |
| `--generate-charts` (alias `--visualize`) | Trajectory chart and interaction graph |
| `--generate-report` (alias `--report`) | Markdown report |
| `--reports-dir` | Where charts and the report go (default `reports/`) |
| `--counterfactual-ablation` | Add `task3_causal_influence` (LLM) |
| `--key-insights` | Add LLM key insights (not allowed with `--no-llm`) |

Standalone tools:

```bash
python -m src.visualization.opinion_trajectory --input outputs/DISCUSSION_ID.json --output-dir reports
python -m src.visualization.interaction_graph  --input outputs/DISCUSSION_ID.json --output-dir reports
python -m src.reporting.report --analytics outputs/analytics-DISCUSSION_ID.json --output reports/report.md
python -m src.analytics.correlation_influence --discussion outputs/DISCUSSION_ID.json \
  --analytics outputs/analytics-DISCUSSION_ID.json --output outputs/influence-DISCUSSION_ID.json
```

The trajectory tool also accepts `--scores-from` and `--filename`; the graph
tool accepts `--filename` and `--title`.

Optional embedding dependencies (only for `--use-embeddings`):

```bash
pip install -r requirements-analytics-embeddings.txt
```

---

## 7. Outputs

| Artifact | Location |
|---|---|
| Analytics JSON (CLI) | the `--output` path you pass |
| Analytics JSON (API cache) | `reports/api_cache/{discussion_id}_analytics.json` |
| Synthesis / advisor (API cache) | `reports/api_cache/{discussion_id}_synthesis.json`, `…_advisor.json` |
| Markdown report | `{reports-dir}/discussion_report_{discussion_id}.md` |
| Charts | `{reports-dir}/` (PNG, paths recorded under `visualizations`) |

Top-level keys of the analytics JSON (`schema_version: 2`):

```text
discussion_id, topic
metadata                      scoring method, snapshot coverage, source SHA-256, warnings, limitations
task1_opinion_trajectories    per-agent points: round_num, stance_value, opinion_change, stance_text
task2_discussion_agreement    round_agreements, mean_discussion_agreement, overall_trend
task3_agent_influence         correlation influence (section 4.1)
distance_reduction_influence  pull-based influence (section 4.2)
task3_causal_influence        only with --counterfactual-ablation
task4_sentiment               per-message and aggregated VADER scores
key_insights                  status "not_requested" unless --key-insights
visualizations, report_path   only when charts/report were generated
```

`metadata.scored_snapshots / observed_snapshots / expected_snapshots` shows how
much of the discussion could actually be scored. Check it before reading any
trend.

---

## 8. Limitations

- One number per agent per round compresses long, conditional arguments.
- Three to five rounds give very few observations, so no result is statistically
  significant.
- Scores are only comparable between runs that used the same method **and** the
  same poles.
- The rule-based default is a conservative baseline: agreeing with a peer is not
  the same as agreeing with the topic, and quoted text can mislead it.
