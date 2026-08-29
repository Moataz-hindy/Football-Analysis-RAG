"""Concrete Persona implementation.

Implements :class:`PersonaInterface` as a simple dataclass that can be
instantiated directly or loaded from a YAML configuration file via
:mod:`persona_loader`.
"""

from dataclasses import dataclass, field

from .interfaces import PersonaInterface


@dataclass(frozen=True)
class Persona(PersonaInterface):
    """An immutable persona configuration for an AI agent.

    Each property maps directly to the abstract properties defined in
    :class:`PersonaInterface`.  The ``frozen=True`` flag prevents
    accidental mutation after creation — persona identity should remain
    constant throughout an agent's lifetime.
    """

    _name: str
    _background: str
    _stance: str
    _communication_style: str
    _expertise: list[str] = field(default_factory=list)
    _priorities: list[str] = field(default_factory=list)

    # ---- PersonaInterface implementation --------------------------------

    @property
    def name(self) -> str:
        return self._name

    @property
    def background(self) -> str:
        return self._background

    @property
    def stance(self) -> str:
        return self._stance

    @property
    def communication_style(self) -> str:
        return self._communication_style

    @property
    def expertise(self) -> list[str]:
        return list(self._expertise)

    @property
    def priorities(self) -> list[str]:
        return list(self._priorities)

    # ---- Utilities -------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"Persona(name={self._name!r}, "
            f"expertise={self._expertise!r})"
        )

    def summary(self) -> str:
        """Return a human-readable summary of the persona."""
        lines = [
            f"Name:                {self._name}",
            f"Background:          {self._background}",
            f"Stance:              {self._stance}",
            f"Communication style: {self._communication_style}",
            f"Expertise:           {', '.join(self._expertise)}",
            f"Priorities:          {', '.join(self._priorities)}",
        ]
        return "\n".join(lines)
