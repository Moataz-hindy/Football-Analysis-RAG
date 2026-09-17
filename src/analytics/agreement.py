"""Task 2: Per-Round Agreement / Disagreement Metric Analysis.

Measures studio panel cohesion and polarization at each discussion round using
mean pairwise stance dispersion:
    D_{ij, r} = |S_{i, r} - S_{j, r}|
    \\bar{D}_r = (1 / \\binom{N}{2}) * \\sum_{i < j} D_{ij, r}
    A_r = 1.0 - (\\bar{D}_r / 2.0)
"""

import itertools
import math
import logging
from typing import Any

from src.discussion.types import DiscussionResult
from .models import (
    DiscussionAgreementResult,
    OpinionTrajectoryResult,
    RoundAgreement,
)
from .stance import compute_opinion_trajectories

logger = logging.getLogger(__name__)


def interpret_agreement(score: float) -> str:
    """Categorize agreement score into intuitive studio dynamic description."""
    if score == 1.0:
        return "Unanimous Consensus"
    elif score >= 0.90:
        return "High Alignment"
    elif score >= 0.75:
        return "Strong Alignment"
    elif score >= 0.55:
        return "Moderate Debate"
    elif score >= 0.35:
        return "Significant Polarization"
    else:
        return "Extreme Polarization"


def compute_round_agreement(
    round_num: int,
    stances: dict[str, float] | list[float],
) -> RoundAgreement:
    """
    Compute scalar agreement score A_r and dispersion metrics for a single round.

    Parameters:
    -----------
    round_num: int
        The index of the discussion round (0, 1, 2, ...).
    stances: dict[str, float] or list[float]
        Either a mapping of {agent_id: stance_value} or a list of stance values in [-1.0, 1.0].

    Returns:
    --------
    RoundAgreement:
        Pydantic model with agreement_score, mean_distance, variance, agent_count, etc.
    """
    if isinstance(stances, dict):
        agent_names = list(stances.keys())
        values = [float(v) for v in stances.values()]
    elif isinstance(stances, list):
        agent_names = [f"agent_{idx}" for idx in range(len(stances))]
        values = [float(v) for v in stances]
    else:
        raise TypeError(f"Expected dict or list for stances, got {type(stances).__name__}")

    if any(not math.isfinite(v) or not -1 <= v <= 1 for v in values):
        raise ValueError("Stances must be finite and between -1 and 1")
    n = len(values)
    if n == 0:
        return RoundAgreement(
            round_num=round_num,
            agreement_score=None,
            mean_distance=None,
            variance=0.0,
            agent_count=0,
            interpretation="No Data",
            pairwise_distances={},
        )

    if n == 1:
        return RoundAgreement(
            round_num=round_num,
            agreement_score=None,
            mean_distance=None,
            variance=0.0,
            agent_count=1,
            interpretation="Single Agent / Uncontested",
            pairwise_distances={},
        )

    # 1. Compute all unique pairwise distances
    pairwise: dict[str, float] = {}
    pair_distances: list[float] = []

    for (i, name_i), (j, name_j) in itertools.combinations(enumerate(agent_names), 2):
        dist = round(abs(values[i] - values[j]), 4)
        pair_distances.append(dist)
        pairwise[f"{name_i} vs {name_j}"] = dist

    # 2. Mean Pairwise Dispersion (\bar{D}_r)
    mean_dist = sum(pair_distances) / len(pair_distances)

    # 3. Stance Variance (\sigma_r^2)
    mean_val = sum(values) / n
    variance = sum((v - mean_val) ** 2 for v in values) / n

    # 4. Normalized Agreement Score (A_r = 1.0 - \bar{D}_r / 2.0)
    agreement_score = max(0.0, min(1.0, 1.0 - (mean_dist / 2.0)))

    final_score = round(agreement_score, 4)
    final_mean_dist = round(mean_dist, 4)
    final_variance = round(variance, 4)
    interp = interpret_agreement(final_score)

    return RoundAgreement(
        round_num=round_num,
        agreement_score=final_score,
        mean_distance=final_mean_dist,
        variance=final_variance,
        agent_count=n,
        interpretation=interp,
        pairwise_distances=pairwise,
    )


def compute_discussion_agreement(
    discussion_input: DiscussionResult | OpinionTrajectoryResult | dict[str, Any],
    trajectories: OpinionTrajectoryResult | None = None,
) -> DiscussionAgreementResult:
    """
    Compute per-round agreement scores across an entire discussion.

    Parameters:
    -----------
    discussion_input: DiscussionResult, OpinionTrajectoryResult, or dict
        The discussion data or pre-computed trajectories.
    trajectories: OpinionTrajectoryResult, optional
        Pre-computed trajectories from Task 1. If not provided and input is not
        OpinionTrajectoryResult, compute_opinion_trajectories will be called.

    Returns:
    --------
    DiscussionAgreementResult:
        Typed object containing list of RoundAgreement for every round, mean agreement, and trend.
    """
    if isinstance(discussion_input, OpinionTrajectoryResult):
        traj_res = discussion_input
        discussion_id = traj_res.discussion_id
        total_rounds = traj_res.total_rounds
    elif trajectories is not None:
        traj_res = trajectories
        if isinstance(discussion_input, DiscussionResult):
            discussion_id = discussion_input.config.discussion_id
        elif isinstance(discussion_input, dict):
            discussion_id = str(discussion_input.get("config", {}).get("discussion_id", traj_res.discussion_id))
        else:
            discussion_id = traj_res.discussion_id
        total_rounds = traj_res.total_rounds
    else:
        traj_res = compute_opinion_trajectories(discussion_input)
        discussion_id = traj_res.discussion_id
        total_rounds = traj_res.total_rounds

    if not traj_res.trajectories:
        return DiscussionAgreementResult(
            discussion_id=discussion_id,
            total_rounds=total_rounds,
            round_agreements=[],
            mean_discussion_agreement=None,
            overall_trend="Insufficient Data",
        )

    # Find maximum round number present in data
    max_round = 0
    for pts in traj_res.trajectories.values():
        for p in pts:
            if p.round_num > max_round:
                max_round = p.round_num

    round_agreements: list[RoundAgreement] = []
    for r in range(max_round + 1):
        stances_r = traj_res.get_round_stances(r)
        if stances_r:
            ra = compute_round_agreement(round_num=r, stances=stances_r)
            round_agreements.append(ra)

    # Compute overall metrics
    measured = [ra for ra in round_agreements if ra.agreement_score is not None]
    if measured:
        mean_agr = round(sum(ra.agreement_score for ra in measured) / len(measured), 4)
        first_score = measured[0].agreement_score
        last_score = measured[-1].agreement_score
        delta = round(last_score - first_score, 4)

        if len(measured) < 2 or len({tuple(sorted(traj_res.get_round_stances(ra.round_num))) for ra in measured}) > 1:
            trend = "Insufficient Comparable Data"
        elif delta >= 0.05:
            trend = "Converging"
        elif delta <= -0.05:
            trend = "Diverging"
        else:
            trend = "Stable"
    else:
        mean_agr = None
        trend = "Insufficient Data"

    return DiscussionAgreementResult(
        discussion_id=discussion_id,
        total_rounds=len(round_agreements),
        round_agreements=round_agreements,
        mean_discussion_agreement=mean_agr,
        overall_trend=trend,
    )
