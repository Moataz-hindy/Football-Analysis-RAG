"""Load Persona instances from YAML configuration files.

Usage::

    from src.agent.persona_loader import load_persona, load_all_personas

    # Single persona
    persona = load_persona("personas/tactical_analyst.yaml")

    # All personas in a directory
    personas = load_all_personas("personas/")
    tactical = personas["Tactical Analyst"]
"""

from pathlib import Path
from typing import Union

import yaml

from .persona import Persona


# Fields that every persona YAML file must contain.
_REQUIRED_FIELDS = (
    "name",
    "background",
    "stance",
    "communication_style",
    "expertise",
    "priorities",
)


class PersonaValidationError(Exception):
    """Raised when a persona YAML file is missing required fields or
    contains invalid values."""


def _validate(data: dict, source: Union[str, Path]) -> None:
    """Check that *data* contains all required fields with valid values."""
    missing = [f for f in _REQUIRED_FIELDS if f not in data]
    if missing:
        raise PersonaValidationError(
            f"Persona file '{source}' is missing required fields: "
            f"{', '.join(missing)}"
        )

    for field in _REQUIRED_FIELDS:
        value = data[field]
        if field in ("expertise", "priorities"):
            if not isinstance(value, list) or len(value) == 0:
                raise PersonaValidationError(
                    f"Persona file '{source}': '{field}' must be a "
                    f"non-empty list, got {type(value).__name__}"
                )
            for item in value:
                if not isinstance(item, str) or not item.strip():
                    raise PersonaValidationError(
                        f"Persona file '{source}': every item in "
                        f"'{field}' must be a non-empty string"
                    )
        else:
            if not isinstance(value, str) or not value.strip():
                raise PersonaValidationError(
                    f"Persona file '{source}': '{field}' must be a "
                    f"non-empty string"
                )


def load_persona(path: Union[str, Path]) -> Persona:
    """Load a single persona from a YAML file.

    Parameters
    ----------
    path : str or Path
        Path to a ``.yaml`` or ``.yml`` file containing persona fields.

    Returns
    -------
    Persona
        A fully validated :class:`Persona` instance.

    Raises
    ------
    FileNotFoundError
        If *path* does not exist.
    PersonaValidationError
        If required fields are missing or invalid.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Persona file not found: {path}")

    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    if not isinstance(data, dict):
        raise PersonaValidationError(
            f"Persona file '{path}' did not parse to a dictionary"
        )

    _validate(data, path)

    return Persona(
        _name=data["name"].strip(),
        _background=data["background"].strip(),
        _stance=data["stance"].strip(),
        _communication_style=data["communication_style"].strip(),
        _expertise=[item.strip() for item in data["expertise"]],
        _priorities=[item.strip() for item in data["priorities"]],
    )


def load_all_personas(
    directory: Union[str, Path] = "personas",
) -> dict[str, Persona]:
    """Load every persona YAML file from *directory*.

    Parameters
    ----------
    directory : str or Path
        Directory containing ``.yaml`` / ``.yml`` persona files.

    Returns
    -------
    dict[str, Persona]
        A dictionary mapping persona **name** → :class:`Persona`.

    Raises
    ------
    FileNotFoundError
        If *directory* does not exist or contains no YAML files.
    PersonaValidationError
        If any persona file is invalid.
    """
    directory = Path(directory)
    if not directory.is_dir():
        raise FileNotFoundError(f"Persona directory not found: {directory}")

    yaml_files = sorted(
        p for p in directory.iterdir()
        if p.suffix in (".yaml", ".yml")
    )

    if not yaml_files:
        raise FileNotFoundError(
            f"No YAML files found in persona directory: {directory}"
        )

    personas: dict[str, Persona] = {}
    for yaml_file in yaml_files:
        persona = load_persona(yaml_file)
        personas[persona.name] = persona

    return personas
