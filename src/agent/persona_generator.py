"""Dynamic 3v3 Persona Generator with Anti-Sycophancy Epistemic Resistance.

Generates symmetrical, topic-specific debate panels (Coach, Fan, Pundit for each side)
equipped with high epistemic resistance to prevent premature round-1 consensus collapse.
Caches generated persona YAMLs in `personas/generated/<discussion_id>/` for zero-cost reuse.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
import re
from typing import Any
import yaml

from src.agent.interfaces import LLMInterface
from src.agent.persona import Persona
from src.agent.persona_loader import load_persona

logger = logging.getLogger(__name__)


def _sanitize_id(name: str) -> str:
    """Create a clean lowercase snake_case identifier."""
    cleaned = re.sub(r"[^a-zA-Z0-9_]+", "_", name.strip().lower())
    return re.sub(r"_+", "_", cleaned).strip("_")


def _canonical_role(raw_role: Any, default: str = "coach") -> str:
    r = str(raw_role or "").lower().strip()
    if any(k in r for k in ["coach", "manager", "gaffer", "tacti"]):
        return "coach"
    if any(k in r for k in ["fan", "supporter", "terrace", "crowd"]):
        return "fan"
    if any(k in r for k in ["pundit", "player", "analyst", "legend", "expert", "former"]):
        return "pundit"
    return default


def generate_personas_for_topic(
    topic: str,
    llm: Any,
    discussion_id: str,
    output_dir: str | Path = "personas/generated",
    force_regenerate: bool = False,
) -> tuple[dict[str, Persona], dict[str, str], dict[str, Any]]:
    """Generate 6 polarized personas for a debate topic, or load from cache if already generated.

    Parameters
    ----------
    topic : str
        Match or tactical debate topic (e.g. 'England 6-4 France World Cup Playoff').
    llm : Any
        LLM instance implementing `.generate(...)`.
    discussion_id : str
        Unique slug/identifier for this discussion (used as folder name).
    output_dir : str | Path
        Directory where generated personas are saved. Defaults to 'personas/generated'.
    force_regenerate : bool
        If True, ignores existing cached YAML files and generates fresh personas.

    Returns
    -------
    tuple[dict[str, Persona], dict[str, str], dict[str, Any]]
        - Mapping of agent_id -> Persona object
        - Mapping of agent_id -> persona YAML file path string
        - Camps metadata mapping {camp_a: {...}, camp_b: {...}}
    """
    target_dir = Path(output_dir) / discussion_id
    manifest_path = target_dir / "manifest.json"

    # 1. Check Smart Cache: Must have 6 distinct valid personas and manifest
    if target_dir.exists() and not force_regenerate and manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            camp_a = manifest.get("camp_a", {})
            camp_b = manifest.get("camp_b", {})
            expected_ids = [
                camp_a.get("coach"), camp_a.get("fan"), camp_a.get("pundit"),
                camp_b.get("coach"), camp_b.get("fan"), camp_b.get("pundit"),
            ]
            if (
                len(set(expected_ids)) == 6
                and None not in expected_ids
                and all((target_dir / f"{aid}.yaml").exists() for aid in expected_ids)
            ):
                personas: dict[str, Persona] = {}
                persona_files: dict[str, str] = {}
                for aid in expected_ids:
                    yaml_p = target_dir / f"{aid}.yaml"
                    personas[aid] = load_persona(yaml_p)
                    persona_files[aid] = str(yaml_p.resolve())
                logger.info("Reusing 6 cached dynamic personas from %s", target_dir)
                return personas, persona_files, manifest
        except Exception as err:
            logger.warning("Failed to load cached personas from %s (%s); regenerating...", target_dir, err)

    # 2. Cache Miss or Force Regenerate: Prompt LLM in two compact camp calls to respect max_tokens
    target_dir.mkdir(parents=True, exist_ok=True)

    def _call_camp_llm(camp_prompt: str) -> dict[str, Any]:
        response = llm.generate(
            [
                {"role": "system", "content": "You are a football broadcasting director. Output only valid JSON."},
                {"role": "user", "content": camp_prompt},
            ],
            tools=None,
        )
        raw_text = response.get("content", "") if isinstance(response, dict) else str(response)
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_text.strip())
        # Clean trailing commas if any
        cleaned = re.sub(r",\s*([\]}])", r"\1", cleaned)
        try:
            return json.loads(cleaned)
        except Exception as err:
            logger.warning("Standard JSON decode failed: %s; attempting regex extraction", err)
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                return json.loads(match.group(0))
            raise

    # Prompt 1: Identify debate sides and generate Camp A
    prompt_camp_a = (
        f"You are organizing a 3v3 football debate on the topic or question:\n"
        f"\"{topic}\"\n\n"
        "TASK:\n"
        "1. Formulate the two opposing camps, positions, or theses on this debate/question:\n"
        "   - Camp A: Affirmative / Thesis (e.g. Tactical Masterclass, Winning Team, Pro-Decision)\n"
        "   - Camp B: Counter / Antithesis (e.g. Defensive Collapse, Losing Team, Anti-Decision)\n"
        "2. Generate 3 personas advocating for Camp A:\n"
        "   - coach: Manager / Head Coach / Tactical Architect defending Camp A\n"
        "   - fan: Passionate matchday supporter defending Camp A\n"
        "   - pundit: Former player / tactical pundit defending Camp A\n\n"
        "DIALECTICAL & EVIDENCE-CALIBRATED MANDATE:\n"
        "Each persona strongly favors Camp A's primary thesis, but is an intellectually honest analyst.\n"
        "They must NOT be completely obstinate or dogmatically repeat 'Maintain' without nuance.\n"
        "When opponents present verified match facts (e.g. goals conceded, defensive gaps, counter-pressing pace), "
        "they defend their perspective with passion, but acknowledge dual factors and calibrate their position.\n"
        "Keep all descriptions concise (under 25 words each) to fit token limits.\n\n"
        "Return ONLY a JSON object:\n"
        "{\n"
        "  \"camp_a_name\": \"Concise name or stance for Camp A (e.g. England / Tactical Masterclass)\",\n"
        "  \"camp_b_name\": \"Concise name or stance for Camp B (e.g. France / Defensive Collapse)\",\n"
        "  \"personas\": [\n"
        "    {\n"
        "      \"id\": \"snake_case_id (e.g. england_coach)\",\n"
        "      \"role\": \"coach\",\n"
        "      \"name\": \"Full Name (e.g. Thomas Tuchel)\",\n"
        "      \"background\": \"1-2 concise sentences on background\",\n"
        "      \"stance\": \"1-2 sentences stating their primary thesis on the debate question, while acknowledging nuance based on match evidence.\",\n"
        "      \"communication_style\": \"1 sentence style\",\n"
        "      \"expertise\": [\"skill 1\", \"skill 2\"],\n"
        "      \"priorities\": [\"priority 1\", \"priority 2\"]\n"
        "    }\n"
        "  ]\n"
        "}\n"
    )

    data_a = _call_camp_llm(prompt_camp_a)
    camp_a_name = data_a.get("camp_a_name", "Side A")
    camp_b_name = data_a.get("camp_b_name", "Side B")
    personas_a = data_a.get("personas", [])

    # Prompt 2: Generate Camp B
    prompt_camp_b = (
        f"You are organizing a 3v3 football debate on the topic or question: \"{topic}\".\n"
        f"Camp A is: \"{camp_a_name}\". Camp B is: \"{camp_b_name}\".\n\n"
        f"TASK: Generate 3 opposing personas advocating for Camp B (\"{camp_b_name}\") on this question:\n"
        "   - coach: Opposing Manager / Tactical Counterpart defending Camp B\n"
        "   - fan: Opposing passionate matchday supporter defending Camp B\n"
        "   - pundit: Opposing former player / pundit defending Camp B\n\n"
        "DIALECTICAL & EVIDENCE-CALIBRATED MANDATE:\n"
        "Each persona strongly favors Camp B's primary thesis, but is an intellectually honest analyst.\n"
        "They must NOT be completely obstinate or dogmatically repeat 'Maintain' without nuance.\n"
        "When opponents present verified match facts (e.g. offensive execution, 6 goals scored, transitions), "
        "they defend their perspective with passion, but acknowledge dual factors and calibrate their position.\n"
        "Keep all descriptions concise (under 25 words each).\n\n"
        "Return ONLY a JSON object:\n"
        "{\n"
        "  \"personas\": [\n"
        "    {\n"
        "      \"id\": \"snake_case_id (e.g. france_coach)\",\n"
        "      \"role\": \"coach\",\n"
        "      \"name\": \"Full Name (e.g. Didier Deschamps)\",\n"
        "      \"background\": \"1-2 concise sentences\",\n"
        "      \"stance\": \"1-2 sentences stating their primary thesis on the question, while acknowledging nuance based on match evidence.\",\n"
        "      \"communication_style\": \"1 sentence style\",\n"
        "      \"expertise\": [\"skill 1\", \"skill 2\"],\n"
        "      \"priorities\": [\"priority 1\", \"priority 2\"]\n"
        "    }\n"
        "  ]\n"
        "}\n"
    )

    data_b = _call_camp_llm(prompt_camp_b)
    personas_b = data_b.get("personas", [])

    roles_order = ["coach", "fan", "pundit"]
    personas_dict: dict[str, Persona] = {}
    persona_files: dict[str, str] = {}

    def _process_camp(camp_key: str, camp_personas: list[dict[str, Any]]) -> dict[str, str]:
        camp_mapping: dict[str, str] = {}
        padded = list(camp_personas)
        while len(padded) < 3:
            idx = len(padded)
            padded.append({
                "role": roles_order[idx],
                "name": f"{camp_key.replace('_', ' ').title()} {roles_order[idx].title()}",
            })

        for idx, pdata in enumerate(padded[:3]):
            desired_role = _canonical_role(pdata.get("role"), default=roles_order[idx])
            if desired_role in camp_mapping:
                avail = [r for r in roles_order if r not in camp_mapping]
                desired_role = avail[0] if avail else desired_role

            pid = _sanitize_id(pdata.get("id") or f"{camp_key}_{desired_role}")
            if pid in personas_dict:
                pid = f"{camp_key}_{desired_role}"

            camp_mapping[desired_role] = pid

            yaml_dict = {
                "name": pdata.get("name", pid.replace("_", " ").title()),
                "background": pdata.get("background", "").strip(),
                "stance": pdata.get("stance", "").strip(),
                "communication_style": pdata.get("communication_style", "").strip(),
                "expertise": pdata.get("expertise", ["Tactical analysis", "Matchday evaluation"]),
                "priorities": pdata.get("priorities", ["Defend squad perspective", "Demand hard evidence"]),
            }

            yaml_path = target_dir / f"{pid}.yaml"
            with open(yaml_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(yaml_dict, f, sort_keys=False, allow_unicode=True)

            personas_dict[pid] = load_persona(yaml_path)
            persona_files[pid] = str(yaml_path.resolve())

        for r in roles_order:
            if r not in camp_mapping:
                camp_mapping[r] = list(camp_mapping.values())[0]

        return camp_mapping

    camp_a_roles = _process_camp("camp_a", personas_a)
    camp_b_roles = _process_camp("camp_b", personas_b)

    # Build and write manifest
    manifest = {
        "discussion_id": discussion_id,
        "topic": topic,
        "camp_a": {
            "name": camp_a_name,
            "coach": camp_a_roles["coach"],
            "fan": camp_a_roles["fan"],
            "pundit": camp_a_roles["pundit"],
        },
        "camp_b": {
            "name": camp_b_name,
            "coach": camp_b_roles["coach"],
            "fan": camp_b_roles["fan"],
            "pundit": camp_b_roles["pundit"],
        },
    }

    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    logger.info("Saved 6 dynamic debate personas to %s", target_dir)

    return personas_dict, persona_files, manifest
