"""Route definitions for the Football Analysis Platform API."""

import json
import logging
import os
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import RedirectResponse

from starlette.concurrency import run_in_threadpool

from src.api.services.discussion_service import (
    get_saved_discussion,
    list_saved_discussions,
)
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
async def root(request: Request):
    """Redirect root to React frontend app preserving query params."""
    target = f"/app/?{request.url.query}" if request.url.query else "/app/"
    return RedirectResponse(url=target)



# ── Curated Predefined Topics ──
CURATED_TOPICS: list[TopicItem] = [
    TopicItem(
        id="argentina-france-2022",
        label="Argentina vs France (2022 World Cup Final)",
        description="Scaloni's tactical switch of Di María to the left flank vs France's late physical transitions.",
    ),
    TopicItem(
        id="japan-spain-2022",
        label="Japan's 5-4-1 Low Block vs Spain (2022 World Cup)",
        description="Tactical and performance analysis of Japan's compact 5-4-1 defensive structure and rapid transitions against Spain.",
    ),
    TopicItem(
        id="netherlands-argentina-2022",
        label="Netherlands vs Argentina (2022 World Cup Quarter-Final)",
        description="Van Gaal's direct Route-One aerial overload vs Argentina's defensive rest structure.",
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
        raw_summaries = await run_in_threadpool(list_saved_discussions)
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
    
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        )
    
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
    """Schedule a real discussion in the background."""
    from src.api.services.discussion_service import enqueue_discussion

    discussion_id = req.discussion_id or f"disc-{uuid4().hex[:8]}"

    return await enqueue_discussion(
        discussion_id=discussion_id,
        request=req,
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
        discussion: DiscussionResult = await run_in_threadpool(
            get_saved_discussion,
            discussion_id,
        )    
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

    metadata = discussion.config.metadata or {}
    camps = metadata.get("camps", {})
    persona_files_map = metadata.get("persona_files", {})
    project_root = Path(__file__).resolve().parents[2]

    import yaml
    agents = []
    for aid in discussion.config.agent_ids:
        p_path = persona_files_map.get(aid, f"personas/{aid}.yaml")
        name = ""
        role = ""
        camp = ""

        if camps:
            for c_key in ["camp_a", "camp_b"]:
                c_data = camps.get(c_key, {})
                for r_key in ["coach", "fan", "pundit"]:
                    if c_data.get(r_key) == aid:
                        role = r_key
                        camp = c_data.get("name", c_key)
                        break

        try:
            yaml_p = Path(p_path)
            if not yaml_p.is_absolute():
                yaml_p = project_root / yaml_p
            if yaml_p.exists():
                with open(yaml_p, "r", encoding="utf-8") as f:
                    y_data = yaml.safe_load(f) or {}
                    if isinstance(y_data, dict):
                        name = y_data.get("name", "")
                        if not role and "role" in y_data:
                            role = y_data["role"]
        except Exception:
            pass

        if not name:
            name = aid.replace("_", " ").title()
        if not role:
            for r in ["coach", "fan", "pundit"]:
                if r in aid.lower():
                    role = r
                    break

        agents.append(
            AgentInfo(
                agent_id=aid,
                persona_file=p_path,
                name=name,
                role=role,
                camp=camp,
            )
        )

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
        metadata=discussion.config.metadata or {},
    )


# ── 6. Discussion Status ──
@router.get(
    "/discussions/{discussion_id}/status",
    response_model=DiscussionStatusResponse,
    tags=["Discussions"],
    summary="Check discussion execution status",
)
async def get_discussion_status(discussion_id: str):
    """Return runtime status and saved checkpoint progress."""
    from src.api.services.discussion_service import (
        get_discussion_status_record,
    )

    try:
        return await run_in_threadpool(
            get_discussion_status_record,
            discussion_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        )

# ── 7. Discussion Analytics ──
@router.get(
    "/discussions/{discussion_id}/analytics",
    response_model=AnalyticsResponse,
    tags=["Analytics"],
    summary="Get analytics for a discussion",
)
async def get_analytics(discussion_id: str):
    """Return cached or newly calculated discussion analytics."""
    from src.api.services.analytics_service import (
        get_discussion_analytics,
    )

    try:
        return await get_discussion_analytics(discussion_id)

    except FileNotFoundError:
        logger.info(
            "Analytics requested for missing discussion: %s",
            discussion_id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Discussion '{discussion_id}' not found.",
        )

    except ValueError as exc:
        logger.warning(
            "Rejected analytics request for %s: %s",
            discussion_id,
            exc,
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid discussion ID or discussion/analytics data.",
        )

    except RuntimeError as exc:
        logger.warning(
            "Analytics temporarily unavailable for %s: %s",
            discussion_id,
            exc,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Analytics are temporarily unavailable. Please retry.",
        )

    except Exception:
        logger.exception(
            "Unexpected analytics failure for %s",
            discussion_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Analytics processing failed. Check the server logs.",
        )


# ── 8. Discussion Causal Counterfactual Analysis ──
@router.post(
    "/discussions/{discussion_id}/causal-analysis",
    tags=["Analytics"],
    summary="Run or retrieve counterfactual causal ablation analysis",
)
@router.get(
    "/discussions/{discussion_id}/causal-analysis",
    tags=["Analytics"],
    summary="Get counterfactual causal ablation analysis",
)
async def get_causal_analysis(discussion_id: str):
    """Compute or load cached counterfactual causal ablation for a discussion."""
    from src.api.services.analytics_service import (
        get_discussion_causal_analysis,
    )

    try:
        return await get_discussion_causal_analysis(discussion_id)

    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Discussion '{discussion_id}' not found.",
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    except Exception as exc:
        logger.exception("Causal analysis failed for %s", discussion_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Causal analysis failed: {exc}",
        )


@router.post(
    "/discussions/{discussion_id}/synthesis",
    tags=["Analytics"],
    summary="Generate or retrieve LLM executive summary and agent commentary synthesis",
)
@router.get(
    "/discussions/{discussion_id}/synthesis",
    tags=["Analytics"],
    summary="Get LLM executive summary and agent commentary synthesis",
)
async def get_or_compute_synthesis_route(discussion_id: str):
    """Retrieve or generate LLM executive summary and agent commentary synthesis."""
    from src.api.services.analytics_service import get_discussion_synthesis

    try:
        return await get_discussion_synthesis(discussion_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Discussion '{discussion_id}' not found.",
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    except Exception as exc:
        logger.exception("Synthesis failed for %s", discussion_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Synthesis failed: {exc}",
        )