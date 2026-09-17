"""Validate the saved Week 3 format before analytics applies defaults."""


def validate_discussion(data):
    if not isinstance(data, dict):
        raise ValueError("Discussion must be a JSON object")

    config = data.get("config")
    if not isinstance(config, dict):
        raise ValueError("Missing discussion config")

    for field in ("discussion_id", "topic"):
        value = config.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Missing or invalid config.{field}")

    agents = config.get("agent_ids")
    if (
        not isinstance(agents, list)
        or not agents
        or any(not isinstance(a, str) or not a.strip() for a in agents)
    ):
        raise ValueError("agent_ids must contain non-empty strings")
    if len(set(agents)) != len(agents):
        raise ValueError("Duplicate agent IDs")

    rounds = config.get("num_rounds")
    if type(rounds) is not int or rounds < 0:
        raise ValueError("num_rounds must be a non-negative integer")

    expected = {
        (agent, round_num)
        for agent in agents
        for round_num in range(rounds + 1)
    }
    warnings = []

    for section, agent_field, text_field in (
        ("messages", "sender_id", "content"),
        ("opinions", "agent_id", "stance"),
    ):
        records = data.get(section)
        if not isinstance(records, list):
            raise ValueError(f"{section} must be a list")

        seen = set()
        for index, record in enumerate(records):
            location = f"{section}[{index}]"
            if not isinstance(record, dict):
                raise ValueError(f"{location} must be an object")

            agent = record.get(agent_field)
            round_num = record.get("round_num")
            if agent not in agents:
                raise ValueError(f"{location}: unknown agent")
            if type(round_num) is not int or not 0 <= round_num <= rounds:
                raise ValueError(f"{location}: invalid or missing round_num")
            if not isinstance(record.get(text_field), str):
                raise ValueError(f"{location}: invalid or missing {text_field}")

            key = (agent, round_num)
            if key in seen:
                raise ValueError(f"{location}: duplicate agent/round")
            seen.add(key)

            if section == "messages":
                recipients = record.get("recipient_ids")
                if not isinstance(recipients, list):
                    raise ValueError(f"{location}: recipient_ids must be a list")
                if any(r not in agents for r in recipients):
                    raise ValueError(f"{location}: unknown recipient")
                if len(set(recipients)) != len(recipients):
                    raise ValueError(f"{location}: duplicate recipients")
                if agent in recipients:
                    raise ValueError(f"{location}: self-directed message")

        missing = len(expected - seen)
        if missing:
            warnings.append(f"{section}: missing {missing} agent/round records")

    if not data["messages"] and not data["opinions"]:
        raise ValueError("Discussion is empty")

    if not any(message["recipient_ids"] for message in data["messages"]):
        warnings.append("No recorded routes; interaction influence is unavailable")

    return warnings