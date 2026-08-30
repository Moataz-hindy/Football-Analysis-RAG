"""Tests for the persona system.

Covers:
- Concrete Persona class and PersonaInterface compliance
- YAML loading and validation
- Loading all personas from a directory
- Persona behavioral differences
- Error handling for invalid configs
- Compatibility with AgentConfig
"""

import os
import tempfile
from pathlib import Path

import pytest
import yaml

from src.agent.interfaces import PersonaInterface
from src.agent.persona import Persona
from src.agent.persona_loader import (
    PersonaValidationError,
    load_all_personas,
    load_persona,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PERSONAS_DIR = PROJECT_ROOT / "personas"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_persona_data():
    """Minimal valid persona data for testing."""
    return {
        "name": "Test Analyst",
        "background": "A test persona for unit testing.",
        "stance": "Believes testing is important.",
        "communication_style": "Clear and concise.",
        "expertise": ["Unit testing", "Integration testing"],
        "priorities": ["Verify correctness", "Catch regressions"],
    }


@pytest.fixture
def sample_yaml_file(sample_persona_data, tmp_path):
    """Write sample persona data to a temporary YAML file."""
    path = tmp_path / "test_analyst.yaml"
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(sample_persona_data, f)
    return path


# ---------------------------------------------------------------------------
# 1. Persona class implements PersonaInterface
# ---------------------------------------------------------------------------

class TestPersonaInterface:

    def test_persona_is_instance_of_interface(self):
        persona = Persona(
            _name="Test",
            _background="bg",
            _stance="stance",
            _communication_style="style",
            _expertise=["a"],
            _priorities=["b"],
        )
        assert isinstance(persona, PersonaInterface)

    def test_persona_properties_return_correct_values(self):
        persona = Persona(
            _name="Tactical Analyst",
            _background="Coach background",
            _stance="Tactics matter most",
            _communication_style="Methodical",
            _expertise=["Formations", "Pressing"],
            _priorities=["Identify systems", "Evaluate pressing"],
        )
        assert persona.name == "Tactical Analyst"
        assert persona.background == "Coach background"
        assert persona.stance == "Tactics matter most"
        assert persona.communication_style == "Methodical"
        assert persona.expertise == ["Formations", "Pressing"]
        assert persona.priorities == ["Identify systems", "Evaluate pressing"]

    def test_expertise_returns_defensive_copy(self):
        """Modifying the returned list should not affect the persona."""
        persona = Persona(
            _name="Test",
            _background="bg",
            _stance="s",
            _communication_style="cs",
            _expertise=["original"],
            _priorities=["p"],
        )
        returned = persona.expertise
        returned.append("injected")
        assert "injected" not in persona.expertise

    def test_priorities_returns_defensive_copy(self):
        persona = Persona(
            _name="Test",
            _background="bg",
            _stance="s",
            _communication_style="cs",
            _expertise=["e"],
            _priorities=["original"],
        )
        returned = persona.priorities
        returned.append("injected")
        assert "injected" not in persona.priorities

    def test_persona_is_frozen(self):
        persona = Persona(
            _name="Test",
            _background="bg",
            _stance="s",
            _communication_style="cs",
            _expertise=["e"],
            _priorities=["p"],
        )
        with pytest.raises(AttributeError):
            persona._name = "Hacked"

    def test_repr(self):
        persona = Persona(
            _name="Tactical Analyst",
            _background="bg",
            _stance="s",
            _communication_style="cs",
            _expertise=["Formations"],
            _priorities=["p"],
        )
        r = repr(persona)
        assert "Tactical Analyst" in r
        assert "Formations" in r

    def test_summary(self):
        persona = Persona(
            _name="Tactical Analyst",
            _background="Coach background",
            _stance="Tactics first",
            _communication_style="Methodical",
            _expertise=["Formations", "Pressing"],
            _priorities=["Identify systems"],
        )
        s = persona.summary()
        assert "Tactical Analyst" in s
        assert "Coach background" in s
        assert "Tactics first" in s
        assert "Methodical" in s
        assert "Formations" in s
        assert "Identify systems" in s


# ---------------------------------------------------------------------------
# 2. YAML loading
# ---------------------------------------------------------------------------

class TestLoadPersona:

    def test_load_from_yaml(self, sample_yaml_file):
        persona = load_persona(sample_yaml_file)
        assert persona.name == "Test Analyst"
        assert isinstance(persona, Persona)
        assert isinstance(persona, PersonaInterface)

    def test_load_preserves_all_fields(self, sample_yaml_file, sample_persona_data):
        persona = load_persona(sample_yaml_file)
        assert persona.name == sample_persona_data["name"]
        assert persona.background == sample_persona_data["background"]
        assert persona.stance == sample_persona_data["stance"]
        assert persona.communication_style == sample_persona_data["communication_style"]
        assert persona.expertise == sample_persona_data["expertise"]
        assert persona.priorities == sample_persona_data["priorities"]

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            load_persona("nonexistent/path/persona.yaml")

    def test_missing_required_field(self, tmp_path):
        incomplete = {
            "name": "Incomplete",
            "background": "Some background",
            # missing: stance, communication_style, expertise, priorities
        }
        path = tmp_path / "incomplete.yaml"
        with open(path, "w") as f:
            yaml.dump(incomplete, f)

        with pytest.raises(PersonaValidationError, match="missing required fields"):
            load_persona(path)

    def test_empty_name_raises_error(self, tmp_path):
        data = {
            "name": "",
            "background": "bg",
            "stance": "s",
            "communication_style": "cs",
            "expertise": ["e"],
            "priorities": ["p"],
        }
        path = tmp_path / "empty_name.yaml"
        with open(path, "w") as f:
            yaml.dump(data, f)

        with pytest.raises(PersonaValidationError, match="non-empty string"):
            load_persona(path)

    def test_empty_expertise_list_raises_error(self, tmp_path):
        data = {
            "name": "Test",
            "background": "bg",
            "stance": "s",
            "communication_style": "cs",
            "expertise": [],
            "priorities": ["p"],
        }
        path = tmp_path / "empty_expertise.yaml"
        with open(path, "w") as f:
            yaml.dump(data, f)

        with pytest.raises(PersonaValidationError, match="non-empty list"):
            load_persona(path)

    def test_whitespace_is_stripped(self, tmp_path):
        data = {
            "name": "  Padded Name  ",
            "background": "  bg  ",
            "stance": "  s  ",
            "communication_style": "  cs  ",
            "expertise": ["  padded item  "],
            "priorities": ["  padded priority  "],
        }
        path = tmp_path / "padded.yaml"
        with open(path, "w") as f:
            yaml.dump(data, f)

        persona = load_persona(path)
        assert persona.name == "Padded Name"
        assert persona.expertise == ["padded item"]
        assert persona.priorities == ["padded priority"]


# ---------------------------------------------------------------------------
# 3. Load all personas from directory
# ---------------------------------------------------------------------------

class TestLoadAllPersonas:

    @pytest.mark.skipif(
        not PERSONAS_DIR.is_dir(),
        reason="personas/ directory not found"
    )
    def test_load_all_project_personas(self):
        personas = load_all_personas(PERSONAS_DIR)
        assert len(personas) >= 6
        expected_names = {
            "Tactical Analyst",
            "Statistical Analyst",
            "Performance Analyst",
            "Refereeing Analyst",
            "Context Analyst",
            "Fan Analyst",
        }
        assert expected_names.issubset(set(personas.keys()))

    @pytest.mark.skipif(
        not PERSONAS_DIR.is_dir(),
        reason="personas/ directory not found"
    )
    def test_all_personas_implement_interface(self):
        personas = load_all_personas(PERSONAS_DIR)
        for name, persona in personas.items():
            assert isinstance(persona, PersonaInterface), (
                f"{name} does not implement PersonaInterface"
            )

    @pytest.mark.skipif(
        not PERSONAS_DIR.is_dir(),
        reason="personas/ directory not found"
    )
    def test_all_persona_fields_not_empty(self):
        personas = load_all_personas(PERSONAS_DIR)
        for name, persona in personas.items():
            assert persona.name.strip(), f"{name}: name is empty"
            assert persona.background.strip(), f"{name}: background is empty"
            assert persona.stance.strip(), f"{name}: stance is empty"
            assert persona.communication_style.strip(), f"{name}: communication_style is empty"
            assert len(persona.expertise) > 0, f"{name}: expertise is empty"
            assert len(persona.priorities) > 0, f"{name}: priorities is empty"

    def test_empty_directory_raises_error(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="No YAML files"):
            load_all_personas(tmp_path)

    def test_nonexistent_directory_raises_error(self):
        with pytest.raises(FileNotFoundError, match="not found"):
            load_all_personas("nonexistent_directory")


# ---------------------------------------------------------------------------
# 4. Two personas differ meaningfully
# ---------------------------------------------------------------------------

class TestPersonaDifferences:

    @pytest.mark.skipif(
        not PERSONAS_DIR.is_dir(),
        reason="personas/ directory not found"
    )
    def test_tactical_vs_statistical_differ(self):
        personas = load_all_personas(PERSONAS_DIR)
        tactical = personas["Tactical Analyst"]
        statistical = personas["Statistical Analyst"]

        # Names differ
        assert tactical.name != statistical.name

        # Backgrounds differ
        assert tactical.background != statistical.background

        # Stances differ
        assert tactical.stance != statistical.stance

        # Communication styles differ
        assert tactical.communication_style != statistical.communication_style

        # Expertise areas differ
        assert set(tactical.expertise) != set(statistical.expertise)

        # Priorities differ
        assert set(tactical.priorities) != set(statistical.priorities)

    @pytest.mark.skipif(
        not PERSONAS_DIR.is_dir(),
        reason="personas/ directory not found"
    )
    def test_all_personas_have_unique_names(self):
        personas = load_all_personas(PERSONAS_DIR)
        names = [p.name for p in personas.values()]
        assert len(names) == len(set(names)), "Persona names are not unique"

    @pytest.mark.skipif(
        not PERSONAS_DIR.is_dir(),
        reason="personas/ directory not found"
    )
    def test_all_personas_have_unique_stances(self):
        personas = load_all_personas(PERSONAS_DIR)
        stances = [p.stance for p in personas.values()]
        assert len(stances) == len(set(stances)), "Persona stances are not unique"


# ---------------------------------------------------------------------------
# 5. Persona works with AgentConfig
# ---------------------------------------------------------------------------

class TestAgentConfigCompatibility:

    def test_persona_accepted_by_agent_config(self):
        """Persona can be passed as the persona argument to AgentConfig."""
        from src.agent.config import AgentConfig

        persona = Persona(
            _name="Test",
            _background="bg",
            _stance="s",
            _communication_style="cs",
            _expertise=["e"],
            _priorities=["p"],
        )

        # AgentConfig expects all fields — we only test that persona
        # is accepted without a TypeError.  We use None for the other
        # fields since we're only testing persona compatibility.
        config = AgentConfig(
            persona=persona,
            memory=None,       # type: ignore
            tools=None,        # type: ignore
            retrieval=None,    # type: ignore
            llm=None,          # type: ignore
        )
        assert config.persona is persona
        assert config.persona.name == "Test"
