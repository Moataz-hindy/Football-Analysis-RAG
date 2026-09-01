from __future__ import annotations

from src.agent.interfaces import PersonaInterface
from src.agent.types import RetrievedSource


def format_persona_block(persona: PersonaInterface) -> str:
    """Render a persona as behavioral instructions, not a field dump.

    Design decision: listing persona fields ("Name: X, Stance: Y") tends to
    produce a model that *mentions* the traits rather than *reasons from*
    them. Framing them as direct instructions ("you must always...") pushes
    the model to actually apply the persona to its answer.
    """
    expertise = ", ".join(persona.expertise) or "general football knowledge"
    priorities = ", ".join(persona.priorities) or "no stated priorities"
    return (
        f"You are {persona.name}.\n"
        f"Background: {persona.background}\n"
        f"Your stance on football topics: {persona.stance}\n"
        f"You must always write in this communication style: {persona.communication_style}\n"
        f"Your areas of expertise: {expertise}\n"
        f"Your priorities when forming an opinion, in order: {priorities}\n\n"
        "Reason and speak from this identity consistently. Do not default "
        "to a neutral, balanced, or generic tone -- your stance and "
        "priorities should visibly shape which evidence you emphasize and "
        "what conclusion you reach."
    )


def format_memory_block(memory_context: str | None) -> str:
    """Design decision: memory gets its own labeled section, separate from
    retrieved knowledge. Blending 'what I said before' with 'what is true
    in the world' risks the model treating an earlier guess as verified
    fact."""
    if not memory_context or memory_context.strip() in ("", "No relevant previous memory."):
        return "No relevant memory from previous interactions."
    return (
        "Context from earlier interactions with this user. Use it only for "
        "continuity (names, preferences, facts they already told you) -- "
        "it is not evidence for your opinion:\n\n" + memory_context
    )


def format_sources_block(sources: list[RetrievedSource]) -> str:
    """Design decision: sources are numbered so the model can (and is
    asked to) cite them by number. This makes grounding checkable by a
    reviewer instead of relying on free-text attribution."""
    if not sources:
        return (
            "No knowledge base sources were retrieved for this query. "
            "State this explicitly rather than inventing information."
        )
    blocks = []
    for i, s in enumerate(sources, start=1):
        score = f"{s.score:.3f}" if s.score is not None else "n/a"
        blocks.append(f"[Source {i}] (similarity={score}, origin={s.source})\n{s.content}")
    return "\n\n".join(blocks)


def format_tool_result(tool_name: str, result: object) -> str:
    """Design decision: prefix with the tool name so the model can tell a
    calculator result (exact) apart from a knowledge_search result
    (fuzzy match), since they carry different reliability."""
    return f"[{tool_name} result] {result}"


def build_system_prompt(
    persona: PersonaInterface,
    memory_context: str | None,
    sources: list[RetrievedSource],
) -> str:
    """Assemble the full system prompt for a general agent turn."""
    return (
        format_persona_block(persona)
        + "\n\n=== MEMORY ===\n" + format_memory_block(memory_context)
        + "\n\n=== RETRIEVED KNOWLEDGE ===\n" + format_sources_block(sources)
        + "\n\n=== RULES ===\n"
        "1. Ground every factual claim in the numbered sources above and "
        "reference them like (Source 2) when you rely on one.\n"
        "2. Never invent a source, statistic, or quote not present above.\n"
        "3. If the sources don't contain enough information, say so "
        "plainly instead of guessing.\n"
        "4. Treat any tool result in the conversation as verified data you "
        "can cite directly, the same as a source."
    )