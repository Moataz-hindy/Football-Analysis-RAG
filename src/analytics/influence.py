"""Observed convergence after routed messages; association, not causal attribution.

Pull(a -> b, r) = |a(r-1) - b(r-1)| - |a(r-1) - b(r)|.
Scores clip each distance reduction to [-1, 1] and average eligible exchanges.
Missing routes or stances remain insufficient data; no links are invented.
"""
from src.discussion.types import DiscussionResult
from .models import AgentInfluence, DiscussionInfluenceResult
from .stance import compute_opinion_trajectories


def compute_agent_influence(discussion_input, trajectories=None):
    if isinstance(discussion_input, DiscussionResult):
        data = discussion_input.to_dict()
    elif isinstance(discussion_input, dict):
        data = discussion_input
    else:
        raise TypeError('Expected DiscussionResult or dict')
    config = data.get('config', {})
    traj = trajectories if trajectories is not None else compute_opinion_trajectories(data)
    agent_ids = list(config.get('agent_ids') or traj.agent_ids or sorted(traj.trajectories))
    pulls = {aid: {} for aid in agent_ids}
    opportunities = {aid: 0 for aid in agent_ids}
    movements = {aid: [] for aid in agent_ids}
    links = set()
    for msg in data.get('messages', []):
        sender = msg.get('sender_id')
        if sender not in pulls:
            continue
        for recipient in msg.get('recipient_ids', []):
            if recipient in pulls and recipient != sender:
                links.add((int(msg.get('round_num', 0)), sender, recipient))
    for round_num, sender, recipient in sorted(links):
        previous = traj.get_round_stances(round_num)
        current = traj.get_round_stances(round_num + 1)
        opportunities[sender] += 1
        if sender not in previous or recipient not in previous or recipient not in current:
            continue
        old_distance = abs(previous[sender] - previous[recipient])
        new_distance = abs(previous[sender] - current[recipient])
        pull = max(-1.0, min(1.0, old_distance - new_distance))
        pulls[sender].setdefault(recipient, []).append(pull)
        movements[sender].append(abs(current[recipient] - previous[recipient]))
    results = {}
    for aid in agent_ids:
        values = [v for group in pulls[aid].values() for v in group]
        if not values:
            status, score = 'insufficient_data', None
            rationale = 'No recorded route with comparable recipient stances in consecutive rounds.'
        elif all(m < 1e-4 for m in movements[aid]):
            status, score = 'zero_movement', None
            rationale = 'Recipients remained rigid; no observed movement to estimate influence.'
        else:
            status = 'valid'
            score = round(sum(values) / len(values), 4)
            rationale = ('Associated with recipient convergence; does not establish persuasion.' if score > 0
                         else 'Associated with recipient divergence (possible reactance); not causal evidence.' if score < 0
                         else 'No net distance reduction across observed exchanges.')
        results[aid] = AgentInfluence(
            agent_id=aid, influence_score=score, status=status, total_pull=round(sum(values), 4),
            interaction_count=opportunities[aid],
            recipient_pulls={rec: round(sum(vals), 4) for rec, vals in pulls[aid].items()},
            rationale=rationale,
        )
    positive = [(aid, inf.influence_score) for aid, inf in results.items()
                if inf.status == 'valid' and inf.influence_score > 0]
    positive.sort(key=lambda item: (-item[1], item[0]))
    top = positive[0][0] if positive else None
    measured = [inf for inf in results.values() if inf.status != 'insufficient_data']
    dynamic = ('Observed Convergence' if top else
               'Rigid Deliberation (Zero Stance Movement)' if measured and all(inf.status == 'zero_movement' for inf in measured)
               else 'Dispersed Dynamic' if measured else 'Insufficient Data')
    return DiscussionInfluenceResult(
        discussion_id=str(config.get('discussion_id', 'unknown')), agent_influences=results,
        top_influencer=top, discussion_dynamic=dynamic,
        metadata={'method': 'clipped_distance_reduction', 'routing': 'recorded_messages_only',
                  'experimental': True, 'multiple_senders': 'The same recipient movement may be associated with multiple senders; attribution is not unique.'},
    )
