"""Pydantic v2 schemas for the Football Analysis Platform API."""

from typing import Any, Literal
from pydantic import BaseModel, Field


# ── Health Check ──
class HealthResponse(BaseModel):
    status: str = "ok"


# ── Topics ──
class TopicItem(BaseModel):
    id: str
    label: str
    description: str = ""


class TopicsResponse(BaseModel):
    topics: list[TopicItem]


# ── Discussion Summary (for list endpoint) ──
class DiscussionSummary(BaseModel):
    discussion_id: str
    topic: str
    num_agents: int
    num_rounds: int
    num_messages: int
    timestamp: str = ""


class DiscussionListResponse(BaseModel):
    discussions: list[DiscussionSummary]


# ── Single Discussion Detail ──
class MessageOut(BaseModel):
    round_num: int
    sender_id: str
    recipient_ids: list[str] = Field(default_factory=list)
    content: str
    sentiment_score: float | None = None
    sentiment_label: str | None = None
    timestamp: str = ""


class AgentInfo(BaseModel):
    agent_id: str
    persona_file: str = ""
    name: str = ""
    role: str = ""
    camp: str = ""


class DiscussionDetailResponse(BaseModel):
    discussion_id: str
    topic: str
    agents: list[AgentInfo]
    num_rounds: int
    graph: dict[str, list[str]] = Field(default_factory=dict)
    messages: list[MessageOut]
    timestamp: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


# ── Start Discussion ──
class StartDiscussionRequest(BaseModel):
    topic: str = Field(min_length=1)
    num_rounds: int = Field(default=3, ge=3, le=10)
    discussion_id: str | None = Field(
        default=None,
        pattern=r"^[A-Za-z0-9_-]+$",
    )
    dynamic_personas: bool = Field(
        default=True,
        description="Whether to generate dynamic 3v3 polarized personas via LLM.",
    )
    force_regenerate: bool = Field(
        default=False,
        description="Force regeneration of dynamic personas if cached.",
    )



class StartDiscussionResponse(BaseModel):
    discussion_id: str
    status: Literal["queued", "running", "completed", "failed"]
    message: str = ""


# ── Discussion Status ──
class DiscussionStatusResponse(BaseModel):
    discussion_id: str
    status: Literal[
        "queued",
        "running",
        "completed",
        "failed",
        "not_found",
        "unknown",
    ]
    current_round: int | None = None
    total_rounds: int | None = None
    message: str = ""


# ── Analytics ──
class StancePointOut(BaseModel):
    agent_id: str
    round_num: int
    stance_value: float | None = None
    opinion_change: float | None = None
    stance_text: str = ""


class RoundAgreementOut(BaseModel):
    round_num: int
    agreement_score: float | None = None
    mean_distance: float | None = None
    variance: float = 0.0
    interpretation: str = ""


class AgentInfluenceOut(BaseModel):
    agent_id: str
    influence_score: float | None = None
    status: str = "valid"
    rationale: str = ""


class SentimentOut(BaseModel):
    round_num: int
    sender_id: str
    sentiment_score: float | None = None
    sentiment_label: str | None = None


class AnalyticsResponse(BaseModel):
    discussion_id: str
    topic: str = ""
    opinion_trajectories: dict[str, list[StancePointOut]] = Field(default_factory=dict)
    agreement: list[RoundAgreementOut] = Field(default_factory=list)
    mean_agreement: float | None = None
    overall_trend: str = ""
    influence: list[AgentInfluenceOut] = Field(default_factory=list)
    top_influencer: str | None = None
    sentiment: list[SentimentOut] = Field(default_factory=list)
    interaction_graph: dict[str, list[str]] = Field(default_factory=dict)
    cached: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
    causal_influence: dict[str, Any] | None = None


# ── Generic Error ──
class ErrorResponse(BaseModel):
    error: str
    detail: str = ""
