"""Load and generate analytics for saved discussions."""

import os
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

    # Do not serve an empty causal payload as if it were a computed result.
    causal_raw = raw.get("task3_causal_influence")
    if causal_raw and not causal_raw.get("evaluated_exchanges_count"):
        causal_raw = None

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
        causal_influence=causal_raw,
    )


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
                meta = raw.get("metadata", {})
                scoring_method = meta.get("scoring_method")
                scored_snapshots = meta.get("scored_snapshots", 0)
                num_agents = len(discussion.config.agent_ids or [])
                num_rounds = discussion.config.num_rounds or 3
                total_expected = num_agents * (num_rounds + 1)
                if total_expected == 0:
                    total_expected = len(discussion.opinions) or 1
                scored_ratio = scored_snapshots / total_expected if total_expected > 0 else 0.0

                if (
                    scoring_method in ("self_report_rules", "camp_sentiment_heuristic")
                    or scored_ratio < 0.80
                    or scored_snapshots == 0
                ):
                    logger.info(
                        "Cached analytics for %s invalid (scoring_method=%s, scored_ratio=%.2f, scored_snapshots=%s); invalidating cache to recompute.",
                        discussion_id,
                        scoring_method,
                        scored_ratio,
                        scored_snapshots,
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

                is_testing = bool(os.environ.get("PYTEST_CURRENT_TEST"))
                try:
                    raw = engine.analyze(
                        source_path,
                        use_llm=not is_testing,
                        positive_pole=pos_pole,
                        negative_pole=neg_pole,
                        counterfactual_ablation=False,
                        key_insights=False,
                        generate_charts=False,
                        generate_report=False,
                    )
                except Exception as exc:
                    logger.warning(
                        "LLM analytics failed for %s: %s; falling back to embedding scoring",
                        discussion_id,
                        exc,
                    )
                    raw = engine.analyze(
                        source_path,
                        use_llm=False,
                        use_embeddings=True,
                        positive_pole=pos_pole,
                        negative_pole=neg_pole,
                        counterfactual_ablation=False,
                        key_insights=False,
                        generate_charts=False,
                        generate_report=False,
                    )
                # No fabrication: an unscorable result stays unscored (null stances) and is
                # reported as such by the API and the Intelligence page.
                if raw.get("metadata", {}).get("scored_snapshots", 0) == 0:
                    logger.warning(
                        "Analytics for %s could not score any stance; returning the unscored result.",
                        discussion_id,
                    )

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
    """Compute or load cached counterfactual causal ablation for a discussion.

    An empty result (no eligible exchanges) is NOT cached: new discussion
    rounds may add exchanges, and a persisted empty result would be served
    forever as 'Cached & Verified'.
    """
    raw, cached, discussion = _load_or_compute_analytics(discussion_id)

    existing = raw.get("task3_causal_influence")
    if existing and existing.get("evaluated_exchanges_count"):
        return existing

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

    if causal_dict.get("evaluated_exchanges_count"):
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


def compute_or_load_advisor_decision(discussion_id: str) -> dict:
    """Compute or load cached LLM strategic advisor decision."""
    cache_path = REPORTS_DIR / "api_cache" / f"{discussion_id}_advisor.json"
    if cache_path.is_file():
        try:
            return json.loads(cache_path.read_text(encoding="utf-8"))
        except Exception as err:
            logger.warning("Could not read advisor decision cache: %s", err)

    from src.api.services.discussion_service import get_saved_discussion
    from src.analytics.advisor import generate_advisor_decision

    discussion = get_saved_discussion(discussion_id)
    advisor = generate_advisor_decision(discussion)

    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(advisor, indent=2), encoding="utf-8")
    except Exception as err:
        logger.warning("Failed to persist advisor decision cache: %s", err)

    return advisor


async def get_discussion_advisor_decision(
    discussion_id: str,
) -> dict:
    """Run advisor decision without blocking the event loop."""
    return await run_in_threadpool(
        compute_or_load_advisor_decision,
        discussion_id,
    )
