"""Pydantic v2 schemas for the Football Analysis Platform API."""

import re
from typing import Any, Literal
from pydantic import BaseModel, Field, field_validator, model_validator


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
    status: str = "unknown"


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
    num_rounds: int = Field(default=3, ge=1, le=10)
    discussion_id: str | None = Field(default=None, description="Discussion ID. Spaces are automatically sanitized.")
    num_agents: int = Field(
        default=6,
        ge=2,
        le=6,
        description="Number of specialist agents in the deliberation (2-6, default 6).",
    )
    dynamic_personas: bool = Field(
        default=False,
        description="Whether to generate dynamic 3v3 polarized personas via LLM (defaults to the 6 specialist system personas).",
    )
    persona_ids: list[str] | None = Field(
        default=None,
        description="Explicit list of persona IDs (system or custom user personas) to participate in the deliberation.",
    )
    camp_a_ids: list[str] | None = Field(
        default=None,
        description="Explicit list of persona IDs assigned to Camp A (Thesis / Home).",
    )
    camp_b_ids: list[str] | None = Field(
        default=None,
        description="Explicit list of persona IDs assigned to Camp B (Antithesis / Away).",
    )
    force_regenerate: bool = Field(
        default=False,
        description="Force regeneration of dynamic personas if cached.",
    )

    @field_validator("persona_ids", "camp_a_ids", "camp_b_ids")
    @classmethod
    def clean_string_list(cls, v: list[str] | None) -> list[str] | None:
        if v is not None:
            return [p.strip() for p in v if isinstance(p, str) and p.strip()]
        return v

    @model_validator(mode="after")
    def validate_camps_and_roster(self) -> "StartDiscussionRequest":
        if self.camp_a_ids is not None or self.camp_b_ids is not None:
            a_ids = self.camp_a_ids or []
            b_ids = self.camp_b_ids or []
            if len(a_ids) < 1 or len(b_ids) < 1:
                raise ValueError("Both Camp A and Camp B must have at least 1 agent.")
            if len(set(a_ids)) != len(a_ids):
                raise ValueError("Duplicate persona IDs in Camp A are not allowed.")
            if len(set(b_ids)) != len(b_ids):
                raise ValueError("Duplicate persona IDs in Camp B are not allowed.")
            overlap = set(a_ids).intersection(set(b_ids))
            if overlap:
                raise ValueError(f"Agent(s) {list(overlap)} cannot be assigned to both Camp A and Camp B.")
            total = len(a_ids) + len(b_ids)
            if total < 2 or total > 6:
                raise ValueError(f"Total curated agents across camps must be between 2 and 6 (received {total}).")
            self.persona_ids = a_ids + b_ids
        elif self.persona_ids is not None:
            cleaned = self.persona_ids
            if len(cleaned) < 2 or len(cleaned) > 6:
                raise ValueError(
                    f"Curated roster must contain between 2 and 6 personas (received {len(cleaned)})."
                )
            if len(set(cleaned)) != len(cleaned):
                raise ValueError("Duplicate persona IDs in curated roster are not allowed.")
        return self

    @field_validator("discussion_id", mode="before")
    @classmethod
    def sanitize_discussion_id(cls, v: Any) -> Any:
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return None
            # Automatically convert spaces and invalid chars to hyphens
            # so inputs like 'Argentina winning players-F2FG' become 'Argentina-winning-players-F2FG'
            cleaned = re.sub(r"[^A-Za-z0-9_-]+", "-", v).strip("-")
            return cleaned or None
        return v



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


# ── Strategic Advisor Decision ──
class AdvisorDecisionResponse(BaseModel):
    discussion_id: str
    topic: str
    topic_type: str = "Tactical Strategy"
    verdict_badge: str = "EXECUTIVE RULING"
    definitive_ruling: str
    confidence_score: float = 0.85
    deciding_factor: str
    action_plan: list[str] = Field(default_factory=list)
    primary_risk: str = ""
    mitigation_strategy: str = ""
    stakeholder_impacts: dict[str, str] = Field(default_factory=dict)


# ── Generic Error ──
class ErrorResponse(BaseModel):
    error: str
    detail: str = ""
