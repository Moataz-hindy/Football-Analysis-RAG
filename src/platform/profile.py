"""Profile types configuration, profile management, and agent influence system."""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from src.platform.db import get_db_cursor
from src.platform.models import ProfileOut, ProfileTypeInfo, ProfileUpdate

logger = logging.getLogger(__name__)

# Data-driven profile types as required by Feature Group C & Section 9
ALL_SIX_PERSONAS = [
    "tactical_analyst",
    "statistical_analyst",
    "performance_analyst",
    "fan_analyst",
    "refereeing_analyst",
    "context_analyst",
]

PROFILE_TYPES: dict[str, ProfileTypeInfo] = {
    "scout": ProfileTypeInfo(
        id="scout",
        name="Football Scout",
        tagline="Talent Identification & Recruitment Analytics",
        description="Prioritizes individual player attributes, structural role suitability, athletic ceiling, statistical percentiles, and market recruitment context.",
        priorities=[
            "Positional suitability and tactical fit",
            "Technical skill execution under pressure",
            "Physical/athletic ceiling and mobility profile",
            "Statistical percentiles vs league peer group",
            "Risk factors, injury history, and squad integration",
        ],
        default_report="Scout Report",
        default_personas=list(ALL_SIX_PERSONAS),
        tone="Evaluative, objective, talent-focused, actionable recruitment recommendations.",
    ),
    "researcher": ProfileTypeInfo(
        id="researcher",
        name="Football Researcher",
        tagline="Methodology, Peer Evidence & Critical Comparison",
        description="Demands rigorous primary evidence, sample size qualification, source comparison, uncertainty quantification, and cross-era contextualization.",
        priorities=[
            "Empirical evidence and citation validation",
            "Sample size and statistical significance",
            "Historical and cross-competition precedent",
            "Systematic counterarguments and edge cases",
            "Explicit uncertainty and methodology constraints",
        ],
        default_report="Research Report",
        default_personas=list(ALL_SIX_PERSONAS),
        tone="Scholarly, rigorous, evidence-cited, scientifically disciplined.",
    ),
    "fan": ProfileTypeInfo(
        id="fan",
        name="Football Fan",
        tagline="Narrative, Passion, Momentum & Terrace Experience",
        description="Focuses on the emotional arc of the match, memorable moments, heroic player performances, dramatic turning points, and accessible tactical storytelling.",
        priorities=[
            "Emotional momentum and psychological swings",
            "Clutch individual actions and key moments",
            "Accessible, vivid storytelling without dry jargon",
            "Historical folklore and supporter identity",
            "Impact on team morale and season trajectory",
        ],
        default_report="Fan Briefing",
        default_personas=list(ALL_SIX_PERSONAS),
        tone="Engaging, passionate, vivid, accessible, narrative-driven.",
    ),
    "analyst": ProfileTypeInfo(
        id="analyst",
        name="Football Analyst",
        tagline="Spatial Formations, Expected Metrics & Tactical Systems",
        description="Breaks down game models into spatial phases: build-up, rest defense, pressing triggers, counter-pressing lanes, and expected goal (xG/xT) flow.",
        priorities=[
            "In-possession and out-of-possession structures",
            "Half-space manipulation and third-man runs",
            "Pressing triggers and defensive block compactness",
            "Expected Threat (xT) and progressive value",
            "Transition timing and spatial dominance",
        ],
        default_report="Tactical Analysis",
        default_personas=list(ALL_SIX_PERSONAS),
        tone="Technical, precise, spatial, data-integrated.",
    ),
    "coach": ProfileTypeInfo(
        id="coach",
        name="Coach / Technical Staff",
        tagline="Match Preparation, In-Game Adjustments & Tactical Counter-Moves",
        description="Focuses on actionable coaching interventions, exploiting opposition weaknesses, defensive spacing guidelines, set-piece matchups, and subs.",
        priorities=[
            "Opponent structural flaws to exploit",
            "Defensive rest structure stability",
            "In-game tactical substitutions and shape tweaks",
            "Set-piece organization and transition rest defense",
            "Clear coaching directives and player instructions",
        ],
        default_report="Match Preparation & Tactical Briefing",
        default_personas=list(ALL_SIX_PERSONAS),
        tone="Actionable, pragmatic, direct, coaching-oriented.",
    ),
    "custom": ProfileTypeInfo(
        id="custom",
        name="Custom Analyst",
        tagline="Tailored Football Intelligence Workspace",
        description="Customized hybrid perspective combining chosen analytical frameworks, specialized metrics, and personalized reporting structures.",
        priorities=[
            "User-defined analytical priorities",
            "Bespoke persona combinations",
            "Flexible reporting format",
        ],
        default_report="Comprehensive Intelligence Report",
        default_personas=list(ALL_SIX_PERSONAS),
        tone="Balanced, multidimensional, customized.",
    ),
}


def get_profile_types() -> list[ProfileTypeInfo]:
    """Return all supported profile type configurations."""
    return list(PROFILE_TYPES.values())


def get_profile_by_id(profile_id: str) -> Optional[ProfileOut]:
    """Retrieve profile by its unique ID."""
    with get_db_cursor() as cur:
        cur.execute("SELECT * FROM profiles WHERE id = ?", (profile_id,))
        row = cur.fetchone()
        if not row:
            return None
        r = dict(row)
        return ProfileOut(
            id=r["id"],
            user_id=r["user_id"],
            display_name=r["display_name"],
            profile_type=r["profile_type"],
            football_focus=r["football_focus"] or "",
            experience_level=r["experience_level"] or "",
            preferred_analysis_style=r["preferred_analysis_style"] or "",
            preferred_report_type=r["preferred_report_type"] or "",
            favorite_competitions=json.loads(r["favorite_competitions"]) if isinstance(r["favorite_competitions"], str) else (r["favorite_competitions"] or []),
            favorite_teams=json.loads(r["favorite_teams"]) if isinstance(r["favorite_teams"], str) else (r["favorite_teams"] or []),
            favorite_analysis_areas=json.loads(r["favorite_analysis_areas"]) if isinstance(r["favorite_analysis_areas"], str) else (r["favorite_analysis_areas"] or []),
            created_at=str(r["created_at"]),
            updated_at=str(r["updated_at"]),
        )


def update_profile(profile_id: str, update: ProfileUpdate) -> ProfileOut:
    """Update profile fields safely."""
    existing = get_profile_by_id(profile_id)
    if not existing:
        raise ValueError(f"Profile '{profile_id}' not found.")

    display_name = update.display_name if update.display_name is not None else existing.display_name
    profile_type = update.profile_type if update.profile_type is not None else existing.profile_type
    football_focus = update.football_focus if update.football_focus is not None else existing.football_focus
    experience_level = update.experience_level if update.experience_level is not None else existing.experience_level
    preferred_analysis_style = update.preferred_analysis_style if update.preferred_analysis_style is not None else existing.preferred_analysis_style
    preferred_report_type = update.preferred_report_type if update.preferred_report_type is not None else existing.preferred_report_type
    favorite_competitions = update.favorite_competitions if update.favorite_competitions is not None else existing.favorite_competitions
    favorite_teams = update.favorite_teams if update.favorite_teams is not None else existing.favorite_teams
    favorite_analysis_areas = update.favorite_analysis_areas if update.favorite_analysis_areas is not None else existing.favorite_analysis_areas
    now_str = datetime.now(timezone.utc).isoformat()

    with get_db_cursor() as cur:
        cur.execute(
            """UPDATE profiles SET
                   display_name = ?,
                   profile_type = ?,
                   football_focus = ?,
                   experience_level = ?,
                   preferred_analysis_style = ?,
                   preferred_report_type = ?,
                   favorite_competitions = ?,
                   favorite_teams = ?,
                   favorite_analysis_areas = ?,
                   updated_at = ?
               WHERE id = ?""",
            (
                display_name,
                profile_type,
                football_focus,
                experience_level,
                preferred_analysis_style,
                preferred_report_type,
                json.dumps(favorite_competitions),
                json.dumps(favorite_teams),
                json.dumps(favorite_analysis_areas),
                now_str,
                profile_id,
            ),
        )

    return get_profile_by_id(profile_id)


def get_profile_prompt_influence(profile: ProfileOut) -> str:
    """Convert authenticated profile into structured instructions for agent reasoning."""
    ptype_info = PROFILE_TYPES.get(profile.profile_type.lower(), PROFILE_TYPES["custom"])

    lines = [
        "### TARGET USER PROFILE & PERSONALIZED PERSPECTIVE",
        f"- Target User: {profile.display_name} (Role: {ptype_info.name})",
        f"- Focus Area: {profile.football_focus}",
        f"- Experience Level: {profile.experience_level}",
        f"- Analysis Style Preference: {profile.preferred_analysis_style}",
        f"- Desired Tone: {ptype_info.tone}",
        "- Core Priorities:",
    ]
    for p in ptype_info.priorities[:4]:
        lines.append(f"  * {p}")

    if profile.favorite_teams:
        lines.append(f"- Known Primary Interest Teams: {', '.join(profile.favorite_teams[:4])}")
    if profile.favorite_analysis_areas:
        lines.append(f"- Preferred Analytical Angles: {', '.join(profile.favorite_analysis_areas[:4])}")

    lines.append(
        "Direct your deliberation to highlight evidence and reasoning most relevant to this user's role. "
        "Do not invent facts, but tailor the depth, focus, and structural conclusions accordingly."
    )
    return "\n".join(lines)
