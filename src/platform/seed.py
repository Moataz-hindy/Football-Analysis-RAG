"""Seed database and outputs/ with rich, realistic multi-round football discussions,
profile memories, custom personas, and sample personalized reports.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from src.agent.types import RetrievedSource
from src.discussion.persistence import save_discussion
from src.discussion.types import (
    DiscussionConfig,
    DiscussionMessage,
    DiscussionMetadata,
    DiscussionResult,
    OpinionSnapshot,
    RetrievalEvent,
)
from src.platform.auth import hash_password
from src.platform.db import get_db_cursor, init_db
from src.platform.models import PersonaCreate
from src.platform.personas import create_profile_persona
from src.platform.reports import generate_profile_report

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUTS_DIR = PROJECT_ROOT / "outputs"


def seed_database_and_discussions():
    """Seed sample data for immediate illustration and UI testing."""
    init_db()
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    now_str = datetime.now(timezone.utc).isoformat()

    # ─────────────────────────────────────────────────────────────
    # 1. Create Default Demo User & Profile: Marwan (Scout)
    # ─────────────────────────────────────────────────────────────
    demo_email = "marwan@football.ai"
    demo_user_id = "usr-demo-marwan"
    demo_profile_id = "prof-demo-marwan"
    pw_hash, salt = hash_password("password123")

    with get_db_cursor() as cur:
        # Check if demo user exists
        cur.execute("SELECT id FROM users WHERE LOWER(email) = ?", (demo_email,))
        if not cur.fetchone():
            cur.execute(
                """INSERT INTO users (id, email, password_hash, salt, display_name, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (demo_user_id, demo_email, pw_hash, salt, "Marwan", now_str, now_str),
            )
            cur.execute(
                """INSERT INTO profiles (
                       id, user_id, display_name, profile_type, football_focus, experience_level,
                       preferred_analysis_style, preferred_report_type, favorite_competitions,
                       favorite_teams, favorite_analysis_areas, created_at, updated_at
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    demo_profile_id,
                    demo_user_id,
                    "Marwan",
                    "scout",
                    "Player Recruitment & Positional Profiling",
                    "Professional",
                    "Statistical & Quantitative",
                    "Scout Report",
                    json.dumps(["FIFA World Cup", "UEFA Champions League", "Premier League", "Copa Libertadores"]),
                    json.dumps(["Argentina", "Manchester City", "Arsenal", "Real Madrid"]),
                    json.dumps(["Tactical Compactness", "Pressing Resistance", "Expected Threat (xT)", "Transition Timing"]),
                    now_str,
                    now_str,
                ),
            )
            # Create session for seamless testing
            cur.execute(
                """INSERT INTO sessions (token, user_id, profile_id, created_at, expires_at)
                   VALUES (?, ?, ?, ?, ?)""",
                ("demo-session-token-marwan", demo_user_id, demo_profile_id, now_str, "2030-01-01T00:00:00Z"),
            )

            # Insert sample persistent memories
            sample_memories = [
                ("preference", "Analysis Tone", "Prefers concrete structural mechanics over speculative fan banter", "explicit", 1.0),
                ("preference", "Preferred Detail", "Demands expected threat (xT) and progressive carry stats alongside spatial maps", "explicit", 1.0),
                ("football_interest", "Scouting Focus", "Prioritizes U23 inverted wingers and press-resistant deep pivots", "explicit", 1.0),
                ("report_preference", "Report Format", "Requires explicit risk factors and squad integration recommendations", "explicit", 1.0),
                ("interaction_pattern", "Recurring Topic", "Frequently investigates defensive rest structure in high blocks", "inferred", 0.85),
            ]
            for m_type, key, val, src, conf in sample_memories:
                cur.execute(
                    """INSERT INTO profile_memory (id, profile_id, memory_type, key, value, source, confidence, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (f"mem-{uuid4().hex[:10]}", demo_profile_id, m_type, key, val, src, conf, now_str, now_str),
                )

        # Insert sample custom personas after outer transaction commits
        try:
            create_profile_persona(
                demo_profile_id,
                PersonaCreate(
                    name="Opposition Transition Scout",
                    field="Scouting & Recruitment",
                    specifications="Analyzes opponents' rest defense vulnerabilities, turnover trigger zones, and counter-attacking lane coverage.",
                ),
            )
            create_profile_persona(
                demo_profile_id,
                PersonaCreate(
                    name="Ball Progression Specialist",
                    field="Statistics & Analytics",
                    specifications="Measures line-breaking pass completion, progressive carry distances under pressure, and pass network centrality.",
                ),
            )
        except Exception as e:
            logger.info("Custom persona seed notice: %s", e)
    # ─────────────────────────────────────────────────────────────
    # 2. Seed Discussion 1: Argentina vs France (2022 World Cup Final)
    #    Agents: Arg Coach, Arg Fan, Arg Pundit, France Coach, France Fan, France Pundit
    #    (Matches Image #1 with passes back and forth!)
    # ─────────────────────────────────────────────────────────────
    disc1_id = "argentina-france-2022"
    disc1_agents = [
        "arg_coach", "arg_fan", "arg_pundit",
        "france_coach", "france_fan", "france_pundit"
    ]
    disc1_graph = {
        "arg_coach": ["france_coach", "arg_pundit", "arg_fan"],
        "arg_fan": ["arg_pundit", "france_fan"],
        "arg_pundit": ["arg_coach", "france_pundit", "arg_fan"],
        "france_coach": ["arg_coach", "france_pundit", "france_fan"],
        "france_fan": ["france_pundit", "arg_fan"],
        "france_pundit": ["france_coach", "arg_pundit", "france_fan"],
    }

    disc1_messages = [
        # Round 1
        DiscussionMessage(
            round_num=1,
            sender_id="arg_coach",
            recipient_ids=["france_coach", "arg_pundit"],
            content="Our strategic deployment of Ángel Di María on the left touchline fundamentally isolated Koundé. By pinning France's right-back deep, we created immediate overloads with Tagliafico and Mac Allister, neutralizing France's central progression before it could formulate.",
            timestamp="2026-09-27T10:00:00Z",
            sentiment_score=0.88,
            sentiment_label="positive",
            sources_used=[
                RetrievedSource(
                    content="Di María won 6 duels and completed 3 progressive dribbles down the left flank inside the first 35 minutes.",
                    source="World Cup 2022 Final Tactical Dossier",
                    score=0.94,
                    metadata={"match": "ARG-FRA"},
                )
            ],
        ),
        DiscussionMessage(
            round_num=1,
            sender_id="france_coach",
            recipient_ids=["arg_coach", "france_pundit"],
            content="We concede Di María created an asymmetry we did not anticipate early. However, removing Giroud and Dembélé before half-time shifted our center of gravity toward physical transition channels with Thuram and Kolo Muani, resetting the physical contest.",
            timestamp="2026-09-27T10:02:15Z",
            sentiment_score=-0.25,
            sentiment_label="negative",
        ),
        DiscussionMessage(
            round_num=1,
            sender_id="arg_pundit",
            recipient_ids=["france_pundit", "arg_fan"],
            content="Look at Enzo Fernández and De Paul's rest defense. In the first 70 minutes, France had zero shots on target because Argentina suffocated the transition before Mbappé could ever face forward. That was a masterclass in tactical discipline.",
            timestamp="2026-09-27T10:04:30Z",
            sentiment_score=0.76,
            sentiment_label="positive",
        ),
        DiscussionMessage(
            round_num=1,
            sender_id="france_pundit",
            recipient_ids=["arg_pundit", "france_coach"],
            content="True until the 79th minute, but high-intensity pressing decays after 75 minutes. The moment Otamendi made a single recovery misjudgment, Mbappé's burst changed the psychological reality of the entire match in 97 seconds.",
            timestamp="2026-09-27T10:06:45Z",
            sentiment_score=0.45,
            sentiment_label="positive",
        ),
        DiscussionMessage(
            round_num=1,
            sender_id="arg_fan",
            recipient_ids=["france_fan", "arg_coach"],
            content="The stadium erupted! When Di María scored that team move—Enzo to Messi, Messi to Julián, Julián to Mac Allister, and boom! That was pure Argentine folklore, the greatest team goal in World Cup final history!",
            timestamp="2026-09-27T10:09:00Z",
            sentiment_score=0.95,
            sentiment_label="positive",
        ),
        DiscussionMessage(
            round_num=1,
            sender_id="france_fan",
            recipient_ids=["arg_fan", "france_pundit"],
            content="We were down and out for an hour, but you cannot celebrate early when Kylian is on the pitch. The volley for 2-2 silenced the entire Lusail Stadium. Pure resilience!",
            timestamp="2026-09-27T10:11:20Z",
            sentiment_score=0.60,
            sentiment_label="positive",
        ),

        # Round 2
        DiscussionMessage(
            round_num=2,
            sender_id="arg_coach",
            recipient_ids=["arg_pundit", "france_coach"],
            content="In extra time, our response was vital. Bringing on Paredes and Montiel stabilized the central pivot. Messi's goal for 3-2 demonstrated composure inside the 6-yard box after sustained combination play.",
            timestamp="2026-09-27T10:14:00Z",
            sentiment_score=0.82,
            sentiment_label="positive",
        ),
        DiscussionMessage(
            round_num=2,
            sender_id="france_coach",
            recipient_ids=["france_pundit", "france_fan"],
            content="Our penalty concession in extra time gave us the lifeline. Mbappé demonstrated unprecedented psychological resolve to take three penalties in one final and convert all of them.",
            timestamp="2026-09-27T10:16:30Z",
            sentiment_score=0.55,
            sentiment_label="positive",
        ),
        DiscussionMessage(
            round_num=2,
            sender_id="arg_pundit",
            recipient_ids=["arg_coach", "france_pundit"],
            content="And the 123rd minute save from Dibu Martínez against Kolo Muani! From a pure goalkeeping mechanics standpoint, spreading the left leg and holding vertical balance was the definitive intervention of modern football.",
            timestamp="2026-09-27T10:19:00Z",
            sentiment_score=0.91,
            sentiment_label="positive",
        ),
        DiscussionMessage(
            round_num=2,
            sender_id="france_pundit",
            recipient_ids=["arg_pundit", "france_coach"],
            content="Agreed. Kolo Muani hit it low and true; Martínez's spread covered 2.4 meters of horizontal plane. Penalty shootouts then reflect mental composure, where Dibu clearly mastered the psychological warfare.",
            timestamp="2026-09-27T10:21:15Z",
            sentiment_score=0.35,
            sentiment_label="neutral",
        ),

        # Round 3
        DiscussionMessage(
            round_num=3,
            sender_id="arg_coach",
            recipient_ids=["france_coach", "arg_pundit"],
            content="Final consensus: Scaloni's initial tactical blueprint established an unassailable foundation. Even under extreme transition stress, our structural collective prevailed.",
            timestamp="2026-09-27T10:24:00Z",
            sentiment_score=0.89,
            sentiment_label="positive",
        ),
        DiscussionMessage(
            round_num=3,
            sender_id="france_coach",
            recipient_ids=["arg_coach", "france_pundit"],
            content="A match of two tactical masteries: Argentina's positional dominance for 75 minutes countered by our explosive vertical transition power. A historic contest deservedly decided by margins.",
            timestamp="2026-09-27T10:26:30Z",
            sentiment_score=0.54,
            sentiment_label="positive",
        ),
    ]

    disc1_opinions = [
        OpinionSnapshot(agent_id="arg_coach", round_num=1, stance="Scaloni left-flank overload dominated French structure", reasoning="Di Maria isolated Koundé and produced 2 goals.", sources_used="Tactical Dossier"),
        OpinionSnapshot(agent_id="france_coach", round_num=1, stance="Early structure compromised; transition substitutions required", reasoning="Double substitution before half-time restored physical contest.", sources_used=""),
        OpinionSnapshot(agent_id="arg_coach", round_num=2, stance="Extra-time composure proved decisive", reasoning="Substitutions restored pivot control.", sources_used=""),
        OpinionSnapshot(agent_id="france_coach", round_num=2, stance="Physical parity achieved but penalty execution fell short", reasoning="Mbappe completed historic hat-trick.", sources_used=""),
        OpinionSnapshot(agent_id="arg_coach", round_num=3, stance="Complete tactical and psychological victory", reasoning="Scaloni system validated.", sources_used=""),
        OpinionSnapshot(agent_id="france_coach", round_num=3, stance="Historic contest of opposing tactical systems", reasoning="Transitions countered possession.", sources_used=""),
    ]

    disc1_result = DiscussionResult(
        config=DiscussionConfig(
            discussion_id=disc1_id,
            topic="Scaloni's tactical switch of Di María to the left flank vs France's late physical transitions (2022 World Cup Final)",
            num_rounds=3,
            agent_ids=disc1_agents,
            graph=disc1_graph,
            llm_model="openai/gpt-oss-20b",
            llm_temperature=0.2,
            timestamp="2026-09-27T10:00:00Z",
            metadata={
                "status": "completed",
                "current_round": 3,
                "camps": {
                    "camp_a": {"name": "Argentina", "coach": "arg_coach", "fan": "arg_fan", "pundit": "arg_pundit"},
                    "camp_b": {"name": "France", "coach": "france_coach", "fan": "france_fan", "pundit": "france_pundit"},
                },
            },
        ),
        messages=disc1_messages,
        opinions=disc1_opinions,
        metadata=DiscussionMetadata(
            duration_seconds=184.2,
            total_messages=len(disc1_messages),
            total_retrieval_events=4,
        ),
    )
    save_discussion(disc1_result, output_dir=OUTPUTS_DIR)

    # ─────────────────────────────────────────────────────────────
    # 3. Seed Discussion 2: Japan vs Spain 2022
    # ─────────────────────────────────────────────────────────────
    disc2_id = "japan-spain-2022"
    disc2_agents = ["tactical_analyst", "statistical_analyst", "performance_analyst", "fan_analyst", "refereeing_analyst", "context_analyst"]
    disc2_graph = {
        "tactical_analyst": ["statistical_analyst", "performance_analyst", "fan_analyst"],
        "statistical_analyst": ["tactical_analyst", "context_analyst"],
        "performance_analyst": ["tactical_analyst", "refereeing_analyst"],
        "fan_analyst": ["tactical_analyst", "statistical_analyst"],
        "refereeing_analyst": ["fan_analyst", "context_analyst"],
        "context_analyst": ["tactical_analyst", "statistical_analyst"],
    }
    disc2_messages = [
        DiscussionMessage(
            round_num=1,
            sender_id="tactical_analyst",
            recipient_ids=["statistical_analyst", "performance_analyst"],
            content="Japan's 5-4-1 mid-to-low block intentionally surrendered the flanks to protect central passing lanes into Morata. By maintaining vertical interline compactness under 18 meters, Moriyasu prevented Spain's midfield interior runners from receiving facing forward.",
            timestamp="2026-09-27T11:00:00Z",
            sentiment_score=0.78,
            sentiment_label="positive",
        ),
        DiscussionMessage(
            round_num=1,
            sender_id="statistical_analyst",
            recipient_ids=["tactical_analyst", "context_analyst"],
            content="The data validates Moriyasu's strategy: Spain generated 1,058 passes with 82.3% possession, yet recorded an xG of merely 0.68 outside of the early Morata goal. Japan allowed high pass volume in harmless third-line zones while locking down zone 14.",
            timestamp="2026-09-27T11:02:00Z",
            sentiment_score=0.84,
            sentiment_label="positive",
        ),
        DiscussionMessage(
            round_num=1,
            sender_id="performance_analyst",
            recipient_ids=["tactical_analyst", "refereeing_analyst"],
            content="Notice the sprint intensity spike upon Doan and Mitoma's introduction at half-time. Japan's pressing trap shifted to a synchronized 3-second counter-press on Balde and Simon, immediately generating two goals in three minutes.",
            timestamp="2026-09-27T11:04:30Z",
            sentiment_score=0.72,
            sentiment_label="positive",
        ),
        DiscussionMessage(
            round_num=2,
            sender_id="refereeing_analyst",
            recipient_ids=["fan_analyst", "context_analyst"],
            content="Regarding Mitoma's cross for Tanaka's winner: hawk-eye goal line camera projection confirmed that while the base of the ball was off the grass, the outer curve of the sphere projected 1.88 millimeters over the chalk. By Law 9, the ball was in play.",
            timestamp="2026-09-27T11:07:00Z",
            sentiment_score=0.90,
            sentiment_label="positive",
        ),
        DiscussionMessage(
            round_num=2,
            sender_id="fan_analyst",
            recipient_ids=["tactical_analyst", "statistical_analyst"],
            content="The belief and discipline from Japan sent shockwaves through football! To defeat Germany and Spain in the same tournament with less than 20% possession each time is pure tactical heroism!",
            timestamp="2026-09-27T11:09:15Z",
            sentiment_score=0.95,
            sentiment_label="positive",
        ),
        DiscussionMessage(
            round_num=3,
            sender_id="context_analyst",
            recipient_ids=["tactical_analyst", "statistical_analyst"],
            content="In historical context, this match marked the definitive structural pivot away from sterile possession models towards fast-break spatial efficiency in tournament football.",
            timestamp="2026-09-27T11:12:00Z",
            sentiment_score=0.88,
            sentiment_label="positive",
        ),
    ]

    disc2_result = DiscussionResult(
        config=DiscussionConfig(
            discussion_id=disc2_id,
            topic="Japan's 5-4-1 Low Block vs Spain (2022 World Cup)",
            num_rounds=3,
            agent_ids=disc2_agents,
            graph=disc2_graph,
            llm_model="openai/gpt-oss-20b",
            llm_temperature=0.2,
            timestamp="2026-09-27T11:00:00Z",
            metadata={"status": "completed", "current_round": 3},
        ),
        messages=disc2_messages,
        opinions=[],
        metadata=DiscussionMetadata(duration_seconds=142.0, total_messages=len(disc2_messages)),
    )
    save_discussion(disc2_result, output_dir=OUTPUTS_DIR)

    # ─────────────────────────────────────────────────────────────
    # 4. Generate Initial Personalized Scout Report for Demo User
    # ─────────────────────────────────────────────────────────────
    try:
        generate_profile_report(
            profile_id=demo_profile_id,
            discussion_id=disc1_id,
            custom_report_type="Scout Report",
        )
    except Exception as e:
        logger.warning("Auto-generating seed report failed: %s", e)

    logger.info("Successfully seeded database with discussions %s, %s and demo user %s.", disc1_id, disc2_id, demo_email)
