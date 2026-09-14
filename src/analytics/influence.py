"""Task 3: Per-Agent Influence Scores & Network Opinion Dynamics.

Measures how much each agent's contributions appear to move the opinions of peers
using directed message routing and subsequent round-to-round stance shifts:
    Target Direction = sign(S_{a, r-1} - S_{b, r-1})
    Pull_{a -> b, r} = \\Delta S_{b, r} * Target Direction

Follows DeGroot-style opinion dynamics over directed communication graphs.
Handles zero-movement and insufficient variance discussions explicitly per Week 4 Section 16.
"""

import logging
from typing import Any

from src.discussion.types import DiscussionResult
from .models import (
    AgentInfluence,
    DiscussionInfluenceResult,
    OpinionTrajectoryResult,
)
from .stance import compute_opinion_trajectories

logger = logging.getLogger(__name__)


def compute_agent_influence(
    discussion_input: DiscussionResult | dict[str, Any],
    trajectories: OpinionTrajectoryResult | None = None,
) -> DiscussionInfluenceResult:
    """
    Compute per-agent influence scores from message topology and stance deltas.

    Parameters:
    -----------
    discussion_input: DiscussionResult or dict
        Loaded discussion result containing config, messages, and opinions.
    trajectories: OpinionTrajectoryResult, optional
        Pre-computed trajectories from Task 1. If None, computes automatically.

    Returns:
    --------
    DiscussionInfluenceResult:
        Typed result containing per-agent influence metrics, top influencer, and dynamic summary.
    """
    if isinstance(discussion_input, DiscussionResult):
        data = discussion_input.to_dict()
    elif isinstance(discussion_input, dict):
        data = discussion_input
    else:
        raise TypeError(f"Expected DiscussionResult or dict, got {type(discussion_input).__name__}")

    config = data.get("config", {})
    discussion_id = str(config.get("discussion_id", "unknown"))
    agent_ids = list(config.get("agent_ids", []))
    raw_messages = data.get("messages", [])

    # 1. Obtain opinion trajectories from Task 1
    if trajectories is None:
        traj_res = compute_opinion_trajectories(data)
    else:
        traj_res = trajectories

    if not agent_ids and traj_res.agent_ids:
        agent_ids = list(traj_res.agent_ids)

    # 2. Check for overall movement across the discussion
    total_discussion_movement = 0.0
    for pts in traj_res.trajectories.values():
        for p in pts:
            if p.opinion_change is not None:
                total_discussion_movement += abs(p.opinion_change)

    # If no agent moved whatsoever (e.g. all maintained their original opinions)
    if total_discussion_movement < 1e-4:
        logger.info("Discussion %s exhibits zero opinion movement. Returning zero_movement status.", discussion_id)
        agent_influences: dict[str, AgentInfluence] = {}
        for aid in agent_ids:
            agent_influences[aid] = AgentInfluence(
                agent_id=aid,
                influence_score=None,
                status="zero_movement",
                total_pull=0.0,
                interaction_count=0,
                recipient_pulls={},
                rationale=(
                    f"Agent '{aid}' deliberated in a rigid discussion where no participating "
                    "agent shifted stance (total discussion delta = 0.0). Insufficient stance variance "
                    "to measure directional influence."
                ),
            )
        return DiscussionInfluenceResult(
            discussion_id=discussion_id,
            agent_influences=agent_influences,
            top_influencer=None,
            discussion_dynamic="Rigid Deliberation (Zero Stance Movement)",
        )

    # 3. Index messages by round_num and sender_id -> recipient_ids
    # Message sent in round (r - 1) informs opinion shift in round r
    directed_links_by_round: dict[int, list[tuple[str, str]]] = {}
    for msg in raw_messages:
        r_msg = int(msg.get("round_num", 0))
        sender = str(msg.get("sender_id", ""))
        recipients = msg.get("recipient_ids", [])
        if not sender:
            continue
        for rec in recipients:
            if rec and rec != sender:
                directed_links_by_round.setdefault(r_msg, []).append((sender, str(rec)))

    # Find max round number in trajectories
    max_round = 0
    for pts in traj_res.trajectories.values():
        for p in pts:
            if p.round_num > max_round:
                max_round = p.round_num

    # If raw_messages was empty, fall back to complete network broadcast
    if not raw_messages and max_round > 0:
        for r_idx in range(max_round):
            for a in agent_ids:
                for b in agent_ids:
                    if a != b:
                        directed_links_by_round.setdefault(r_idx, []).append((a, b))

    # 4. Map message links to subsequent round stance changes
    pulls_by_sender: dict[str, dict[str, list[float]]] = {aid: {} for aid in agent_ids}
    interaction_counts: dict[str, int] = {aid: 0 for aid in agent_ids}

    for r in range(1, max_round + 1):
        prev_round = r - 1
        links = directed_links_by_round.get(prev_round, [])
        prev_stances = traj_res.get_round_stances(prev_round)
        curr_stances = traj_res.get_round_stances(r)

        unique_pairs = set(links)

        for sender, recipient in unique_pairs:
            if sender not in pulls_by_sender:
                pulls_by_sender[sender] = {}
                interaction_counts[sender] = 0

            interaction_counts[sender] += 1

            s_sender_prev = prev_stances.get(sender)
            s_rec_prev = prev_stances.get(recipient)
            s_rec_curr = curr_stances.get(recipient)

            if s_sender_prev is None or s_rec_prev is None or s_rec_curr is None:
                continue

            delta_recipient = s_rec_curr - s_rec_prev
            distance_prev = s_sender_prev - s_rec_prev

            # If recipient did not move, pull is 0.0
            if abs(delta_recipient) < 1e-4:
                pulls_by_sender[sender].setdefault(recipient, []).append(0.0)
                continue

            # If they were already at the exact same stance, distance is 0
            if abs(distance_prev) < 1e-4:
                pulls_by_sender[sender].setdefault(recipient, []).append(0.0)
                continue

            target_direction = 1.0 if distance_prev > 0 else -1.0
            raw_pull = delta_recipient * target_direction

            # Clamp pull within [-1.0, 1.0] to prevent outlier distortion
            clamped_pull = max(-1.0, min(1.0, raw_pull))
            pulls_by_sender[sender].setdefault(recipient, []).append(clamped_pull)

    # 5. Aggregate metrics for each agent
    agent_influences: dict[str, AgentInfluence] = {}

    for aid in agent_ids:
        rec_dict = pulls_by_sender.get(aid, {})
        n_interactions = interaction_counts.get(aid, 0)

        recipient_pulls_agg: dict[str, float] = {}
        all_pulls: list[float] = []

        for rec, pull_list in rec_dict.items():
            net_rec_pull = sum(pull_list)
            recipient_pulls_agg[rec] = round(net_rec_pull, 3)
            all_pulls.extend(pull_list)

        total_pull = sum(all_pulls)

        if n_interactions > 0 and len(all_pulls) > 0:
            avg_pull = total_pull / len(all_pulls)
            score = round(max(-1.0, min(1.0, avg_pull)), 3)
            status = "valid"
            if score > 0.10:
                rationale = (
                    f"Consistently persuaded peers toward their stance (average positive pull of {score:+.2f} "
                    f"across {n_interactions} directed communication exchanges)."
                )
            elif score < -0.10:
                rationale = (
                    f"Associated with peer reactance/backfire effect (average negative pull of {score:+.2f}; "
                    "recipients shifted further away from stance)."
                )
            else:
                rationale = (
                    f"Neutral persuasive impact (average pull of {score:+.2f}; recipients maintained or exhibited "
                    "balanced drift)."
                )
        else:
            score = 0.0
            status = "insufficient_data"
            rationale = "No measurable directed communication opportunities with responsive peers."

        agent_influences[aid] = AgentInfluence(
            agent_id=aid,
            influence_score=score,
            status=status,
            total_pull=round(total_pull, 3),
            interaction_count=n_interactions,
            recipient_pulls=recipient_pulls_agg,
            rationale=rationale,
        )

    # 6. Determine top influencer
    valid_scores = [
        (aid, inf.influence_score)
        for aid, inf in agent_influences.items()
        if inf.influence_score is not None and inf.status == "valid"
    ]
    top_influencer = None
    if valid_scores:
        valid_scores.sort(key=lambda item: item[1], reverse=True)
        if valid_scores[0][1] > 0.0:
            top_influencer = valid_scores[0][0]

    dynamic_summary = "Active Persuasion & Convergence" if top_influencer else "Dispersed Dynamic"

    return DiscussionInfluenceResult(
        discussion_id=discussion_id,
        agent_influences=agent_influences,
        top_influencer=top_influencer,
        discussion_dynamic=dynamic_summary,
    )
