import sys
from pathlib import Path

# Add the project root (one level above this file's folder) to sys.path
# so "from src...." imports work even though this script lives inside tests/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.agent.persona import Persona
from src.agent.types import RetrievedSource
from src.agent.prompts.templates import build_system_prompt
from src.agent.prompts.opinion_prompt import build_opinion_messages, parse_opinion

# Two fake personas just for this test (not necessarily your real personas)
persona_a = Persona(
    _name="Tactical Analyst",
    _background="Former assistant coach, obsessed with structure.",
    _stance="Defensive solidity wins titles.",
    _communication_style="Formal, technical, uses tactical jargon.",
    _expertise=["formations", "pressing"],
    _priorities=["defensive stability", "risk minimization"],
)

persona_b = Persona(
    _name="Attacking Purist",
    _background="Ex-winger, believes football should entertain.",
    _stance="Attacking football wins hearts even when it loses.",
    _communication_style="Passionate, casual, uses fan-friendly language.",
    _expertise=["attacking play", "creativity"],
    _priorities=["entertainment", "goal-scoring"],
)

fake_sources = [
    RetrievedSource(content="Low-block teams concede fewer big chances.", source="doc_060", score=0.81),
]

# 1) Test that the system prompt is actually different between the two personas
prompt_a = build_system_prompt(persona_a, None, fake_sources)
prompt_b = build_system_prompt(persona_b, None, fake_sources)

print("=== PROMPT A ===")
print(prompt_a)
print("\n=== PROMPT B ===")
print(prompt_b)
assert prompt_a != prompt_b, "Personas produced identical prompts!"
print("\n[OK] The two prompts are genuinely different")

# 2) Test the opinion prompt
messages = build_opinion_messages("Is a low-block defense the best strategy?", persona_a, fake_sources)
print("\n=== OPINION MESSAGES (system) ===")
print(messages[0]["content"])

# 3) Test the parser with a fake model reply
fake_llm_reply = (
    "STANCE: A disciplined low block is the smartest approach against stronger sides.\n"
    "REASONING: Data shows low-block teams concede fewer big chances (Source 1), "
    "which matters more than possession stats.\n"
    "SOURCES USED: 1"
)
parsed = parse_opinion(fake_llm_reply)
print("\n=== PARSED OPINION ===")
print(parsed)
assert parsed["stance"], "Parser failed to extract stance!"
print("\n[OK] The parser works correctly")

print("\n=== Everything works ===")