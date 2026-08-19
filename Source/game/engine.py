"""Stateful game engine: the sole owner of hidden puzzle information."""

from __future__ import annotations

from enum import Enum

from .models import Puzzle, Status
from .public_state import PublicCharacter, PublicGameState
from .regions import row_major_key


class VerdictOutcome(str, Enum):
    ACCEPTED = "ACCEPTED"
    NOT_PROVABLE = "NOT_PROVABLE"
    CONTRADICTED = "CONTRADICTED"
    INCONSISTENT = "INCONSISTENT"


class GameEngine:
    """Own hidden labels/clues and expose only immutable public snapshots."""

    def __init__(self, puzzle: Puzzle):
        self._puzzle = puzzle
        self._characters = puzzle.character_map()
        self._revealed: set[str] = set()
        self.restart()

    @property
    def puzzle_id(self) -> str:
        return self._puzzle.id

    @property
    def solved(self) -> bool:
        return len(self._revealed) == len(self._characters)

    def restart(self) -> PublicGameState:
        self._revealed = set(self._puzzle.initially_revealed)
        return self.public_state()

    def public_state(self) -> PublicGameState:
        ordered = sorted(
            self._puzzle.characters,
            key=lambda character: row_major_key(character.cell, self._puzzle.size),
        )
        public = tuple(
            PublicCharacter(
                cell=character.cell,
                name=character.name,
                profession=character.profession,
                revealed=character.cell in self._revealed,
                proved_status=character.status if character.cell in self._revealed else None,
                revealed_clue=character.clue if character.cell in self._revealed else None,
            )
            for character in ordered
        )
        return PublicGameState(self._puzzle.id, self._puzzle.title, self._puzzle.size, public)

    def submit_proved_verdict(
        self, cell: str, requested: Status, classification: str
    ) -> VerdictOutcome:
        """Apply a public-logic classification without doing hidden-data reasoning."""
        if cell not in self._characters or cell in self._revealed:
            raise ValueError(f"cell {cell} is absent or already revealed")
        if classification == "INCONSISTENT":
            return VerdictOutcome.INCONSISTENT
        if classification == "UNKNOWN":
            return VerdictOutcome.NOT_PROVABLE
        if classification != requested.value:
            return VerdictOutcome.CONTRADICTED
        # This check protects against malformed puzzle data; only the engine can perform it.
        if self._characters[cell].status is not requested:
            return VerdictOutcome.INCONSISTENT
        self._revealed.add(cell)
        return VerdictOutcome.ACCEPTED

