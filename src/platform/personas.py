"""Persona Management Service: System Personas, Custom Personas & AI Persona Generation.

Guarantees full compatibility with the existing Persona abstraction while enabling
tenant-isolated custom and AI-generated specialist agents.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from src.agent.persona import Persona
from src.agent.persona_loader import load_persona
from src.platform.db import get_db_cursor
from src.platform.models import PersonaCreate, PersonaGenerateRequest, PersonaOut, PersonaUpdate

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PERSONAS_DIR = PROJECT_ROOT / "personas"

# Data-driven Persona Fields as required by Feature Group F & Section 19
PERSONA_FIELDS = [
    {"id": "tactical", "name": "Tactical Analysis", "icon": "ph ph-strategy", "color": "#10b981", "desc": "Formations, phases of play, pressing schemes and spatial mechanics."},
    {"id": "scouting", "name": "Scouting & Recruitment", "icon": "ph ph-binoculars", "color": "#00d2ff", "desc": "Talent identification, player profiles, athletic ceilings and squad fit."},
    {"id": "statistics", "name": "Statistics & Analytics", "icon": "ph ph-chart-line-up", "color": "#38bdf8", "desc": "xG models, expected threat (xT), progressive metrics and data validation."},
    {"id": "performance", "name": "Physical & Performance", "icon": "ph ph-heartbeat", "color": "#f43f5e", "desc": "Sprints, high-intensity distance, stamina decay, fatigue and duel physicals."},
    {"id": "refereeing", "name": "Refereeing & Laws", "icon": "ph ph-flag", "color": "#fbbf24", "desc": "IFAB rules, VAR intervention thresholds, disciplinary standards and penalty incidents."},
    {"id": "history", "name": "Historical Context", "icon": "ph ph-books", "color": "#a78bfa", "desc": "Precedents, head-to-head records, managerial legacies and eras."},
    {"id": "fan", "name": "Fan & Media Narrative", "icon": "ph ph-users-three", "color": "#ec4899", "desc": "Atmosphere, psychological momentum, supporter sentiment and pressure."},
    {"id": "player_dev", "name": "Player Development", "icon": "ph ph-trend-up", "color": "#34d399", "desc": "U21 potential, positional transition, coaching reception and development curve."},
    {"id": "custom", "name": "Custom Analytical Field", "icon": "ph ph-sparkle", "color": "#818cf8", "desc": "Bespoke analytical lens tailored to unique football research questions."},
]


def get_persona_fields() -> list[dict[str, Any]]:
    """Return all supported persona fields."""
    return PERSONA_FIELDS


def get_system_personas() -> list[PersonaOut]:
    """Load built-in system personas from yaml files."""
    system_personas = []
    if not PERSONAS_DIR.is_dir():
        return system_personas

    field_map = {
        "tactical_analyst": ("Tactical Analysis", "ph ph-strategy", "#00f59b"),
        "statistical_analyst": ("Statistics & Analytics", "ph ph-chart-line-up", "#00d2ff"),
        "performance_analyst": ("Physical & Performance", "ph ph-heartbeat", "#f43f5e"),
        "fan_analyst": ("Fan & Media Narrative", "ph ph-users-three", "#fbbf24"),
        "refereeing_analyst": ("Refereeing & Laws", "ph ph-flag", "#a855f7"),
        "context_analyst": ("Historical Context", "ph ph-books", "#fb923c"),
    }

    for yaml_path in sorted(PERSONAS_DIR.glob("*.yaml")):
        stem = yaml_path.stem
        try:
            p = load_persona(yaml_path)
            f_name, icon, color = field_map.get(stem, ("Football Analysis", "ph ph-user", "#00d2ff"))
            system_personas.append(
                PersonaOut(
                    id=stem,
                    profile_id=None,
                    name=p.name,
                    field=f_name,
                    background=p.background,
                    stance=p.stance,
                    communication_style=p.communication_style,
                    expertise=p.expertise,
                    priorities=p.priorities,
                    source="system",
                    is_active=True,
                    icon=icon,
                    color=color,
                )
            )
        except Exception as e:
            logger.warning("Failed to load system persona '%s': %s", yaml_path.name, e)
    return system_personas


def get_all_personas_for_profile(profile_id: str) -> list[PersonaOut]:
    """Retrieve all available personas: global system personas + profile-owned custom personas."""
    personas = list(get_system_personas())

    with get_db_cursor() as cur:
        cur.execute(
            "SELECT * FROM profile_personas WHERE profile_id = ? ORDER BY created_at DESC",
            (profile_id,),
        )
        rows = cur.fetchall()
        palette = ["#38bdf8", "#ec4899", "#34d399", "#818cf8", "#f97316", "#06b6d4", "#e11d48", "#10b981", "#8b5cf6", "#f59e0b"]
        for r in rows:
            field_entry = next((f for f in PERSONA_FIELDS if f["name"] == r["field"]), None)
            assigned_color = field_entry["color"] if field_entry else palette[abs(hash(r["id"])) % len(palette)]
            personas.append(
                PersonaOut(
                    id=r["id"],
                    profile_id=r["profile_id"],
                    name=r["name"],
                    field=r["field"],
                    background=r["background"],
                    stance=r["stance"],
                    communication_style=r["communication_style"],
                    expertise=json.loads(r["expertise"]) if isinstance(r["expertise"], str) else r["expertise"],
                    priorities=json.loads(r["priorities"]) if isinstance(r["priorities"], str) else r["priorities"],
                    source=r["source"],
                    is_active=bool(r["is_active"]),
                    created_at=str(r["created_at"]),
                    icon="ph ph-sparkle" if r["source"] == "generated" else "ph ph-user-circle",
                    color=assigned_color,
                )
            )
    return personas


def get_persona_by_id(persona_id: str) -> Persona | None:
    """Load a persona by its identifier, checking system YAMLs then custom DB records."""
    yaml_path = PERSONAS_DIR / f"{persona_id}.yaml"
    if yaml_path.is_file():
        try:
            return load_persona(yaml_path)
        except Exception as e:
            logger.warning("Failed loading system persona YAML '%s': %s", yaml_path, e)

    # Check generated folder
    for gen_p in PERSONAS_DIR.glob(f"generated/*/{persona_id}.yaml"):
        if gen_p.is_file():
            try:
                return load_persona(gen_p)
            except Exception:
                pass

    # Check database
    try:
        with get_db_cursor() as cur:
            cur.execute("SELECT * FROM profile_personas WHERE id = ?", (persona_id,))
            r = cur.fetchone()
            if r:
                exp = json.loads(r["expertise"]) if isinstance(r["expertise"], str) else (r["expertise"] or [])
                prio = json.loads(r["priorities"]) if isinstance(r["priorities"], str) else (r["priorities"] or [])
                return Persona(
                    _name=r["name"],
                    _background=r["background"],
                    _stance=r["stance"],
                    _communication_style=r["communication_style"],
                    _expertise=exp,
                    _priorities=prio,
                )
    except Exception as e:
        logger.warning("Failed querying profile_personas for ID '%s': %s", persona_id, e)

    return None


def create_profile_persona(profile_id: str, req: PersonaCreate) -> PersonaOut:
    """Create and validate a new custom persona for the authenticated profile."""
    name = req.name.strip()
    field_name = req.field.strip()

    # Freeform specification parsing if explicit fields not supplied
    background = (req.background or "").strip()
    stance = (req.stance or "").strip()
    comm_style = (req.communication_style or "").strip()
    expertise = req.expertise or []
    priorities = req.priorities or []

    if req.specifications and (not background or not priorities or not expertise):
        specs = req.specifications.strip()
        if not background:
            background = f"Specialist analyst focusing on {field_name}. {specs}"
        if not stance:
            stance = f"Evaluates matches and players with emphasis on {field_name} principles."
        if not comm_style:
            comm_style = "Precise, structured, evidence-grounded and analytical."
        if not expertise:
            expertise = [field_name, "Tactical profiling", "Performance metrics"]
        if not priorities:
            priorities = [specs[:120], f"Deep validation in {field_name}", "Objective role assessment"]

    if not background:
        background = f"Specialist analyst focused on {field_name}."
    if not stance:
        stance = f"Evaluates football systems through the lens of {field_name}."
    if not comm_style:
        comm_style = "Objective, analytical, and evidence-grounded."
    if not expertise:
        expertise = [field_name, "Tactical evaluation"]
    if not priorities:
        priorities = [f"Rigorous assessment of {field_name}", "Evidence-grounded argumentation"]

    persona_id = f"custom-{uuid4().hex[:10]}"
    now_str = datetime.now(timezone.utc).isoformat()

    with get_db_cursor() as cur:
        cur.execute(
            """INSERT INTO profile_personas (
                   id, profile_id, name, field, background, stance, communication_style,
                   expertise, priorities, source, is_active, created_at, updated_at
               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                persona_id,
                profile_id,
                name,
                field_name,
                background,
                stance,
                comm_style,
                json.dumps(expertise),
                json.dumps(priorities),
                "user",
                True,
                now_str,
                now_str,
            ),
        )

    return PersonaOut(
        id=persona_id,
        profile_id=profile_id,
        name=name,
        field=field_name,
        background=background,
        stance=stance,
        communication_style=comm_style,
        expertise=expertise,
        priorities=priorities,
        source="user",
        is_active=True,
        created_at=now_str,
        icon="ph ph-user-circle",
        color="#00f59b",
    )


def update_profile_persona(profile_id: str, persona_id: str, req: PersonaUpdate) -> PersonaOut:
    """Update an existing custom persona ensuring tenant ownership."""
    # Ensure system personas cannot be updated
    for sys_p in get_system_personas():
        if sys_p.id == persona_id:
            raise ValueError("System personas are protected and cannot be modified.")

    with get_db_cursor() as cur:
        cur.execute(
            "SELECT * FROM profile_personas WHERE id = ? AND profile_id = ?",
            (persona_id, profile_id),
        )
        row = cur.fetchone()
        if not row:
            raise ValueError(f"Persona '{persona_id}' not found or access denied.")

        r = dict(row)
        name = req.name.strip() if req.name is not None else r["name"]
        field_name = req.field.strip() if req.field is not None else r["field"]
        background = req.background.strip() if req.background is not None else r["background"]
        stance = req.stance.strip() if req.stance is not None else r["stance"]
        comm_style = req.communication_style.strip() if req.communication_style is not None else r["communication_style"]
        expertise = req.expertise if req.expertise is not None else (json.loads(r["expertise"]) if isinstance(r["expertise"], str) else r["expertise"])
        priorities = req.priorities if req.priorities is not None else (json.loads(r["priorities"]) if isinstance(r["priorities"], str) else r["priorities"])
        is_active = bool(req.is_active) if req.is_active is not None else bool(r["is_active"])
        now_str = datetime.now(timezone.utc).isoformat()

        cur.execute(
            """UPDATE profile_personas SET
                   name = ?, field = ?, background = ?, stance = ?, communication_style = ?,
                   expertise = ?, priorities = ?, is_active = ?, updated_at = ?
               WHERE id = ? AND profile_id = ?""",
            (
                name,
                field_name,
                background,
                stance,
                comm_style,
                json.dumps(expertise),
                json.dumps(priorities),
                is_active,
                now_str,
                persona_id,
                profile_id,
            ),
        )

    return PersonaOut(
        id=persona_id,
        profile_id=profile_id,
        name=name,
        field=field_name,
        background=background,
        stance=stance,
        communication_style=comm_style,
        expertise=expertise,
        priorities=priorities,
        source=r["source"],
        is_active=bool(is_active),
        created_at=str(r["created_at"]),
        icon="ph ph-sparkle" if r["source"] == "generated" else "ph ph-user-circle",
        color="#818cf8" if r["source"] == "generated" else "#00f59b",
    )


def delete_profile_persona(profile_id: str, persona_id: str) -> bool:
    """Delete a custom persona ensuring tenant ownership and system persona protection."""
    for sys_p in get_system_personas():
        if sys_p.id == persona_id:
            raise ValueError("System personas are protected and cannot be deleted.")

    with get_db_cursor() as cur:
        cur.execute(
            "DELETE FROM profile_personas WHERE id = ? AND profile_id = ?",
            (persona_id, profile_id),
        )
        return cur.rowcount > 0


def generate_ai_personas(profile_id: str, req: PersonaGenerateRequest, llm=None) -> list[PersonaOut]:
    """Generate structured, validated personas using AI or rich field archetype templates."""
    field_name = req.field.strip()
    count = max(1, min(req.count, 6))
    desc = (req.description or "").strip()

    generated_results: list[PersonaOut] = []

    # Try LLM generation if configured
    if llm:
        try:
            prompt = f"""Generate exactly {count} distinct football analyst personas for the field '{field_name}'.
Context/Description: {desc or 'Specialized perspectives for deep football deliberation.'}

You must return a JSON list with exactly {count} objects, each with these exact keys:
- name: string (e.g. "Opposition Scout")
- field: "{field_name}"
- background: string (2-3 sentences of tactical credentials)
- stance: string (core analytical principle)
- communication_style: string (e.g. "Direct, quantitative, concise")
- expertise: list of 3-5 strings
- priorities: list of 3-5 strings

Return JSON only. No markdown formatting."""
            resp = llm.generate(
                messages=[
                    {"role": "system", "content": "You are a football analytics architecture generator. Output valid JSON."},
                    {"role": "user", "content": prompt},
                ]
            )
            raw = resp if isinstance(resp, str) else resp.get("content", "")
            raw = raw.strip()
            if raw.startswith("```json"):
                raw = raw[7:]
            if raw.startswith("```"):
                raw = raw[3:]
            if raw.endswith("```"):
                raw = raw[:-3]
            parsed = json.loads(raw.strip())
            if isinstance(parsed, list):
                for item in parsed[:count]:
                    created = create_profile_persona(
                        profile_id,
                        PersonaCreate(
                            name=str(item.get("name", f"{field_name} Specialist")),
                            field=field_name,
                            background=str(item.get("background", "")),
                            stance=str(item.get("stance", "")),
                            communication_style=str(item.get("communication_style", "")),
                            expertise=list(item.get("expertise", [])),
                            priorities=list(item.get("priorities", [])),
                        ),
                    )
                    # Mark source as generated
                    with get_db_cursor() as cur:
                        cur.execute("UPDATE profile_personas SET source = 'generated' WHERE id = ?", (created.id,))
                    created.source = "generated"
                    created.icon = "ph ph-sparkle"
                    created.color = "#818cf8"
                    generated_results.append(created)
                if generated_results:
                    return generated_results
        except Exception as e:
            logger.warning("LLM persona generation fallback to archetype synthesis: %s", e)

    # Fallback to high-quality data-driven domain archetypes
    archetypes = [
        (
            f"Senior {field_name} Specialist",
            f"Over 12 years of high-performance analytics experience focusing on {field_name.lower()}. {desc}",
            f"Prioritizes structural robustness, repeatable patterns, and measurable margins in {field_name.lower()}.",
            "Authoritative, deeply technical, structured and evidence-grounded.",
            [f"{field_name} models", "Game-model alignment", "Opposition benchmarking", "Tactical diagnostics"],
            [f"Identify structural failure points in {field_name.lower()}", "Verify underlying sample stability", "Synthesize evidence into actionable conclusions"],
        ),
        (
            f"Quantitative {field_name} Scout",
            f"Specializes in translating spatial metrics and event telemetry into actionable {field_name.lower()} assessments.",
            f"Rejects purely narrative assertions without supporting spatial percentiles and turnover rates.",
            "Precise, data-dense, quantitative, direct.",
            ["Event-data parsing", "xG / xT spatial mapping", "Percentile clustering", "Outlier detection"],
            ["Measure statistical deviation from peer average", "Eliminate subjective bias", "Provide concrete probabilistic estimates"],
        ),
        (
            f"Applied {field_name} Practitioner",
            f"Former technical staff specialist focused on pitch application, tactical execution and player comprehension in {field_name.lower()}.",
            f"Balances statistical indicators with real-world pitch dynamics, communication, and decision velocity.",
            "Pragmatic, observant, scenario-oriented, realistic.",
            ["In-game adaptations", "Pressing triggers", "Half-space occupation", "Player psychological response"],
            ["Assess tactical feasibility on the pitch", "Highlight pressure execution under fatigue", "Connect theory to match-winning interventions"],
        ),
        (
            f"Emerging {field_name} Researcher",
            f"Innovator applying cutting-edge network topology and spatial compression theory to football {field_name.lower()}.",
            f"Examines non-linear interactions, passing clusters, and rapid phase transitions.",
            "Forward-looking, exploratory, methodologically rigorous.",
            ["Network flow analysis", "Passing lane geometry", "Spatial clustering", "Phase velocity"],
            ["Identify hidden tactical patterns", "Stress-test prevailing consensus", "Surface second-order effects"],
        ),
    ]

    for i in range(count):
        arch = archetypes[i % len(archetypes)]
        created = create_profile_persona(
            profile_id,
            PersonaCreate(
                name=f"{arch[0]} #{i+1}" if count > len(archetypes) else arch[0],
                field=field_name,
                background=arch[1],
                stance=arch[2],
                communication_style=arch[3],
                expertise=arch[4],
                priorities=arch[5],
            ),
        )
        with get_db_cursor() as cur:
            cur.execute("UPDATE profile_personas SET source = 'generated' WHERE id = ?", (created.id,))
        created.source = "generated"
        created.icon = "ph ph-sparkle"
        created.color = "#818cf8"
        generated_results.append(created)

    return generated_results


def resolve_persona_as_agent_object(persona_id: str, profile_id: Optional[str] = None) -> Persona:
    """Instantiate a concrete Persona object compatible with AgentConfig.

    Works identically for system personas and custom profile personas!
    """
    # 1. Check system personas
    yaml_file = PERSONAS_DIR / f"{persona_id}.yaml"
    if yaml_file.is_file():
        return load_persona(yaml_file)

    # 2. Check profile custom personas
    with get_db_cursor() as cur:
        if profile_id:
            cur.execute(
                "SELECT * FROM profile_personas WHERE id = ? AND profile_id = ?",
                (persona_id, profile_id),
            )
        else:
            cur.execute("SELECT * FROM profile_personas WHERE id = ?", (persona_id,))
        row = cur.fetchone()

        if row:
            r = dict(row)
            return Persona(
                _name=r["name"],
                _background=r["background"],
                _stance=r["stance"],
                _communication_style=r["communication_style"],
                _expertise=json.loads(r["expertise"]) if isinstance(r["expertise"], str) else r["expertise"],
                _priorities=json.loads(r["priorities"]) if isinstance(r["priorities"], str) else r["priorities"],
            )

    raise ValueError(f"Persona '{persona_id}' could not be resolved.")
