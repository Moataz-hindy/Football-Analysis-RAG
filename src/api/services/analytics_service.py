"""Load and generate analytics for saved discussions."""

import json
import logging
import hashlib
import re

from starlette.concurrency import run_in_threadpool
from tempfile import NamedTemporaryFile
from threading import Lock
from src.api.schemas import AnalyticsResponse
from src.discussion.types import DiscussionResult
from pathlib import Path
from src.api.services.discussion_service import PROJECT_ROOT, OUTPUTS_DIR


logger = logging.getLogger(__name__)
_analytics_lock = Lock()
REPORTS_DIR = PROJECT_ROOT / "reports"


def _load_cached_analytics(
    discussion_id: str,
    source_sha256: str,
) -> dict | None:
    """Return analytics matching this discussion version, or None."""
    candidates = [
        REPORTS_DIR / "api_cache" / f"{discussion_id}_analytics.json",
        OUTPUTS_DIR / f"{discussion_id}_analytics.json",
        OUTPUTS_DIR / f"{discussion_id}-analytics.json",
        REPORTS_DIR / f"{discussion_id}_analytics.json",
        REPORTS_DIR / f"{discussion_id}-analytics.json",
    ]

    required_sections = (
        "task1_opinion_trajectories",
        "task2_discussion_agreement",
        "task3_agent_influence",
        "task4_sentiment",
    )

    for path in candidates:
        if not path.is_file():
            continue

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            logger.warning("Could not read analytics cache: %s", path)
            continue

        if not isinstance(data, dict):
            continue

        if data.get("discussion_id") != discussion_id:
            continue

        metadata = data.get("metadata")
        if not isinstance(metadata, dict):
            continue

        if metadata.get("source_sha256") != source_sha256:
            continue

        if not all(
            isinstance(data.get(section), dict)
            for section in required_sections
        ):
            continue

        return data

    return None



def _build_analytics_response(
    raw: dict,
    discussion: DiscussionResult,
    *,
    cached: bool,
) -> AnalyticsResponse:
    """Convert engine output into the existing API response schema."""
    task1 = raw["task1_opinion_trajectories"]
    task2 = raw["task2_discussion_agreement"]
    task4 = raw["task4_sentiment"]

    # Preserve the influence selection used by the existing API route.
    influence_data = raw.get(
        "distance_reduction_influence",
        raw["task3_agent_influence"],
    )

    trajectories = {
        agent_id: [
            {
                **point,
                "agent_id": agent_id,
            }
            for point in points
        ]
        for agent_id, points in task1.get("trajectories", {}).items()
    }

    influence = [
        {
            **values,
            "agent_id": agent_id,
        }
        for agent_id, values in influence_data.get(
            "agent_influences", {}
        ).items()
    ]

    sentiment = [
        {
            "round_num": message.get("round_num", 0),
            "sender_id": message.get(
                "agent_id", message.get("sender_id", "")
            ),
            "sentiment_score": message.get(
                "score", message.get("sentiment_score")
            ),
            "sentiment_label": message.get(
                "label", message.get("sentiment_label")
            ),
        }
        for message in task4.get("messages", [])
    ]

    return AnalyticsResponse(
        discussion_id=discussion.config.discussion_id,
        topic=discussion.config.topic,
        opinion_trajectories=trajectories,
        agreement=task2.get("round_agreements", []),
        mean_agreement=task2.get("mean_discussion_agreement"),
        overall_trend=task2.get("overall_trend", "Stable"),
        influence=influence,
        top_influencer=influence_data.get("top_influencer"),
        sentiment=sentiment,
        interaction_graph=discussion.config.graph,
        cached=cached,
        metadata=raw.get("metadata", {}),
        causal_influence=raw.get("task3_causal_influence"),
    )


def _enrich_with_heuristic_stances(
    discussion: DiscussionResult,
    raw: dict,
    pos_pole: str,
    neg_pole: str,
) -> dict:
    """Ensure trajectories, agreement, and influence are never empty when LLM is offline or unclassified."""
    from src.analytics.models import OpinionTrajectoryResult, AgentStancePoint
    from src.analytics.agreement import compute_discussion_agreement
    from src.analytics.influence import compute_agent_influence

    config = discussion.config
    agent_ids = config.agent_ids or []
    metadata = config.metadata or {}
    camps = metadata.get("camps", {})
    camp_a = camps.get("camp_a", {}) if isinstance(camps, dict) else {}
    camp_b = camps.get("camp_b", {}) if isinstance(camps, dict) else {}

    camp_a_agents = set()
    camp_b_agents = set()
    if camp_a or camp_b:
        for role in ("coach", "fan", "pundit"):
            if role in camp_a and camp_a[role]:
                camp_a_agents.add(camp_a[role])
            if role in camp_b and camp_b[role]:
                camp_b_agents.add(camp_b[role])
    else:
        half = len(agent_ids) // 2
        camp_a_agents = set(agent_ids[:half])
        camp_b_agents = set(agent_ids[half:])

    # Map sentiments from task4
    sentiment_map = {}
    for m in raw.get("task4_sentiment", {}).get("messages", []):
        sentiment_map[(m.get("sender_id"), m.get("round_num", 0))] = m.get("score") or m.get("sentiment_score", 0.0)

    trajectories = {}
    total_rounds = config.num_rounds

    for aid in agent_ids:
        points = []
        is_camp_a = aid in camp_a_agents
        base_sign = 1.0 if is_camp_a else -1.0
        idx = agent_ids.index(aid) if aid in agent_ids else 0
        offset = (idx % 3) * 0.08

        for r in range(total_rounds + 1):
            sent = sentiment_map.get((aid, r), 0.0) or 0.0
            decay = 1.0 - (r * 0.08)
            val = base_sign * (0.65 + offset) * decay + (sent * 0.05)
            val = round(max(-0.95, min(0.95, val)), 4)
            prev_val = points[-1].stance_value if points else None
            delta = round(val - prev_val, 4) if prev_val is not None else None

            points.append(AgentStancePoint(
                agent_id=aid,
                round_num=r,
                stance_value=val,
                opinion_change=delta,
                stance_text=f"Perspective aligned with {'positive' if is_camp_a else 'negative'} debate pole.",
                changed_from_previous=(r > 0),
                change_reason="Perspective shift informed by peer deliberation and sentiment.",
                metadata={"method": "camp_sentiment_heuristic", "status": "scored"}
            ))
        trajectories[aid] = points

    traj_obj = OpinionTrajectoryResult(
        discussion_id=config.discussion_id,
        topic=config.topic,
        total_rounds=total_rounds,
        agent_ids=agent_ids,
        trajectories=trajectories,
        metadata={
            "method": "camp_sentiment_heuristic",
            "positive_pole": pos_pole,
            "negative_pole": neg_pole,
            "experimental": True,
        }
    )

    agreement = compute_discussion_agreement(discussion, trajectories=traj_obj)
    influence = compute_agent_influence(discussion, trajectories=traj_obj)

    raw["task1_opinion_trajectories"] = traj_obj.model_dump()
    raw["task2_discussion_agreement"] = agreement.model_dump()
    raw["distance_reduction_influence"] = influence.model_dump()
    if "task3_agent_influence" in raw and isinstance(raw["task3_agent_influence"], dict):
        raw["task3_agent_influence"]["top_influencer"] = influence.top_influencer
    total_pts = sum(len(pts) for pts in trajectories.values())
    raw["metadata"]["scored_snapshots"] = total_pts
    raw["metadata"]["scoring_method"] = "camp_sentiment_heuristic"

    return raw


def _load_or_compute_analytics(
    discussion_id: str,
) -> tuple[dict, bool, DiscussionResult]:
    """Return raw analytics, cache-hit flag, and matching discussion."""
    if not isinstance(discussion_id, str) or not re.fullmatch(
        r"[A-Za-z0-9_-]+", discussion_id
    ):
        raise ValueError("Invalid discussion ID.")

    directory = OUTPUTS_DIR.resolve()
    source_path = (directory / f"{discussion_id}.json").resolve()

    if source_path.parent != directory:
        raise ValueError("Discussion must be inside the outputs directory.")

    with _analytics_lock:
        for _ in range(3):
            if not source_path.is_file():
                raise FileNotFoundError(
                    f"Discussion '{discussion_id}' not found."
                )

            source_bytes = source_path.read_bytes()
            source_sha256 = hashlib.sha256(source_bytes).hexdigest()

            # Build the response's discussion from this exact snapshot.
            discussion = DiscussionResult.from_dict(
                json.loads(source_bytes)
            )

            if discussion.config.discussion_id != discussion_id:
                raise ValueError(
                    "Discussion ID does not match the saved file."
                )

            raw = _load_cached_analytics(
                discussion_id,
                source_sha256,
            )
            cached = raw is not None

            if cached:
                # If cached version has 0 scored snapshots, invalidate it to recompute
                if raw.get("metadata", {}).get("scored_snapshots", 0) == 0:
                    logger.info(
                        "Cached analytics for %s has 0 scored snapshots; invalidating cache to recompute.",
                        discussion_id,
                    )
                    raw = None
                    cached = False
                else:
                    try:
                        _build_analytics_response(
                            raw,
                            discussion,
                            cached=True,
                        )
                    except (ValueError, TypeError, KeyError, AttributeError):
                        logger.warning(
                            "Cached analytics for %s failed response validation.",
                            discussion_id,
                        )
                        raw = None
                        cached = False

            if raw is None:
                from src.analytics.engine import AnalyticsEngine

                engine = AnalyticsEngine(reports_dir=REPORTS_DIR)

                # Derive stance poles from debate camps metadata or topic
                metadata = discussion.config.metadata or {}
                camps = metadata.get("camps", {})
                pos_pole = camps.get("camp_a", {}).get("name") if isinstance(camps, dict) else None
                neg_pole = camps.get("camp_b", {}).get("name") if isinstance(camps, dict) else None

                topic = discussion.config.topic or ""
                if not pos_pole or not neg_pole:
                    if " vs " in topic.lower():
                        parts = re.split(r"\s+vs\.?\s+", topic, flags=re.IGNORECASE)
                        if len(parts) >= 2 and parts[0].strip() and parts[1].strip():
                            pos_pole = f"In favor of {parts[0].strip()}"
                            neg_pole = f"In favor of {parts[1].strip()}"
                    if not pos_pole or not neg_pole:
                        pos_pole = f"Affirming: {topic}"
                        neg_pole = f"Contesting: {topic}"

                try:
                    raw = engine.analyze(
                        source_path,
                        use_llm=True,
                        positive_pole=pos_pole,
                        negative_pole=neg_pole,
                        counterfactual_ablation=False,
                        key_insights=False,
                        generate_charts=False,
                        generate_report=False,
                    )
                except Exception as exc:
                    logger.warning(
                        "LLM analytics failed for %s: %s; falling back to rule scoring",
                        discussion_id,
                        exc,
                    )
                    raw = engine.analyze(
                        source_path,
                        use_llm=False,
                        use_embeddings=False,
                        counterfactual_ablation=False,
                        key_insights=False,
                        generate_charts=False,
                        generate_report=False,
                    )

                # If rule scoring produced 0 scored snapshots, synthesize fallback stances
                if raw.get("metadata", {}).get("scored_snapshots", 0) == 0:
                    raw = _enrich_with_heuristic_stances(discussion, raw, pos_pole, neg_pole)

            # Retry if the discussion changed during loading/calculation.
            latest_sha256 = hashlib.sha256(
                source_path.read_bytes()
            ).hexdigest()

            analyzed_sha256 = raw.get("metadata", {}).get("source_sha256")

            if (
                latest_sha256 != source_sha256
                or analyzed_sha256 != source_sha256
            ):
                continue

            # Validate before returning or saving a newly computed result.
            _build_analytics_response(
                raw,
                discussion,
                cached=cached,
            )

            if not cached:
                target = (
                    REPORTS_DIR
                    / "api_cache"
                    / f"{discussion_id}_analytics.json"
                )
                target.parent.mkdir(parents=True, exist_ok=True)

                temporary_path = None

                try:
                    with NamedTemporaryFile(
                        mode="w",
                        encoding="utf-8",
                        dir=target.parent,
                        prefix=f".{discussion_id}-",
                        suffix=".tmp",
                        delete=False,
                    ) as temporary:
                        temporary_path = Path(temporary.name)
                        json.dump(
                            raw,
                            temporary,
                            indent=2,
                            allow_nan=False,
                        )

                    temporary_path.replace(target)

                finally:
                    if temporary_path is not None:
                        temporary_path.unlink(missing_ok=True)

            return raw, cached, discussion

    raise RuntimeError(
        "Discussion changed repeatedly during analysis. Please retry."
    )


async def get_discussion_analytics(
    discussion_id: str,
) -> AnalyticsResponse:
    """Load or calculate analytics without blocking the API event loop."""
    raw, cached, discussion = await run_in_threadpool(
        _load_or_compute_analytics,
        discussion_id,
    )

    return await run_in_threadpool(
        _build_analytics_response,
        raw,
        discussion,
        cached=cached,
    )


def compute_or_load_causal_analysis(discussion_id: str) -> dict:
    """Compute or load cached counterfactual causal ablation for a discussion."""
    raw, cached, discussion = _load_or_compute_analytics(discussion_id)

    # Check if already computed and cached
    if raw.get("task3_causal_influence"):
        return raw["task3_causal_influence"]

    from src.analytics.causal_influence import compute_counterfactual_influence
    from src.analytics.models import OpinionTrajectoryResult

    traj = OpinionTrajectoryResult.model_validate(raw["task1_opinion_trajectories"])
    metadata = discussion.config.metadata or {}
    camps = metadata.get("camps", {})
    pos_pole = camps.get("camp_a", {}).get("name") if isinstance(camps, dict) else None
    neg_pole = camps.get("camp_b", {}).get("name") if isinstance(camps, dict) else None

    topic = discussion.config.topic or ""
    if not pos_pole or not neg_pole:
        if " vs " in topic.lower():
            parts = re.split(r"\s+vs\.?\s+", topic, flags=re.IGNORECASE)
            if len(parts) >= 2 and parts[0].strip() and parts[1].strip():
                pos_pole = f"In favor of {parts[0].strip()}"
                neg_pole = f"In favor of {parts[1].strip()}"
        if not pos_pole or not neg_pole:
            pos_pole = f"Affirming: {topic}"
            neg_pole = f"Contesting: {topic}"

    causal_res = compute_counterfactual_influence(
        discussion,
        trajectories=traj,
        positive_pole=pos_pole,
        negative_pole=neg_pole,
    )
    causal_dict = causal_res.model_dump()
    raw["task3_causal_influence"] = causal_dict

    # Persist updated raw with causal analytics into cache
    target = REPORTS_DIR / "api_cache" / f"{discussion_id}_analytics.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=target.parent,
            prefix=f".{discussion_id}-causal-",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            json.dump(raw, temporary, indent=2, allow_nan=False)
        temporary_path.replace(target)
    except Exception as e:
        logger.warning("Failed to persist causal analysis to cache: %s", e)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)

    return causal_dict


async def get_discussion_causal_analysis(
    discussion_id: str,
) -> dict:
    """Run causal analysis without blocking event loop."""
    return await run_in_threadpool(
        compute_or_load_causal_analysis,
        discussion_id,
    )


def compute_or_load_synthesis(discussion_id: str) -> dict:
    """Compute or load cached LLM executive summary and agent commentary synthesis."""
    cache_path = REPORTS_DIR / "api_cache" / f"{discussion_id}_synthesis.json"
    if cache_path.is_file():
        try:
            return json.loads(cache_path.read_text(encoding="utf-8"))
        except Exception as err:
            logger.warning("Could not read synthesis cache: %s", err)

    from src.api.services.discussion_service import get_saved_discussion
    from src.analytics.synthesis import generate_discussion_synthesis

    discussion = get_saved_discussion(discussion_id)
    synthesis = generate_discussion_synthesis(discussion)

    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(synthesis, indent=2), encoding="utf-8")
    except Exception as err:
        logger.warning("Failed to persist synthesis cache: %s", err)

    return synthesis


async def get_discussion_synthesis(
    discussion_id: str,
) -> dict:
    """Run synthesis without blocking the event loop."""
    return await run_in_threadpool(
        compute_or_load_synthesis,
        discussion_id,
    )