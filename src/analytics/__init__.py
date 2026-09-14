"""Week 4 Analytics & Intelligence Layer."""

from .agreement import compute_discussion_agreement, compute_round_agreement
from .influence import compute_agent_influence
from .models import (
    AgentInfluence,
    AgentStancePoint,
    DiscussionAgreementResult,
    DiscussionInfluenceResult,
    OpinionTrajectoryResult,
    RoundAgreement,
)
from .stance import compute_opinion_trajectories, extract_numeric_stance

__all__ = [
    "AgentInfluence",
    "AgentStancePoint",
    "DiscussionAgreementResult",
    "DiscussionInfluenceResult",
    "OpinionTrajectoryResult",
    "RoundAgreement",
    "compute_agent_influence",
    "compute_discussion_agreement",
    "compute_opinion_trajectories",
    "compute_round_agreement",
    "extract_numeric_stance",
]
