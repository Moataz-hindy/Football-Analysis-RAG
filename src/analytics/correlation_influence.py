"""Exploratory correlation between routed stance gaps and later changes."""

import argparse
import json
import math
from pathlib import Path


def pearson(xs, ys):
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    dx = [x - mean_x for x in xs]
    dy = [y - mean_y for y in ys]
    denominator = math.sqrt(
        sum(x * x for x in dx) * sum(y * y for y in dy)
    )
    if denominator < 1e-12:
        return None
    value = sum(x * y for x, y in zip(dx, dy)) / denominator
    return round(max(-1.0, min(1.0, value)), 4)


def compute_correlation_influence(discussion, analytics):
    config = discussion["config"]
    trajectory = analytics["task1_opinion_trajectories"]

    if trajectory["discussion_id"] != config["discussion_id"]:
        raise ValueError("Discussion and analytics IDs differ")

    agents = config["agent_ids"]
    if set(trajectory["agent_ids"]) != set(agents):
        raise ValueError("Discussion and analytics participants differ")

    stances = {}
    for agent, points in trajectory["trajectories"].items():
        for point in points:
            key = (agent, point["round_num"])
            if key in stances:
                raise ValueError("Duplicate stance snapshot")
            value = point["stance_value"]
            if value is not None and (
                type(value) not in (int, float)
                or not math.isfinite(value)
                or not -1 <= value <= 1
            ):
                raise ValueError("Invalid stance value")
            stances[key] = value

    observations = {agent: [] for agent in agents}
    seen = set()

    for message in discussion["messages"]:
        sender = message["sender_id"]
        round_num = message["round_num"]
        if sender not in observations:
            raise ValueError("Unknown message sender")
        if not message.get("content", "").strip():
            continue

        for recipient in message["recipient_ids"]:
            if recipient not in observations:
                raise ValueError("Unknown message recipient")
            if recipient == sender:
                continue

            route = (round_num, sender, recipient)
            if route in seen:
                continue
            seen.add(route)

            sender_score = stances.get((sender, round_num))
            before = stances.get((recipient, round_num))
            after = stances.get((recipient, round_num + 1))
            if any(value is None for value in (sender_score, before, after)):
                continue

            observations[sender].append({
                "round_num": round_num,
                "recipient_id": recipient,
                "stance_gap": sender_score - before,
                "recipient_change": after - before,
            })

    results = {}
    for agent, rows in observations.items():
        distinct_rounds = len({row["round_num"] for row in rows})
        score = None

        # Minimal computational eligibility, not statistical reliability.
        if len(rows) < 3 or distinct_rounds < 2:
            status = "insufficient_data"
        else:
            xs = [row["stance_gap"] for row in rows]
            ys = [row["recipient_change"] for row in rows]
            score = pearson(xs, ys)
            status = "constant_signal" if score is None else "computed"

        results[agent] = {
            "agent_id": agent,
            "influence_score": score,
            "status": status,
            "observation_count": len(rows),
            "distinct_rounds": distinct_rounds,
            "observations": rows,
        }

    return {
        "discussion_id": config["discussion_id"],
        "method": "pearson_stance_gap_vs_next_round_change",
        "range": [-1, 1],
        "agent_influences": results,
        "limitations": [
            "Exploratory association, not causal persuasion.",
            "Message position is approximated by its agent-round opinion score.",
            "Scores inherit the stance model's interpretation errors.",
            "Observations share agents and rounds and are not independent.",
            "Pooling recipients can introduce differences between recipients.",
            "Shared evidence and other senders can explain the same change.",
            "Both variables use the recipient's prior stance; this shared "
            "baseline can itself contribute to correlation.",
            "Eligibility thresholds do not establish statistical significance.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--discussion", required=True)
    parser.add_argument("--analytics", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    source = Path(args.discussion)
    saved = Path(args.analytics)
    output = Path(args.output)
    if output.resolve() in (source.resolve(), saved.resolve()):
        raise ValueError("Choose a new output file")

    discussion = json.loads(source.read_text(encoding="utf-8"))
    analytics = json.loads(saved.read_text(encoding="utf-8"))
    result = compute_correlation_influence(discussion, analytics)

    # Preserve the earlier metric for comparison.
    analytics["distance_reduction_influence"] = analytics["task3_agent_influence"]
    analytics["task3_agent_influence"] = result
    analytics.setdefault("metadata", {})["influence_method"] = result["method"]

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(analytics, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )

    for agent, row in result["agent_influences"].items():
        print(
            f"{agent}: score={row['influence_score']} "
            f"status={row['status']} observations={row['observation_count']}"
        )
    print(f"Saved: {output}")


if __name__ == "__main__":
    main()