"""Pydantic data models for Week 4 discussion analytics."""

from typing import Any
from pydantic import BaseModel, Field


class AgentStancePoint(BaseModel):
    """A single numeric stance point for an agent at a specific discussion round."""

    agent_id: str
    round_num: int
    stance_value: float = Field(
        ...,
        ge=-1.0,
        le=1.0,
        description="Continuous numeric stance score in [-1.0, 1.0]. +1.0 = pure sporting merit; -1.0 = officiating injustice.",
    )
    opinion_change: float | None = Field(
        default=None,
        description="Round-to-round delta: Stance(round) - Stance(round-1). None for round 0.",
    )
    stance_text: str = Field(default="", description="Original qualitative stance text from snapshot.")
    changed_from_previous: bool = Field(default=False, description="Whether opinion evolved from previous round.")
    change_reason: str = Field(default="", description="Stated or inferred rationale for stance change.")
    metadata: dict[str, Any] = Field(default_factory=dict)


class OpinionTrajectoryResult(BaseModel):
    """Full per-agent, per-round opinion trajectory across a discussion."""

    discussion_id: str
    topic: str = Field(default="")
    total_rounds: int = Field(default=3)
    agent_ids: list[str] = Field(default_factory=list)
    trajectories: dict[str, list[AgentStancePoint]] = Field(
        default_factory=dict,
        description="Mapping from agent_id to chronological list of AgentStancePoint (R0 through RN).",
    )
    metadata: dict[str, Any] = Field(default_factory=dict)

    def get_stance_series(self, agent_id: str) -> list[float]:
        """Return the raw numeric stance series for a given agent across rounds."""
        points = self.trajectories.get(agent_id, [])
        return [p.stance_value for p in points]

    def get_round_stances(self, round_num: int) -> dict[str, float]:
        """Return all agent stances for a specific round."""
        result = {}
        for agent_id, points in self.trajectories.items():
            for p in points:
                if p.round_num == round_num:
                    result[agent_id] = p.stance_value
                    break
        return result


class RoundAgreement(BaseModel):
    """Agreement and dispersion metrics for a single discussion round."""

    round_num: int
    agreement_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Normalized agreement score in [0.0, 1.0]. 1.0 = unanimous consensus; 0.0 = maximum polarization.",
    )
    mean_distance: float = Field(
        ...,
        ge=0.0,
        le=2.0,
        description="Average pairwise stance distance D_bar across all participating agent pairs in the round.",
    )
    variance: float = Field(
        default=0.0,
        ge=0.0,
        description="Variance of agent stances in the round.",
    )
    agent_count: int = Field(default=0, description="Number of agents evaluated in this round.")
    interpretation: str = Field(
        default="",
        description="Qualitative categorization: e.g. 'Unanimous Consensus', 'Substantial Alignment', 'Moderate Debate', 'Polarized'.",
    )
    pairwise_distances: dict[str, float] = Field(
        default_factory=dict,
        description="Detailed pairwise distances for all agent pairs (e.g. 'agent_a vs agent_b': 0.85).",
    )


class DiscussionAgreementResult(BaseModel):
    """Per-round agreement progression and group cohesion trends across an entire discussion."""

    discussion_id: str
    total_rounds: int = Field(default=0)
    round_agreements: list[RoundAgreement] = Field(default_factory=list)
    mean_discussion_agreement: float = Field(default=0.0, ge=0.0, le=1.0)
    overall_trend: str = Field(
        default="Stable",
        description="'Converging' (cohesion increased), 'Diverging' (polarization increased), or 'Stable'.",
    )
    metadata: dict[str, Any] = Field(default_factory=dict)

    def get_round_agreement(self, round_num: int) -> RoundAgreement | None:
        """Retrieve RoundAgreement by round number."""
        for ra in self.round_agreements:
            if ra.round_num == round_num:
                return ra
        return None

    def get_agreement_series(self) -> list[float]:
        """Return list of scalar agreement scores chronologically [A_0, A_1, ..., A_R]."""
        return [ra.agreement_score for ra in self.round_agreements]


class AgentInfluence(BaseModel):
    """Influence metrics for an individual agent across a discussion."""

    agent_id: str
    influence_score: float | None = Field(
        default=None,
        description="Correlation / convergence pull score in [-1.0, 1.0], or None if insufficient variance.",
    )
    status: str = Field(
        default="valid",
        description="'valid', 'zero_movement', or 'insufficient_data'.",
    )
    total_pull: float = Field(default=0.0, description="Sum of directional stance pulls on recipients.")
    interaction_count: int = Field(default=0, description="Total directed message opportunities (sender -> recipient).")
    recipient_pulls: dict[str, float] = Field(
        default_factory=dict,
        description="Detailed pull exerted on each specific recipient {recipient_id: net_pull}.",
    )
    rationale: str = Field(
        default="",
        description="Human-readable explanation of the agent's influence or reason for insufficient data.",
    )


class DiscussionInfluenceResult(BaseModel):
    """Overall influence distribution across all agents in a discussion."""

    discussion_id: str
    agent_influences: dict[str, AgentInfluence] = Field(
        default_factory=dict,
        description="Mapping from agent_id to AgentInfluence.",
    )
    top_influencer: str | None = Field(
        default=None,
        description="agent_id of the most influential agent, or None if zero movement.",
    )
    discussion_dynamic: str = Field(
        default="Stable Deliberation",
        description="Summary of influence dynamics: e.g. 'Active Persuasion', 'Rigid Deliberation (No Movement)', etc.",
    )
    causation_disclaimer: str = Field(
        default="Statistical association: Reflects correlation between message routing and subsequent stance shifts; does not establish cognitive causation.",
    )
    metadata: dict[str, Any] = Field(default_factory=dict)

    def get_influence_score(self, agent_id: str) -> float | None:
        """Get scalar influence score for a specific agent."""
        inf = self.agent_influences.get(agent_id)
        return inf.influence_score if inf else None

    def get_ranked_influencers(self) -> list[tuple[str, float]]:
        """Return list of (agent_id, score) sorted from most influential to least."""
        scored = [
            (aid, inf.influence_score)
            for aid, inf in self.agent_influences.items()
            if inf.influence_score is not None
        ]
        return sorted(scored, key=lambda item: item[1], reverse=True)

