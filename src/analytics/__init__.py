"""Week 4 Analytics & Intelligence Layer."""

from .agreement import compute_discussion_agreement, compute_round_agreement
from .causal_influence import compute_counterfactual_influence
from .engine import AnalyticsEngine
from .influence import compute_agent_influence
from .models import (
    AgentCausalInfluence,
    AgentInfluence,
    AgentStancePoint,
    CounterfactualExchange,
    DiscussionAgreementResult,
    DiscussionCausalResult,
    DiscussionInfluenceResult,
    OpinionTrajectoryResult,
    RoundAgreement,
)
from .stance import compute_opinion_trajectories, extract_numeric_stance
__all__ = [
    "AgentCausalInfluence",
    "AgentInfluence",
    "AgentStancePoint",
    "AnalyticsEngine",
    "CounterfactualExchange",
    "DiscussionAgreementResult",
    "DiscussionCausalResult",
    "DiscussionInfluenceResult",
    "OpinionTrajectoryResult",
    "RoundAgreement",
    "compute_agent_influence",
    "compute_counterfactual_influence",
    "compute_discussion_agreement",
    "compute_opinion_trajectories",
    "compute_round_agreement",
    "extract_numeric_stance",
]
