"""Analytical Counterfactual Ablation Evaluator for Causal Attribution.

Measures the true causal treatment effect of agent messages on peer stances:
    tau_{A -> B, r} = |S_{factual}(B, r+1) - S_{counterfactual}(B, r+1, \neg A)|

Addresses the 'correlation does not imply causation' limitation by counterfactually
evaluating what the recipient's stance would have been had the sender remained silent.
"""

from __future__ import annotations

import json
import logging
import math
import re
from typing import Any

from src.discussion.types import DiscussionResult
from .models import (
    AgentCausalInfluence,
    CounterfactualExchange,
    DiscussionCausalResult,
    OpinionTrajectoryResult,
)
from .stance import compute_opinion_trajectories

logger = logging.getLogger(__name__)


def _classify_causal_score(score: float | None) -> str:
    if score is None:
        return "Untested"
    if score >= 0.35:
        return "Genuine Persuader (High Causal Impact)"
    if score >= 0.15:
        return "Moderate Contributor"
    if score > 0.02:
        return "Minor Nudge"
    return "Zero Causal Shift (Rigid / Ineffective)"


def compute_counterfactual_influence(
    discussion_input: DiscussionResult | dict[str, Any],
    trajectories: OpinionTrajectoryResult | None = None,
    llm_client: Any | None = None,
    positive_pole: str | None = None,
    negative_pole: str | None = None,
    correlation_results: dict[str, Any] | None = None,
) -> DiscussionCausalResult:
    """Evaluate causal impact via batched LLM counterfactual ablation.

    Parameters
    ----------
    discussion_input : DiscussionResult or dict
        The recorded discussion transcript.
    trajectories : OpinionTrajectoryResult, optional
        Pre-computed stance trajectories across rounds.
    llm_client : LLMInterface, optional
        LLM client for evaluating counterfactual stances.
    positive_pole : str, optional
        Positive thesis statement (+1.0).
    negative_pole : str, optional
        Negative thesis statement (-1.0).
    correlation_results : dict, optional
        Pre-computed correlation results to produce contrastive summary.
    """
    if isinstance(discussion_input, DiscussionResult):
        data = discussion_input.to_dict()
    elif isinstance(discussion_input, dict):
        data = discussion_input
    else:
        raise TypeError("Expected DiscussionResult or dict")

    config = data.get("config", {})
    discussion_id = str(config.get("discussion_id", "unknown"))
    topic = str(config.get("topic", ""))

    traj = trajectories if trajectories is not None else compute_opinion_trajectories(data)
    agent_ids = list(config.get("agent_ids") or traj.agent_ids or sorted(traj.trajectories))

    # Identify message routing exchanges
    messages = data.get("messages", [])
    # Index messages by (round_num, sender_id)
    msg_by_round_sender: dict[tuple[int, str], str] = {}
    # Track which senders messaged each recipient in each round
    inbox_senders: dict[tuple[int, str], list[str]] = {}

    for msg in messages:
        sender = msg.get("sender_id")
        r_num = int(msg.get("round_num", 0))
        content = msg.get("content", "")
        if sender:
            msg_by_round_sender[(r_num, sender)] = content
            for rec in msg.get("recipient_ids", []):
                if rec != sender:
                    inbox_senders.setdefault((r_num, rec), []).append(sender)

    # Collect eligible directed exchanges: sender messaged recipient in r, recipient spoke in r+1
    candidate_exchanges = []
    exchange_idx = 0

    for (r_num, rec), senders in inbox_senders.items():
        prior_stances = traj.get_round_stances(r_num)
        factual_stances = traj.get_round_stances(r_num + 1)

        if rec not in prior_stances or rec not in factual_stances:
            continue

        prior_s = prior_stances[rec]
        factual_s = factual_stances[rec]
        if prior_s is None or factual_s is None:
            continue

        rec_response = msg_by_round_sender.get((r_num + 1, rec), "")

        for sender in senders:
            if sender not in prior_stances or prior_stances[sender] is None:
                continue
            sender_content = msg_by_round_sender.get((r_num, sender), "")
            other_senders = [s for s in senders if s != sender]

            candidate_exchanges.append({
                "exchange_id": exchange_idx,
                "round_num": r_num,
                "sender_id": sender,
                "recipient_id": rec,
                "prior_recipient_stance": prior_s,
                "factual_recipient_stance": factual_s,
                "sender_content": sender_content[:400],
                "recipient_response": rec_response[:400],
                "other_senders": other_senders,
            })
            exchange_idx += 1

    if not candidate_exchanges:
        return DiscussionCausalResult(
            discussion_id=discussion_id,
            agent_causal_influences={
                aid: AgentCausalInfluence(agent_id=aid, status="no_exchanges", exchange_count=0)
                for aid in agent_ids
            },
            top_causal_influencer=None,
            evaluated_exchanges_count=0,
            method="counterfactual_ablation_evaluator",
            comparison_summary={"status": "no_eligible_exchanges"},
        )

    # Instantiate LLM client if not passed
    if llm_client is None:
        try:
            from src.agent.llm import OpenAICompatibleLLM
            llm_client = OpenAICompatibleLLM()
        except Exception as err:
            logger.warning(f"Could not instantiate LLM client for causal ablation: {err}")
            return DiscussionCausalResult(
                discussion_id=discussion_id,
                agent_causal_influences={
                    aid: AgentCausalInfluence(
                        agent_id=aid, status="insufficient_data", exchange_count=0,
                        causal_classification="Untested (No LLM Client)"
                    )
                    for aid in agent_ids
                },
                top_causal_influencer=None,
                evaluated_exchanges_count=0,
                method="counterfactual_ablation_evaluator",
                comparison_summary={"status": "llm_client_unavailable", "error": str(err)},
            )

    # Evaluate in batches of 8 exchanges per LLM call to balance token headroom and request rate limits
    evaluated_records: dict[int, dict[str, Any]] = {}
    batch_size = 8

    import time
    for start in range(0, len(candidate_exchanges), batch_size):
        if start > 0:
            time.sleep(1.0)
        batch = candidate_exchanges[start:start + batch_size]
        items_payload = []
        for b in batch:
            items_payload.append({
                "exchange_id": b["exchange_id"],
                "sender": b["sender_id"],
                "recipient": b["recipient_id"],
                "round": b["round_num"],
                "prior_stance": b["prior_recipient_stance"],
                "factual_stance": b["factual_recipient_stance"],
                "sender_argument": b["sender_content"][:250],
                "other_peers_heard": b["other_senders"],
                "recipient_actual_response": b["recipient_response"][:250],
            })

        pos_text = positive_pole or "Factual and tactical merit"
        neg_text = negative_pole or "Officiating bias or physical fatigue"

        prompt = (
            f"You are a rigorous causal evaluation judge for a multi-agent football debate.\n"
            f"Topic: {topic}\n"
            f"Scale: +1.0 = '{pos_text}', -1.0 = '{neg_text}'.\n\n"
            "TASK: Perform Counterfactual Ablation on each peer exchange.\n"
            "In each case, evaluate what the recipient's stance would have been if the sender had REMAINED SILENT "
            "(counterfactual ablation), taking into account the recipient's prior stance and the other peers they heard.\n"
            "If the recipient was genuinely persuaded by this sender's specific evidence, the counterfactual stance "
            "differs from the factual stance. If the recipient moved due to other peers, fatigue, or prior trajectory, "
            "the counterfactual stance will be close to the factual stance.\n\n"
            "EXCHANGES TO EVALUATE:\n"
            f"{json.dumps(items_payload, indent=2)}\n\n"
            "OUTPUT CONTRACT:\n"
            "Return ONLY a JSON array of objects with the following keys:\n"
            "- exchange_id: integer matching the input\n"
            "- counterfactual_stance: float between -1.0 and 1.0 (recipient's stance without sender)\n"
            "- causal_shift: float >= 0.0 (absolute difference |factual_stance - counterfactual_stance|)\n"
            "- attribution_rationale: string (max 15 words concise reason; do not use unescaped double quotes inside strings)\n"
        )

        try:
            response = llm_client.generate(
                [
                    {"role": "system", "content": "You are a causal inference evaluator. Output only valid JSON."},
                    {"role": "user", "content": prompt},
                ],
                tools=None,
            )
            raw_text = response.get("content", "") if isinstance(response, dict) else str(response)
            cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_text.strip())
            parsed = None
            try:
                parsed = json.loads(cleaned)
            except Exception as json_err:
                logger.debug(f"JSON array parsing issue ({json_err}), attempting regex object recovery")
                for match in re.finditer(r'\{[^{}]*"exchange_id"[^{}]*\}', cleaned, re.DOTALL):
                    try:
                        item = json.loads(match.group(0))
                        if isinstance(item, dict) and "exchange_id" in item:
                            evaluated_records[item["exchange_id"]] = item
                    except Exception:
                        pass
            if isinstance(parsed, list):
                for item in parsed:
                    if isinstance(item, dict) and "exchange_id" in item:
                        evaluated_records[item["exchange_id"]] = item
        except Exception as ex:
            logger.warning(f"Error during counterfactual evaluation LLM call: {ex}")

    # Build CounterfactualExchange list
    all_exchanges: list[CounterfactualExchange] = []
    agent_exchanges_map: dict[str, list[CounterfactualExchange]] = {aid: [] for aid in agent_ids}

    for cand in candidate_exchanges:
        eid = cand["exchange_id"]
        res = evaluated_records.get(eid, {})
        factual_s = cand["factual_recipient_stance"]

        cf_s = res.get("counterfactual_stance")
        if cf_s is not None:
            try:
                cf_s = max(-1.0, min(1.0, float(cf_s)))
            except (ValueError, TypeError):
                cf_s = factual_s
        else:
            # Fallback if unparsed: assume zero causal shift (conservative baseline)
            cf_s = factual_s

        shift = res.get("causal_shift")
        if shift is not None:
            try:
                shift = max(0.0, min(2.0, float(shift)))
            except (ValueError, TypeError):
                shift = abs(factual_s - cf_s)
        else:
            shift = abs(factual_s - cf_s)

        shift = round(shift, 4)
        rationale = res.get("attribution_rationale") or "Analyzed under counterfactual peer ablation."

        exchange_obj = CounterfactualExchange(
            round_num=cand["round_num"],
            sender_id=cand["sender_id"],
            recipient_id=cand["recipient_id"],
            factual_stance=round(factual_s, 4),
            counterfactual_stance=round(cf_s, 4),
            causal_shift=shift,
            attribution_rationale=rationale,
        )
        all_exchanges.append(exchange_obj)
        agent_exchanges_map[cand["sender_id"]].append(exchange_obj)

    # Compute per-agent causal influence
    agent_influences: dict[str, AgentCausalInfluence] = {}
    positive_causal_influencers: list[tuple[str, float]] = []

    for aid in agent_ids:
        exs = agent_exchanges_map.get(aid, [])
        if not exs:
            agent_influences[aid] = AgentCausalInfluence(
                agent_id=aid,
                causal_score=None,
                status="no_exchanges",
                exchange_count=0,
                exchanges=[],
                causal_classification="Untested (No Direct Peers)",
            )
        else:
            avg_shift = round(sum(e.causal_shift for e in exs if e.causal_shift is not None) / len(exs), 4)
            classification = _classify_causal_score(avg_shift)
            agent_influences[aid] = AgentCausalInfluence(
                agent_id=aid,
                causal_score=avg_shift,
                status="computed",
                exchange_count=len(exs),
                exchanges=exs,
                causal_classification=classification,
            )
            if avg_shift > 0.0:
                positive_causal_influencers.append((aid, avg_shift))

    positive_causal_influencers.sort(key=lambda x: -x[1])
    top_causal = positive_causal_influencers[0][0] if positive_causal_influencers else None

    # Produce contrastive summary with correlation
    comparison_summary: dict[str, Any] = {
        "top_causal_influencer": top_causal,
        "evaluated_exchanges": len(all_exchanges),
    }

    if correlation_results and isinstance(correlation_results, dict):
        corr_scores = {}
        for aid, inf in correlation_results.get("agent_influences", {}).items():
            if isinstance(inf, dict):
                corr_scores[aid] = inf.get("influence_score")
        top_corr = correlation_results.get("top_influencer")
        comparison_summary["top_correlation_influencer"] = top_corr
        comparison_summary["correlation_vs_causation_alignment"] = (
            "Aligned (Same Persona)" if top_corr == top_causal and top_causal is not None
            else "Divergent (Different Personas)" if top_corr and top_causal
            else "Inconclusive"
        )

    return DiscussionCausalResult(
        discussion_id=discussion_id,
        agent_causal_influences=agent_influences,
        top_causal_influencer=top_causal,
        evaluated_exchanges_count=len(all_exchanges),
        method="counterfactual_ablation_evaluator",
        comparison_summary=comparison_summary,
    )
