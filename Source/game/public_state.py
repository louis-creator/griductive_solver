"""Public, immutable views that deliberately exclude hidden game information."""

from __future__ import annotations

from dataclasses import dataclass

from .models import Clue, Status


@dataclass(frozen=True)
class PublicCharacter:
    cell: str
    name: str
    profession: str
    revealed: bool
    proved_status: Status | None
    revealed_clue: Clue | None


@dataclass(frozen=True)
class PublicGameState:
    puzzle_id: str
    title: str
    size: int
    characters: tuple[PublicCharacter, ...]

    @property
    def revealed_cells(self) -> tuple[str, ...]:
        return tuple(character.cell for character in self.characters if character.revealed)

    @property
    def unresolved_cells(self) -> tuple[str, ...]:
        return tuple(character.cell for character in self.characters if not character.revealed)

    @property
    def proved_statuses(self) -> tuple[tuple[str, Status], ...]:
        return tuple(
            (character.cell, character.proved_status)
            for character in self.characters
            if character.proved_status is not None
        )

    @property
    def active_clues(self) -> tuple[tuple[str, Clue], ...]:
        return tuple(
            (f"CLUE_{character.cell}", character.revealed_clue)
            for character in self.characters
            if character.revealed_clue is not None
        )

