"""Route definitions for the Football Analysis Platform API."""

import json
import logging
import os
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import RedirectResponse

from src.discussion.persistence import list_discussions, load_discussion_by_id
from src.discussion.types import DiscussionResult
from src.api.schemas import (
    AgentInfluenceOut,
    AgentInfo,
    AnalyticsResponse,
    DiscussionDetailResponse,
    DiscussionListResponse,
    DiscussionStatusResponse,
    DiscussionSummary,
    HealthResponse,
    MessageOut,
    RoundAgreementOut,
    SentimentOut,
    StancePointOut,
    StartDiscussionRequest,
    StartDiscussionResponse,
    TopicItem,
    TopicsResponse,
)

logger = logging.getLogger("src.api.routes")
router = APIRouter()


# ── Root Redirect ──
@router.get("/", include_in_schema=False)
async def root():
    """Redirect root to Swagger UI docs."""
    return RedirectResponse(url="/docs")


# ── Curated Predefined Topics ──
CURATED_TOPICS = [
    TopicItem(
        id="japan-spain-2022",
        label="Japan's 5-4-1 Low Block vs Spain (2022 World Cup)",
        description="Tactical and performance analysis of Japan's defensive structure and counter-attacking efficiency against Spain.",
    ),
    TopicItem(
        id="argentina-france-2022",
        label="Was France Unlucky in the 2022 World Cup Final?",
        description="Evaluating refereeing decisions, momentum shifts, and tactical changes in the 2022 World Cup Final.",
    ),
    TopicItem(
        id="arsenal-striker-dilemma",
        label="Should Arsenal Sign a Proven Striker in January?",
        description="Statistical and financial analysis comparing Havertz/Jesus with elite central strikers.",
    ),
    TopicItem(
        id="egypt-argentina-officiating",
        label="Did Argentina Win Against Egypt Because of Match Officials?",
        description="Multi-angle debate covering controversial refereeing calls, statistical xG disparity, and tactical game state.",
    ),
    TopicItem(
        id="tuchel-bayern-tactics",
        label="Tuchel's Tactical Setup vs Leverkusen: Masterclass or Collapse?",
        description="Analyzing Bayer Leverkusen's 3-0 victory against Bayern Munich and Tuchel's sudden back-three formation.",
    ),
]


# ── 1. Health Check ──
@router.get(
    "/health",
    response_model=HealthResponse,
    tags=["System"],
    summary="Lightweight system health check",
)
async def health_check():
    """Verify that the API server is healthy and running."""
    return HealthResponse(status="ok")


# ── 2. Topics ──
@router.get(
    "/topics",
    response_model=TopicsResponse,
    tags=["Topics"],
    summary="List available discussion topics",
)
async def get_topics():
    """Return curated football discussion topics compatible with the knowledge base."""
    return TopicsResponse(topics=CURATED_TOPICS)


# ── 3. List Discussions ──
@router.get(
    "/discussions",
    response_model=DiscussionListResponse,
    tags=["Discussions"],
    summary="List saved discussions",
)
async def get_discussions():
    """Return summary metadata for all saved discussions in outputs/."""
    try:
        raw_summaries = list_discussions(output_dir="outputs")
        discussions = [
            DiscussionSummary(
                discussion_id=item.get("discussion_id", ""),
                topic=item.get("topic", ""),
                num_agents=int(item.get("num_agents", 0)),
                num_rounds=int(item.get("num_rounds", 0)),
                num_messages=int(item.get("num_messages", 0)),
                timestamp=str(item.get("timestamp", "")),
            )
            for item in raw_summaries
        ]
        return DiscussionListResponse(discussions=discussions)
    except Exception as exc:
        logger.error("Failed to list discussions: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list discussions: {exc}",
        )


# ── 4. Start Discussion ──
@router.post(
    "/discussions",
    response_model=StartDiscussionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["Discussions"],
    summary="Start a new multi-agent discussion",
)
async def start_discussion(req: StartDiscussionRequest):
    """Queue a new discussion for execution.

    NOTE: P1 provides the endpoint stub and API contract.
    P4 (Backend Integration) wires the background runner to execute
    the multi-agent discussion engine asynchronously.
    """
    discussion_id = req.discussion_id or f"disc-{uuid4().hex[:8]}"

    # Try delegating to P4 discussion service if available
    try:
        from src.api.services.discussion_service import enqueue_discussion
        return await enqueue_discussion(discussion_id=discussion_id, request=req)
    except (ImportError, AttributeError):
        logger.info("P4 discussion service not detected. Returning stub response for %s", discussion_id)

    return StartDiscussionResponse(
        discussion_id=discussion_id,
        status="queued",
        message="Discussion has been accepted and queued for execution",
    )


# ── 5. Discussion Detail ──
@router.get(
    "/discussions/{discussion_id}",
    response_model=DiscussionDetailResponse,
    tags=["Discussions"],
    summary="Get full discussion details",
)
async def get_discussion(discussion_id: str):
    """Load and return the complete persistent record of a single discussion."""
    try:
        discussion: DiscussionResult = load_discussion_by_id(discussion_id, output_dir="outputs")
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Discussion '{discussion_id}' not found",
        )
    except Exception as exc:
        logger.error("Error loading discussion %s: %s", discussion_id, exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error loading discussion: {exc}",
        )

    agents = [
        AgentInfo(agent_id=aid, persona_file=f"personas/{aid}.yaml")
        for aid in discussion.config.agent_ids
    ]

    messages = [
        MessageOut(
            round_num=m.round_num,
            sender_id=m.sender_id,
            recipient_ids=m.recipient_ids,
            content=m.content,
            sentiment_score=m.sentiment_score,
            sentiment_label=m.sentiment_label,
            timestamp=m.timestamp,
        )
        for m in discussion.messages
    ]

    return DiscussionDetailResponse(
        discussion_id=discussion.config.discussion_id,
        topic=discussion.config.topic,
        agents=agents,
        num_rounds=discussion.config.num_rounds,
        graph=discussion.config.graph,
        messages=messages,
        timestamp=discussion.config.timestamp,
    )


# ── 6. Discussion Status ──
@router.get(
    "/discussions/{discussion_id}/status",
    response_model=DiscussionStatusResponse,
    tags=["Discussions"],
    summary="Check discussion execution status",
)
async def get_discussion_status(discussion_id: str):
    """Check the execution status of a discussion (completed, running, or not_found)."""
    # Check if P4 runtime tracker has an in-progress record
    try:
        from src.api.services.discussion_service import get_runtime_status
        rt_status = get_runtime_status(discussion_id)
        if rt_status is not None:
            return rt_status
    except (ImportError, AttributeError):
        pass

    # Check if completed discussion file exists in outputs/
    output_file = Path("outputs") / f"{discussion_id}.json"
    if output_file.is_file():
        try:
            with open(output_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            total_rounds = data.get("config", {}).get("num_rounds")
            return DiscussionStatusResponse(
                discussion_id=discussion_id,
                status="completed",
                current_round=total_rounds,
                total_rounds=total_rounds,
                message="Discussion execution completed",
            )
        except Exception:
            return DiscussionStatusResponse(
                discussion_id=discussion_id,
                status="completed",
                message="Discussion execution completed",
            )

    return DiscussionStatusResponse(
        discussion_id=discussion_id,
        status="not_found",
        message=f"Discussion '{discussion_id}' not found",
    )


# ── 7. Discussion Analytics ──
@router.get(
    "/discussions/{discussion_id}/analytics",
    response_model=AnalyticsResponse,
    tags=["Analytics"],
    summary="Get analytics for a discussion",
)
async def get_analytics(discussion_id: str):
    """Retrieve discussion analytics with cache-first lookup.

    Delegates to P4 Analytics Service when available. Otherwise:
    1. Checks for cached analytics JSON file.
    2. Runs AnalyticsEngine.analyze() on the discussion.
    3. Maps the output to the validated AnalyticsResponse schema.
    """
    # Delegate to P4 Analytics Service if implemented
    try:
        from src.api.services.analytics_service import get_discussion_analytics
        result = await get_discussion_analytics(discussion_id)
        if result is not None:
            return result
    except (ImportError, AttributeError):
        logger.debug("P4 analytics service not found, using built-in cache/engine fallback")

    # Step A: Load discussion result
    try:
        discussion: DiscussionResult = load_discussion_by_id(discussion_id, output_dir="outputs")
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Discussion '{discussion_id}' not found",
        )
    except Exception as exc:
        logger.error("Error loading discussion %s: %s", discussion_id, exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load discussion for analytics: {exc}",
        )

    # Step B: Check for cached analytics file to avoid recomputing expensive operations
    cached_candidates = [
        Path("reports") / f"{discussion_id}_analytics.json",
        Path("outputs") / f"{discussion_id}_analytics.json",
    ]
    raw_analytics = None
    is_cached = False

    for candidate in cached_candidates:
        if candidate.is_file():
            try:
                with open(candidate, "r", encoding="utf-8") as f:
                    raw_analytics = json.load(f)
                is_cached = True
                logger.info("Loaded cached analytics for %s from %s", discussion_id, candidate)
                break
            except Exception as e:
                logger.warning("Failed to parse cached analytics file %s: %s", candidate, e)

    # Step C: Compute analytics if not cached
    if raw_analytics is None:
        try:
            from src.analytics.engine import AnalyticsEngine
            engine = AnalyticsEngine(reports_dir="reports")
            raw_analytics = engine.analyze(discussion)
            is_cached = False
        except Exception as exc:
            logger.error("Analytics computation failed for %s: %s", discussion_id, exc, exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Analytics computation failed: {exc}",
            )

    # Step D: Map raw analytics to AnalyticsResponse schema
    try:
        # Task 1: Trajectories
        t1 = raw_analytics.get("task1_opinion_trajectories", {})
        trajectories: dict[str, list[StancePointOut]] = {}
        for aid, pts in t1.get("trajectories", {}).items():
            trajectories[aid] = [
                StancePointOut(
                    agent_id=p.get("agent_id", aid) if isinstance(p, dict) else getattr(p, "agent_id", aid),
                    round_num=p.get("round_num", 0) if isinstance(p, dict) else getattr(p, "round_num", 0),
                    stance_value=p.get("stance_value") if isinstance(p, dict) else getattr(p, "stance_value", None),
                    opinion_change=p.get("opinion_change") if isinstance(p, dict) else getattr(p, "opinion_change", None),
                    stance_text=p.get("stance_text", "") if isinstance(p, dict) else getattr(p, "stance_text", ""),
                )
                for p in pts
            ]

        # Task 2: Agreement
        t2 = raw_analytics.get("task2_discussion_agreement", raw_analytics.get("task2_agreement", {}))
        agreement = [
            RoundAgreementOut(
                round_num=ra.get("round_num", 0) if isinstance(ra, dict) else getattr(ra, "round_num", 0),
                agreement_score=ra.get("agreement_score") if isinstance(ra, dict) else getattr(ra, "agreement_score", None),
                mean_distance=ra.get("mean_distance") if isinstance(ra, dict) else getattr(ra, "mean_distance", None),
                variance=float(ra.get("variance", 0.0) if isinstance(ra, dict) else getattr(ra, "variance", 0.0)),
                interpretation=ra.get("interpretation", "") if isinstance(ra, dict) else getattr(ra, "interpretation", ""),
            )
            for ra in t2.get("round_agreements", [])
        ]

        # Task 3: Influence
        t3 = raw_analytics.get("distance_reduction_influence", raw_analytics.get("task3_agent_influence", {}))
        agent_influences = t3.get("agent_influences", {})
        influence = []
        for aid, inf in agent_influences.items():
            if isinstance(inf, dict):
                influence.append(
                    AgentInfluenceOut(
                        agent_id=aid,
                        influence_score=inf.get("influence_score"),
                        status=inf.get("status", "valid"),
                        rationale=inf.get("rationale", ""),
                    )
                )
            else:
                influence.append(
                    AgentInfluenceOut(
                        agent_id=aid,
                        influence_score=getattr(inf, "influence_score", None),
                        status=getattr(inf, "status", "valid"),
                        rationale=getattr(inf, "rationale", ""),
                    )
                )

        # Task 4: Sentiment
        t4 = raw_analytics.get("task4_sentiment", {})
        sentiment = [
            SentimentOut(
                round_num=m.get("round_num", 0),
                sender_id=m.get("agent_id", m.get("sender_id", "")),
                sentiment_score=m.get("score", m.get("sentiment_score")),
                sentiment_label=m.get("label", m.get("sentiment_label")),
            )
            for m in t4.get("messages", [])
        ]

        return AnalyticsResponse(
            discussion_id=discussion.config.discussion_id,
            topic=discussion.config.topic,
            opinion_trajectories=trajectories,
            agreement=agreement,
            mean_agreement=t2.get("mean_discussion_agreement"),
            overall_trend=t2.get("overall_trend", "Stable"),
            influence=influence,
            top_influencer=t3.get("top_influencer"),
            sentiment=sentiment,
            interaction_graph=discussion.config.graph,
            cached=is_cached,
            metadata=raw_analytics.get("metadata", {}),
        )
    except Exception as exc:
        logger.error("Failed to map analytics response for %s: %s", discussion_id, exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to map analytics response: {exc}",
        )
