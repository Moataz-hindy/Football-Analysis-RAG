from __future__ import annotations

from src.agent.interfaces import PersonaInterface
from src.agent.types import RetrievedSource
from .templates import format_persona_block, format_sources_block


def build_opinion_messages(
    topic: str,
    persona: PersonaInterface,
    sources: list[RetrievedSource],
) -> list[dict[str, str]]:
    """Return chat messages ready to pass to LLMInterface.generate()."""
    system = (
        format_persona_block(persona)
        + "\n\n=== RETRIEVED KNOWLEDGE ===\n" + format_sources_block(sources)
        + "\n\n=== TASK ===\n"
        "Form your initial opinion on the topic below. Reply in exactly "
        "this structure:\n\n"
        "STANCE: <one sentence, your clear position>\n"
        "REASONING: <2-4 sentences, from your persona's point of view, "
        "citing sources by number, e.g. (Source 1)>\n"
        "SOURCES USED: <comma-separated source numbers you actually relied on>\n\n"
        "Two different personas discussing the same topic must reach "
        "genuinely different STANCE and REASONING -- do not produce a "
        "generic, hedge-everything answer. If no retrieved source supports "
        "any position, say so in REASONING and leave SOURCES USED empty."
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": f"Topic: {topic}"},
    ]


def parse_opinion(raw_text: str) -> dict[str, str]:
    """Best-effort parse of the STANCE/REASONING/SOURCES USED structure,
    so callers (e.g. the demo script or a test) can assert on fields
    instead of grepping free text."""
    fields = {"stance": "", "reasoning": "", "sources_used": ""}
    current = None
    for line in raw_text.splitlines():
        stripped = line.strip()
        if stripped.upper().startswith("STANCE:"):
            current = "stance"
            fields[current] = stripped.split(":", 1)[1].strip()
        elif stripped.upper().startswith("REASONING:"):
            current = "reasoning"
            fields[current] = stripped.split(":", 1)[1].strip()
        elif stripped.upper().startswith("SOURCES USED:"):
            current = "sources_used"
            fields[current] = stripped.split(":", 1)[1].strip()
        elif current:
            fields[current] += " " + stripped
    return fields