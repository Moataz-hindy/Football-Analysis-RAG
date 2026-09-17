# Sentiment and analytics integration — 15 September 2026

This update selectively integrates Nada's sentiment commits through `3a004d1` on `main` and Moataz's analytics/tool work through `e8c1fe7` on `agent-graph`. It preserves the reliability behavior of `mixed-work`; it does not merge the older failure handlers from either source branch. The source branches and Hatem's original checkout remain untouched. No local Gemini embedding code or artifacts are included.

## Sentiment

VADER scores the final response after any duplicate-response retry, without another API call. The trailing SOURCES USED section is excluded. `sentiment_score` and `sentiment_label` travel through AgentResponse, runtime DiscussionMessage, checkpoint JSON, and the persisted DiscussionMessage serializer/loader. Legacy records without the fields load with null values.

Sentiment measures emotional tone, not agreement with the topic. Quoted material in the reasoning may still affect the score, and domain-specific language needs human interpretation. The configured scorer is VADER compound, with positive >= 0.05 and negative <= -0.05.

## Analytics

The package consumes saved discussion records and provides opinion trajectories, pairwise agreement, and observed convergence after directed messages. Results are explicitly experimental.

Install the updated regular dependencies, then run locally from the repository root:

```bash
python -m pip install -r requirements.txt
python -m pytest tests -q
python -m src.analytics.run_analytics --input outputs/YOUR_DISCUSSION_ID.json --output outputs/analytics-YOUR_DISCUSSION_ID.json
```

Replace YOUR_DISCUSSION_ID with an existing saved run ID. The input record is not modified. The output path must differ from the input path. Results include scored/observed/expected snapshot coverage and the original run status, so partial or sparsely scored discussions are visible.

### Default: conservative self-report rules

No API or embedding model is initialized, even if LLM_API_KEY exists. Rules recognize explicit agree/support/oppose statements and simple negation. They do not infer a stance from emotional words, team names, or sporting-merit language. Unclassified text is null, not a neutral zero. A neutral/undecided self-report is zero.

Rules are a diagnostic baseline: agreement with a peer may not be agreement with the topic, complex negation remains difficult, and quoted text can mislead them. Manual review or an explicitly configured model is needed for topic-aware analysis. The method and classification status are recorded for every point. The previous text-parser change flag is retained for comparison but cannot freeze new scores. Missing rounds do not acquire invented deltas.

### Optional LLM scoring

Extra requests require the explicit `--use-llm` flag and two opposing statements:

```bash
python -m src.analytics.run_analytics \
  --input outputs/YOUR_DISCUSSION_ID.json \
  --output outputs/analytics-YOUR_DISCUSSION_ID.json \
  --use-llm \
  --positive-pole "Japan's low block was tactically effective" \
  --negative-pole "Japan's low block was tactically ineffective"
```

This uses the existing configured chat provider. Confirm its free allowance before opting in. Requests contain at most eight snapshots per batch. Invalid, missing, duplicate, unknown, non-finite, or out-of-range returned scores raise errors rather than silently switching to rules. A valid null score means the model could not classify that snapshot. Successful model output is still an estimate, not a measured ground truth.

### Optional local semantic scoring

`--use-embeddings` also requires explicit positive/negative poles. It uses a separately installed sentence-transformers package and an already cached all-MiniLM-L6-v2 model. It does not download weights during analytics, and missing packages/weights remain explicit failures. Optional packages are listed in requirements-analytics-embeddings.txt; they are not needed for normal operation or tests.

The score is half the difference between cosine similarities to the positive and negative poles. There is no arbitrary fivefold amplification. Semantic similarity can struggle with negation, so this remains an experimental comparison method. No poles are guessed by splitting a match title on "vs". No silent fallback mixes its scores with rules or LLM results.

### Agreement

Agreement is `1 - mean_pairwise_distance / 2`. Values are comparable only when stance scoring uses the same method and poles. Zero/one-agent rounds have unavailable agreement. Empty data is not perfect consensus. A six-agent group evenly split between -1 and +1 scores 0.4; zero is not the general minimum for larger groups. Trends are not classified when the measured participant cohort changes.

### Influence

Only recorded sender/recipient links are used. A message in round r is associated with the recipient's change at r+1. Pull is the reduction in distance to the sender's earlier stance, clipped to [-1, 1]. Moving past the sender and farther away gives negative pull. Missing routes/stances return insufficient_data; observed recipients with no movement return zero_movement with no numeric influence score. Neither case enters the ranking.

These are associations. Shared evidence and multiple senders can explain the same change; the system does not claim causal persuasion or exclusive attribution to one agent.

## Other integration changes

Search tools accept common argument aliases while preserving source metadata and raised failures. Web searches deduplicate queries and run at most two per invocation. Persistence retains query aliases in evidence records. Discussion prompts allow evidence-based concessions without demanding consensus. Saved retrieval configuration now correctly says k6.

## Verification

202 tests passed with no skips in an isolated environment with live network connections blocked during tests. The four tests that depended on uncommitted saved runs were replaced with deterministic discussion-record fixtures. A committed offline integration test independently runs all 24 messages, saves/reloads sentiment, and runs the analytics pipeline. Other tests cover negation, missing data, overshoot, absent message routes, explicit model opt-in, invalid model scores, and legacy record loading.

No live model, web-search, or database requests were made for validation. Existing Week 1 corpus/model provenance and live retrieval quality still need the separate acceptance checks described in the earlier integration notes.
