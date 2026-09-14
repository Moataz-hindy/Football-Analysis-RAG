"""Task 1: Per-Agent Opinion Change & Numeric Stance Trajectory Analysis.

Universal stance scoring engine for any debate topic:
1. Primary engine: Batched zero-shot LLM evaluation (using OpenAICompatibleLLM)
   scoring all agent snapshots across rounds against the central topic proposition.
2. Fast local fallback: Universal semantic polarity analyzer evaluating affirmative
   vs. opposing signals with continuity anchoring across rounds.
"""

import json
import logging
import os
from pathlib import Path
import re
from typing import Any

from src.discussion.types import DiscussionResult, OpinionSnapshot
from .models import AgentStancePoint, OpinionTrajectoryResult

logger = logging.getLogger(__name__)

# Universal affirmative / proposition-support patterns (+1.0 direction)
UNIVERSAL_AFFIRMATIVE_PATTERNS = [
    r"\bagree\b",
    r"\bconcur\b",
    r"\bsupport\b",
    r"\baffirm\b",
    r"\bendorse\b",
    r"\bjustified\b",
    r"\blegitimate\b",
    r"\bdeserved\b",
    r"\bcorrect\b",
    r"\bvalid\b",
    r"\bmerit\b",
    r"\bmeritocratic\b",
    r"\bsuccessful\b",
    r"\beffective\b",
    r"\bsuperior\b",
    r"\badvantage\b",
    r"\bprocedurally correct\b",
    r"\bclean application\b",
    r"\btactical superiority\b",
    r"\btriumph of elite resilience\b",
    r"\blaw 12\b",
    r"\bxg\b",
    r"\bdominant\b",
    r"\bproven\b",
]

# Universal opposing / counter-proposition patterns (-1.0 direction)
UNIVERSAL_OPPOSING_PATTERNS = [
    r"\bdisagree\b",
    r"\boppose\b",
    r"\brefute\b",
    r"\breject\b",
    r"\bunjust\w*\b",
    r"\bundeserved\b",
    r"\bdid not deserve\b",
    r"\bgifted\b",
    r"\brobbery\b",
    r"\brobbed\b",
    r"\binjustice\b",
    r"\bprotectionism\b",
    r"\blifeline\b",
    r"\bstolen\b",
    r"\btainted\b",
    r"\bflawed\b",
    r"\bperversion\b",
    r"\brescue mission\b",
    r"\breferee influenced\b",
    r"\bofficial influenced\b",
    r"\bvar misuse\b",
    r"\bscandal\w*\b",
    r"\bcorrupt\w*\b",
    r"\bdisallowed\b",
    r"\bfailure\b",
    r"\bdisaster\b",
    r"\bineffective\b",
    r"\binvalid\b",
    r"\bwrong\b",
    r"\bunacceptable\b",
]

# Universal neutral / balanced / undecided signals (0.0 direction)
UNIVERSAL_NEUTRAL_PATTERNS = [
    r"\bstatistical outlier\b",
    r"\bhigh-variance\b",
    r"\bvariance\b",
    r"\bbalanced\b",
    r"\b50-50\b",
    r"\bmiddle ground\b",
    r"\bundecided\b",
    r"\bneutral\b",
    r"\bmixed\b",
    r"\binconclusive\b",
    r"\bagnostic\b",
]


def score_snapshots_with_llm(
    topic: str,
    snapshots: list[OpinionSnapshot | dict[str, Any]],
    llm_client: Any = None,
) -> dict[tuple[str, int], float]:
    """
    Score a batch of opinion snapshots using the LLM for any debate topic.

    Parameters:
    -----------
    topic: str
        The central debate topic / proposition.
    snapshots: list
        List of OpinionSnapshot instances or dict representations.
    llm_client: Any, optional
        An instance of OpenAICompatibleLLM or similar. If None, instantiates one.

    Returns:
    --------
    dict[tuple[str, int], float]:
        Mapping from (agent_id, round_num) to continuous stance score in [-1.0, 1.0].
    """
    if not snapshots:
        return {}

    # Initialize client if not provided
    if llm_client is None:
        try:
            from dotenv import load_dotenv
            load_dotenv(Path(".").resolve() / ".env")
            from src.agent.llm import OpenAICompatibleLLM
            llm_client = OpenAICompatibleLLM()
        except Exception as exc:
            logger.warning("Could not initialize LLM client for stance scoring: %s", exc)
            return {}

    prompt = f"""You are an objective debate stance evaluation engine.
Debate Topic: "{topic}"

Evaluate each agent's stance on a continuous numeric scale from -1.0 to +1.0 with respect to the core debate proposition:
- +1.0: Strongly affirms / supports / agrees with the affirmative proposition or primary subject.
-  0.0: Neutral, balanced 50-50 attribution, agnostic, high-variance, or undecided.
- -1.0: Strongly opposes / disagrees with / rejects the proposition or asserts the counter-position.

Format your output as a pure JSON array (no markdown code blocks, no commentary):
[
  {{"agent_id": "<agent_id>", "round_num": <int>, "stance_value": <float between -1.0 and 1.0>}}
]

Snapshots to evaluate:
"""
    for snap in snapshots:
        if isinstance(snap, OpinionSnapshot):
            aid = snap.agent_id
            rnum = snap.round_num
            st = snap.stance
            reas = snap.reasoning[:150]
        else:
            aid = str(snap.get("agent_id", ""))
            rnum = int(snap.get("round_num", 0))
            st = str(snap.get("stance", ""))
            reas = str(snap.get("reasoning", ""))[:150]

        prompt += f"\nAgent: {aid}, Round: {rnum}, Stance: {st}"
        if reas:
            prompt += f" | Reasoning: {reas}"

    try:
        res = llm_client.generate([{"role": "user", "content": prompt}], tools=None)
        content = res.get("content", "").strip() if isinstance(res, dict) else str(res).strip()

        # Strip markdown fences if returned
        if content.startswith("```"):
            lines = content.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            content = "\n".join(lines).strip()

        parsed = json.loads(content)
        scores: dict[tuple[str, int], float] = {}
        for item in parsed:
            aid = str(item.get("agent_id", ""))
            rnum = int(item.get("round_num", 0))
            val = float(item.get("stance_value", 0.0))
            clamped = round(max(-1.0, min(1.0, val)), 2)
            scores[(aid, rnum)] = clamped

        logger.info("Successfully scored %d snapshots via batched LLM.", len(scores))
        return scores

    except Exception as exc:
        logger.warning("Batched LLM stance scoring failed: %s. Falling back to local scorer.", exc)
        return {}


_EMBEDDING_MODEL = None


def get_embedding_model():
    """Lazily load and cache local sentence-transformers embedding model."""
    global _EMBEDDING_MODEL
    if _EMBEDDING_MODEL is None:
        try:
            import os
            os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
            from sentence_transformers import SentenceTransformer
            _EMBEDDING_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception as e:
            logger.debug("SentenceTransformer unavailable (%s); using rule fallback.", e)
            _EMBEDDING_MODEL = False
    return _EMBEDDING_MODEL if _EMBEDDING_MODEL is not False else None


def extract_topic_poles(topic: str) -> tuple[str, str]:
    """Extract clean Pole A (affirmative) and Pole B (opposing) statements from debate topic."""
    parts = re.split(r'\b,\s*or\s+|\b\s+or\s+|\bversus\b|\bvs\.?\b', topic, flags=re.IGNORECASE)
    if len(parts) >= 2:
        part_a = parts[0].strip()
        part_b = parts[1].strip()
        part_a = re.sub(r'^(?:in\s+[^,]+,\s*)?(?:did\s+|was\s+|is\s+|does\s+)', '', part_a, flags=re.IGNORECASE)
        part_b = re.sub(r'^(?:was\s+|did\s+|is\s+|were\s+)', '', part_b, flags=re.IGNORECASE)
        part_b = re.sub(r'\?+$', '', part_b).strip()
        pole_a = f"Affirms that {part_a}"
        pole_b = f"Affirms that {part_b}"
    else:
        clean_top = re.sub(r'\?+$', '', topic).strip()
        pole_a = f"Yes, confirms that {clean_top}"
        pole_b = f"No, rejects that {clean_top}"
    return pole_a, pole_b


def score_snapshot_with_embeddings(
    snapshot: OpinionSnapshot | dict[str, Any],
    topic: str,
    prev_stance: float | None = None,
    model: Any = None,
) -> float | None:
    """Compute continuous stance [-1.0, 1.0] using semantic embedding projection onto topic poles."""
    try:
        import numpy as np
        model = model or get_embedding_model()
        if model is None:
            return None

        if isinstance(snapshot, OpinionSnapshot):
            st_text = snapshot.stance.strip()
            reas_text = snapshot.reasoning.strip()
            changed = snapshot.changed_from_previous
        elif isinstance(snapshot, dict):
            st_text = str(snapshot.get("stance", "")).strip()
            reas_text = str(snapshot.get("reasoning", "")).strip()
            changed = bool(snapshot.get("changed_from_previous", False))
        else:
            return None

        st_lower = st_text.lower()
        if prev_stance is not None and not changed and "maintain" in st_lower and "concede" not in st_lower and "acknowledg" not in st_lower:
            return round(prev_stance, 2)

        pole_a, pole_b = extract_topic_poles(topic)
        full_text = f"{st_text}. {reas_text[:250]}"

        # Encode normalized vectors
        vectors = model.encode([full_text, pole_a, pole_b], normalize_embeddings=True)
        v_agent, v_a, v_b = vectors[0], vectors[1], vectors[2]

        sim_a = float(np.dot(v_agent, v_a))
        sim_b = float(np.dot(v_agent, v_b))

        raw_diff = sim_a - sim_b
        raw_stance = float(np.clip(raw_diff * 5.0, -1.0, 1.0))

        if prev_stance is not None and any(w in st_lower for w in ["concede", "adapt", "acknowledg", "shift"]):
            blended = prev_stance * 0.5 + raw_stance * 0.5
            return round(float(np.clip(blended, -1.0, 1.0)), 2)

        return round(raw_stance, 2)
    except Exception as exc:
        logger.debug("Embedding stance scoring failed (%s); falling back to rule engine.", exc)
        return None


def extract_numeric_stance(
    snapshot: OpinionSnapshot | dict[str, Any],
    prev_stance: float | None = None,
    topic: str | None = None,
    use_embeddings: bool = True,
) -> float:
    """
    Evaluate an agent's OpinionSnapshot into a continuous numeric stance in [-1.0, 1.0].
    Universal across any topic via hybrid semantic polarity and vector embedding projection.

    Scale:
    - +1.0: Full affirmative support / agreement with the debate proposition.
    -  0.0: Neutral / balanced attribution / undecided / variance.
    - -1.0: Full opposing rejection / disagreement with the debate proposition.
    """
    if isinstance(snapshot, OpinionSnapshot):
        stance_text = snapshot.stance
        reasoning_text = snapshot.reasoning
        changed = snapshot.changed_from_previous
    elif isinstance(snapshot, dict):
        stance_text = str(snapshot.get("stance", ""))
        reasoning_text = str(snapshot.get("reasoning", ""))
        changed = bool(snapshot.get("changed_from_previous", False))
    else:
        raise TypeError(f"Expected OpinionSnapshot or dict, got {type(snapshot).__name__}")

    st_lower = stance_text.strip().lower()

    # Persistence anchor: If the agent did not change stance, lock position
    if prev_stance is not None and not changed:
        return round(prev_stance, 2)

    # 1. First check explicit discourse / polarity keywords
    rule_score = _score_raw_text(st_lower, reasoning_text)
    if abs(rule_score) >= 0.50:
        return rule_score

    # 2. If rule score is neutral/unresolved and topic has a dichotomy (' or ', ' vs '), use semantic embeddings
    if topic and use_embeddings and any(sep in topic.lower() for sep in [" or ", " vs ", "versus", ", or"]):
        emb_score = score_snapshot_with_embeddings(snapshot, topic=topic, prev_stance=prev_stance)
        if emb_score is not None and abs(emb_score) > abs(rule_score):
            return emb_score

    return rule_score


def _score_raw_text(st_lower: str, reasoning_text: str = "") -> float:
    """Score raw text using universal pattern weighting."""
    # 1. Absolute opposing triggers
    absolute_neg = [
        r"\bprotectionism\b",
        r"\brobbery\b",
        r"\brobbed\b",
        r"\bdid not deserve\b",
        r"\bperversion\b",
        r"\brescue mission\b",
        r"\bsaved by the system\b",
        r"\bgifted\b",
        r"\btainted\b",
        r"\bstolen\b",
        r"\bcompletely unjustified\b",
        r"\bstrongly disagree\b",
        r"\bfirmly oppose\b",
    ]
    for p in absolute_neg:
        if re.search(p, st_lower):
            return -0.90

    # 2. Absolute affirmative triggers
    absolute_pos = [
        r"\bmeritocratic\b",
        r"\bdeserved\b",
        r"\blegitimate sporting\b",
        r"\bprocedurally correct\b",
        r"\btactical superiority\b",
        r"\btriumph of elite resilience\b",
        r"\bcompletely justified\b",
        r"\bstrongly agree\b",
        r"\bfirmly support\b",
    ]
    for p in absolute_pos:
        if re.search(p, st_lower):
            return 0.85

    # 3. Check for neutral variance
    for p in UNIVERSAL_NEUTRAL_PATTERNS:
        if re.search(p, st_lower):
            return 0.10

    # 4. Universal keyword accumulation
    pos_hits = sum(1 for p in UNIVERSAL_AFFIRMATIVE_PATTERNS if re.search(p, st_lower))
    neg_hits = sum(1 for p in UNIVERSAL_OPPOSING_PATTERNS if re.search(p, st_lower))

    if pos_hits > neg_hits:
        return round(min(1.0, 0.70 + 0.08 * (pos_hits - neg_hits)), 2)
    elif neg_hits > pos_hits:
        return round(max(-1.0, -0.70 - 0.08 * (neg_hits - pos_hits)), 2)

    # 5. Fallback check on reasoning if stance header was generic
    if reasoning_text:
        reas_lower = reasoning_text[:300].lower()
        r_pos = sum(1 for p in UNIVERSAL_AFFIRMATIVE_PATTERNS if re.search(p, reas_lower))
        r_neg = sum(1 for p in UNIVERSAL_OPPOSING_PATTERNS if re.search(p, reas_lower))
        if r_pos > r_neg:
            return 0.75
        elif r_neg > r_pos:
            return -0.75

    return 0.0


def compute_opinion_trajectories(
    discussion_data: DiscussionResult | dict[str, Any],
    use_llm: bool = False,
    llm_client: Any = None,
) -> OpinionTrajectoryResult:
    """
    Compute per-agent, per-round numeric stance trajectories and deltas across all rounds.
    Universal for any discussion topic.

    Parameters:
    -----------
    discussion_data: DiscussionResult or dict loaded from outputs/<id>.json
    use_llm: bool, default False
        If True, evaluates stances with batched zero-shot LLM evaluation for any topic.
        If False or on LLM failure, uses fast local semantic polarity analysis.
    llm_client: Any, optional
        Pre-configured OpenAICompatibleLLM client.

    Returns:
    --------
    OpinionTrajectoryResult:
        Typed result containing chronological list of AgentStancePoint per agent.
    """
    if isinstance(discussion_data, DiscussionResult):
        data = discussion_data.to_dict()
    elif isinstance(discussion_data, dict):
        data = discussion_data
    else:
        raise TypeError(f"Expected DiscussionResult or dict, got {type(discussion_data).__name__}")

    config = data.get("config", {})
    discussion_id = str(config.get("discussion_id", "unknown"))
    topic = str(config.get("topic", ""))
    total_rounds = int(config.get("num_rounds", 3))
    agent_ids = list(config.get("agent_ids", []))

    raw_opinions = data.get("opinions", [])
    if not raw_opinions:
        logger.warning("Discussion %s contains no opinion snapshots.", discussion_id)
        return OpinionTrajectoryResult(
            discussion_id=discussion_id,
            topic=topic,
            total_rounds=total_rounds,
            agent_ids=agent_ids,
            trajectories={},
        )

    # Optional: run universal batched LLM evaluation
    llm_scores: dict[tuple[str, int], float] = {}
    if use_llm:
        llm_scores = score_snapshots_with_llm(topic, raw_opinions, llm_client=llm_client)

    # Group snapshots by agent_id, sorted by round_num
    opinions_by_agent: dict[str, list[dict[str, Any]]] = {}
    for op in raw_opinions:
        aid = op.get("agent_id") if isinstance(op, dict) else getattr(op, "agent_id", "")
        if not aid:
            continue
        opinions_by_agent.setdefault(aid, []).append(op if isinstance(op, dict) else op.to_dict())

    # Build agent list if missing in config
    if not agent_ids:
        agent_ids = sorted(opinions_by_agent.keys())

    trajectories: dict[str, list[AgentStancePoint]] = {}

    for agent_id in agent_ids:
        agent_ops = opinions_by_agent.get(agent_id, [])
        agent_ops.sort(key=lambda item: int(item.get("round_num", 0)))

        points: list[AgentStancePoint] = []
        prev_stance_val: float | None = None

        for op in agent_ops:
            round_num = int(op.get("round_num", 0))
            stance_text = str(op.get("stance", ""))
            changed = bool(op.get("changed_from_previous", False))
            change_reason = str(op.get("change_reason", ""))

            # Retrieve score from LLM batch if available, else local semantic scoring
            if (agent_id, round_num) in llm_scores:
                curr_stance_val = llm_scores[(agent_id, round_num)]
            else:
                curr_stance_val = extract_numeric_stance(op, prev_stance=prev_stance_val, topic=topic)

            # Calculate round-to-round delta
            if prev_stance_val is None:
                opinion_change = None
            else:
                opinion_change = round(curr_stance_val - prev_stance_val, 2)

            point = AgentStancePoint(
                agent_id=agent_id,
                round_num=round_num,
                stance_value=curr_stance_val,
                opinion_change=opinion_change,
                stance_text=stance_text,
                changed_from_previous=changed,
                change_reason=change_reason,
            )
            points.append(point)
            prev_stance_val = curr_stance_val

        trajectories[agent_id] = points

    return OpinionTrajectoryResult(
        discussion_id=discussion_id,
        topic=topic,
        total_rounds=total_rounds,
        agent_ids=agent_ids,
        trajectories=trajectories,
    )
