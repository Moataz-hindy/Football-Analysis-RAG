import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.discussion.types import DiscussionResult

logger = logging.getLogger(__name__)


def save_discussion(
    result: DiscussionResult | dict[str, Any],
    output_dir: str | Path = "outputs",
) -> str:
    """
    Persist a completed discussion result to a JSON file.

    Parameters:
    -----------
    result: DiscussionResult or dict
        The completed discussion record to persist.
    output_dir: str or Path
        Directory where the discussion JSON file will be saved.
        Defaults to 'outputs'.

    Returns:
    --------
    str: Absolute or normalized path to the saved JSON file.

    Raises:
    -------
    ValueError: If required fields (e.g. discussion_id) are missing.
    IOError / OSError: If saving to disk fails.
    """
    output_path = Path(output_dir)

    # Convert to dict representation
    if isinstance(result, DiscussionResult):
        data = result.to_dict()
    elif isinstance(result, dict):
        data = result
    else:
        raise ValueError(
            f"Expected DiscussionResult or dict, got {type(result).__name__}"
        )

    config = data.get("config")
    if not isinstance(config, dict):
        raise ValueError("Missing or invalid 'config' section in discussion data")

    discussion_id = config.get("discussion_id")
    if not discussion_id or not str(discussion_id).strip():
        raise ValueError("Discussion 'discussion_id' must be a non-empty string")

    discussion_id = str(discussion_id).strip()
    num_messages = len(data.get("messages", []))
    num_agents = len(config.get("agent_ids", []))

    logger.info(
        "Saving discussion %s (%d messages, %d agents)...",
        discussion_id,
        num_messages,
        num_agents,
    )

    file_path = output_path / f"{discussion_id}.json"
    temp_file_path = output_path / f".{discussion_id}.tmp.{uuid4().hex}"

    try:
        output_path.mkdir(parents=True, exist_ok=True)

        # Atomic write: write to temp file then rename
        with open(temp_file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        os.replace(temp_file_path, file_path)

        file_size = os.path.getsize(file_path)
        logger.info(
            "Discussion %s saved to %s (%d bytes)",
            discussion_id,
            file_path,
            file_size,
        )
        return str(file_path)

    except Exception as e:
        logger.error(
            "Failed to save discussion %s: %s",
            discussion_id,
            e,
            exc_info=True,
        )
        if temp_file_path.exists():
            try:
                temp_file_path.unlink()
            except OSError:
                pass
        raise


def load_discussion(path: str | Path) -> DiscussionResult:
    """
    Load and reconstruct a DiscussionResult from a persisted JSON file.

    Parameters:
    -----------
    path: str or Path
        Path to the JSON discussion file.

    Returns:
    --------
    DiscussionResult: Fully reconstructed discussion result object.

    Raises:
    -------
    FileNotFoundError: If the specified file does not exist.
    ValueError: If file content is invalid JSON or violates required schema.
    """
    file_path = Path(path)
    logger.info("Loading discussion from %s...", file_path)

    if not file_path.is_file():
        err_msg = f"Discussion file not found: {file_path}"
        logger.error("Failed to load %s: %s", file_path, err_msg)
        raise FileNotFoundError(err_msg)

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        err_msg = f"Invalid JSON in {file_path}: {e}"
        logger.error("Failed to load %s: %s", file_path, err_msg)
        raise ValueError(err_msg) from e
    except Exception as e:
        logger.error("Failed to load %s: %s", file_path, e, exc_info=True)
        raise

    if not isinstance(data, dict):
        err_msg = f"Root of discussion file must be a JSON object, got {type(data).__name__}"
        logger.error("Failed to load %s: %s", file_path, err_msg)
        raise ValueError(err_msg)

    # Optional fields validation with warnings
    discussion_id = data.get("config", {}).get("discussion_id", "unknown")
    if "metadata" not in data:
        logger.warning(
            "Discussion %s: missing optional field 'metadata', defaulting to empty",
            discussion_id,
        )

    for idx, msg in enumerate(data.get("messages", [])):
        if isinstance(msg, dict) and "retrieval_events" not in msg:
            logger.warning(
                "Discussion %s: message index %d missing optional field 'retrieval_events', defaulting to empty",
                discussion_id,
                idx,
            )

    try:
        result = DiscussionResult.from_dict(data)
    except Exception as e:
        err_msg = f"Failed to parse discussion schema from {file_path}: {e}"
        logger.error("Failed to load %s: %s", file_path, err_msg)
        raise ValueError(err_msg) from e

    logger.info(
        "Loaded discussion %s: topic='%s', %d messages, %d rounds",
        result.config.discussion_id,
        result.config.topic,
        len(result.messages),
        result.config.num_rounds,
    )
    return result


def list_discussions(output_dir: str | Path = "outputs") -> list[dict[str, Any]]:
    """
    List summary metadata for all discussions found in output_dir.

    Parameters:
    -----------
    output_dir: str or Path
        Directory to scan for discussion JSON files.

    Returns:
    --------
    list[dict[str, Any]]: List of metadata summaries sorted newest first.
    """
    output_path = Path(output_dir)
    if not output_path.exists() or not output_path.is_dir():
        logger.info(
            "Directory '%s' does not exist or is not a directory, returning empty list",
            output_dir,
        )
        return []

    summaries: list[dict[str, Any]] = []

    for file_path in output_path.glob("*.json"):
        if file_path.name.startswith("."):
            continue

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            config = data.get("config", {})
            discussion_id = config.get("discussion_id", file_path.stem)
            topic = config.get("topic", "")
            timestamp = config.get("timestamp", "")
            num_agents = len(config.get("agent_ids", []))
            num_rounds = config.get("num_rounds", 0)
            num_messages = len(data.get("messages", []))

            summaries.append(
                {
                    "discussion_id": discussion_id,
                    "topic": topic,
                    "timestamp": timestamp,
                    "file_path": str(file_path),
                    "num_agents": num_agents,
                    "num_rounds": num_rounds,
                    "num_messages": num_messages,
                }
            )
        except Exception as e:
            logger.warning("Skipping %s: %s", file_path.name, e)
            continue

    # Sort descending by timestamp, falling back to discussion_id
    summaries.sort(
        key=lambda item: (item.get("timestamp") or "", item.get("discussion_id") or ""),
        reverse=True,
    )

    logger.info("Found %d discussion(s) in %s", len(summaries), output_dir)
    return summaries

def load_discussion_by_id(
    discussion_id: str,
    output_dir: str | Path = "outputs",
) -> DiscussionResult:
    """Reconstruct a completed discussion from its identifier (Requirement 4.8).

    Because ``save_discussion`` names each file ``{discussion_id}.json``,
    the identifier alone is enough for a downstream system (Week 4) to
    retrieve the complete discussion history.

    Parameters:
    -----------
    discussion_id: str
        The identifier the discussion was persisted under.
    output_dir: str or Path
        Directory scanned by ``save_discussion``; defaults to 'outputs'.

    Returns:
    --------
    DiscussionResult: Fully reconstructed discussion result object.

    Raises:
    -------
    FileNotFoundError: If no file exists for ``discussion_id``.
    """
    discussion_id = str(discussion_id).strip()
    if not discussion_id:
        raise ValueError("discussion_id must be a non-empty string")

    file_path = Path(output_dir) / f"{discussion_id}.json"
    return load_discussion(file_path)


# ---------------------------------------------------------------------------
# Bridge: DiscussionState (orchestrator) → persistence JSON
# ---------------------------------------------------------------------------

def _extract_opinion(content: str) -> dict[str, str]:
    """Best-effort extraction of STANCE / REASONING / SOURCES USED from agent text.

    The orchestrator prompts agents to respond in this structured format.
    If markers are missing, the full content is stored as raw_text so
    Week 4 can still consume it.
    """
    stance = ""
    reasoning = ""
    sources_used = ""

    # Try to extract STANCE
    stance_match = re.search(
        r"STANCE\s*:\s*(.+?)(?=\nREASONING\s*:|$)",
        content,
        re.DOTALL | re.IGNORECASE,
    )
    if stance_match:
        stance = stance_match.group(1).strip()

    # Try to extract REASONING
    reasoning_match = re.search(
        r"REASONING\s*:\s*(.+?)(?=\nSOURCES?\s*USED\s*:|$)",
        content,
        re.DOTALL | re.IGNORECASE,
    )
    if reasoning_match:
        reasoning = reasoning_match.group(1).strip()

    # Try to extract SOURCES USED
    sources_match = re.search(
        r"SOURCES?\s*USED\s*:\s*(.+)",
        content,
        re.DOTALL | re.IGNORECASE,
    )
    if sources_match:
        sources_used = sources_match.group(1).strip()

    return {
        "stance": stance,
        "reasoning": reasoning,
        "sources_used": sources_used,
        "raw_text": content,
    }


def _stance_changed(previous_stance: str, current_stance: str) -> bool:
    """Whitespace/case-insensitive comparison used to detect an opinion change."""
    return previous_stance.strip().lower() != current_stance.strip().lower()


def _derive_change_reason(reasoning: str) -> str:
    """Best-effort short reason for a stance change, taken from the agent's own reasoning.

    We don't invent an explanation; we surface the first sentence of the
    REASONING the agent already gave for that round, so the reason stays
    grounded in what the agent actually said.
    """
    reasoning = reasoning.strip()
    if not reasoning:
        return ""

    first_sentence = re.split(r"(?<=[.!?])\s+", reasoning)[0].strip()
    return first_sentence


def build_opinion_history(state: Any) -> list[dict[str, Any]]:
    """Build the Requirement 4.7 opinion-evolution history from a DiscussionState.

    For every agent, walks their messages in round order (round 0 = initial
    opinion) and produces one snapshot per round containing:
      - the parsed stance/reasoning for that round,
      - `changed_from_previous`: whether the stance differs from that same
        agent's immediately preceding snapshot (always False for round 0),
      - `change_reason`: a short, best-effort reason drawn from the agent's
        own REASONING text when a change is detected, else "".

    The agent's final opinion is simply the snapshot with the highest
    `round_num` for that `agent_id`; no separate storage is needed for it.

    This works for any number of configured rounds, since it derives
    everything from `state.messages` rather than assuming a fixed count.
    """
    previous_stance_by_agent: dict[str, str] = {}
    opinions: list[dict[str, Any]] = []

    # state.messages are appended round-by-round as the discussion runs, but
    # sort defensively so this function is correct regardless of call order.
    ordered_messages = sorted(state.messages, key=lambda msg: msg.round_number)

    for msg in ordered_messages:
        parsed = _extract_opinion(msg.content)
        agent_id = msg.sender_id
        # Fall back to the raw text when STANCE: isn't present, so agents
        # that don't follow the format still get meaningful change detection.
        comparable_stance = parsed["stance"] or parsed["raw_text"]

        is_initial_snapshot = agent_id not in previous_stance_by_agent
        changed = (
            False
            if is_initial_snapshot
            else _stance_changed(previous_stance_by_agent[agent_id], comparable_stance)
        )
        change_reason = _derive_change_reason(parsed["reasoning"]) if changed else ""

        opinions.append({
            "agent_id": agent_id,
            "round_num": msg.round_number,
            "stance": parsed["stance"],
            "reasoning": parsed["reasoning"],
            "sources_used": parsed["sources_used"],
            "raw_text": parsed["raw_text"],
            "timestamp": getattr(msg, "timestamp", ""),
            "changed_from_previous": changed,
            "change_reason": change_reason,
        })

        previous_stance_by_agent[agent_id] = comparable_stance

    return opinions


def _graph_to_adjacency(graph_obj: Any) -> dict[str, list[str]]:
    """Convert a DiscussionGraph / NetworkX DiGraph to an adjacency dict."""
    # Accept GraphRouter, DiscussionGraph, or nx.DiGraph
    g = graph_obj
    if hasattr(g, "graph"):  # GraphRouter or DiscussionGraph wrapper
        g = g.graph
    if hasattr(g, "graph"):  # DiscussionGraph.graph → nx.DiGraph
        g = g.graph

    adjacency: dict[str, list[str]] = {}
    for node in g.nodes:
        adjacency[node] = list(g.successors(node))
    return adjacency


def save_discussion_from_state(
    state: Any,
    router: Any = None,
    output_dir: str | Path = "outputs",
    llm_model: str = "",
    llm_temperature: float = 0.0,
    llm: Any = None,
    config_metadata: dict[str, Any] | None = None,
    duration_seconds: float = 0.0,
    errors: list[str] | None = None,
) -> str:
    """Bridge function: convert orchestrator DiscussionState → persistence JSON.

    Parameters
    ----------
    state : DiscussionState
        The completed discussion state returned by DiscussionOrchestrator.run().
    router : GraphRouter or DiscussionGraph, optional
        The graph/router used during the discussion. If provided, the
        adjacency list is serialized into the output config.
    output_dir : str or Path
        Directory for the output JSON file.
    llm_model : str
        Model identifier for reproducibility. Overrides ``llm`` when both
        are given.
    llm_temperature : float
        Temperature used during the discussion. Overrides ``llm`` when
        both are given.
    llm : LLMInterface, optional
        The LLM adapter used during the run. When given and the explicit
        ``llm_model``/``llm_temperature`` arguments are left blank, the
        model and temperature are captured from this adapter so the
        persisted config always matches the run's source of truth
        (Requirement 4.8). Its base_url and max_tokens are recorded in
        ``config.metadata``.
    config_metadata : dict, optional
        Extra run-configuration entries merged into ``config.metadata``
        (e.g. persona files, seeds, demo script version).
    duration_seconds : float
        Wall-clock duration of the discussion run.
    errors : list[str] or None
        Any errors that occurred during the discussion.

    Returns
    -------
    str
        Path to the saved JSON file.
    """
    logger.info(
        "Converting DiscussionState %s to persistence format...",
        state.discussion_id,
    )

    # --- Build config ---
    graph_dict: dict[str, list[str]] = {}
    if router is not None:
        try:
            graph_dict = _graph_to_adjacency(router)
        except Exception as e:
            logger.warning("Could not serialize graph: %s", e)

    # Requirement 4.8: the persisted model configuration must match the
    # adapter that actually served the discussion. Explicit arguments keep
    # priority; otherwise capture from the LLM adapter.
    if not llm_model and llm is not None and hasattr(llm, "model"):
        llm_model = str(llm.model)
    if not llm_temperature and llm is not None and hasattr(llm, "temperature"):
        llm_temperature = float(llm.temperature)

    run_metadata = dict(config_metadata or {})
    if llm is not None:
        if hasattr(llm, "base_url"):
            run_metadata.setdefault("llm_base_url", str(llm.base_url))
        if hasattr(llm, "max_tokens"):
            run_metadata.setdefault("llm_max_tokens", int(llm.max_tokens))
    seed = os.environ.get("LLM_SEED", "").strip()
    if seed:
        run_metadata.setdefault("llm_seed", seed)

    config = {
        "discussion_id": state.discussion_id,
        "topic": state.topic,
        "num_rounds": state.total_rounds,
        "agent_ids": list(state.agent_ids),
        "graph": graph_dict,
        "llm_model": llm_model,
        "llm_temperature": llm_temperature,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metadata": run_metadata,
    }

    # --- Convert messages ---
    messages = []
    for msg in state.messages:
        # Convert sources (RetrievedSource objects) to dicts
        sources_used = []
        for s in getattr(msg, "sources", []):
            if hasattr(s, "content"):
                sources_used.append({
                    "content": s.content,
                    "source": getattr(s, "source", ""),
                    "score": getattr(s, "score", None),
                    "metadata": getattr(s, "metadata", {}),
                })
            elif isinstance(s, dict):
                sources_used.append(s)

        # Convert tool_calls to retrieval_events
        retrieval_events = []
        for tc in getattr(msg, "tool_calls", []):
            name = tc.name if hasattr(tc, "name") else tc.get("name", "")
            args = tc.arguments if hasattr(tc, "arguments") else tc.get("arguments", {})
            result = tc.result if hasattr(tc, "result") else tc.get("result")

            retrieval_events.append({
                "query": args.get("query", str(args)),
                "num_results": len(result) if isinstance(result, list) else 0,
                "timestamp": getattr(msg, "timestamp", ""),
                "metadata": {"tool_name": name, "arguments": args},
            })

        messages.append({
            "round_num": msg.round_number,
            "sender_id": msg.sender_id,
            "recipient_ids": list(msg.recipient_ids),
            "content": msg.content,
            "timestamp": getattr(msg, "timestamp", ""),
            "sources_used": sources_used,
            "retrieval_events": retrieval_events,
            "metadata": {
                "message_id": getattr(msg, "message_id", ""),
            },
        })

    # --- Extract opinion evolution (Requirement 4.7) from messages ---
    opinions = build_opinion_history(state)

    # --- Build metadata ---
    total_retrieval = sum(
        len(m.get("retrieval_events", [])) if isinstance(m, dict)
        else len(getattr(m, "retrieval_events", []))
        for m in messages
    )

    metadata = {
        "duration_seconds": duration_seconds,
        "total_messages": len(messages),
        "total_retrieval_events": total_retrieval,
        "errors": errors or [],
    }

    # --- Assemble and save ---
    data = {
        "config": config,
        "messages": messages,
        "opinions": opinions,
        "metadata": metadata,
    }

    return save_discussion(data, output_dir=output_dir)
