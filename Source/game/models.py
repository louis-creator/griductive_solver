"""Immutable domain models used by the loader and game engine."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Status(str, Enum):
    CRIMINAL = "CRIMINAL"
    INNOCENT = "INNOCENT"


class ClueType(str, Enum):
    FACT = "FACT"
    SAME = "SAME"
    DIFFERENT = "DIFFERENT"
    EXACTLY = "EXACTLY"
    AT_LEAST = "AT_LEAST"
    AT_MOST = "AT_MOST"
    PARITY = "PARITY"


class RegionType(str, Enum):
    ROW = "ROW"
    COLUMN = "COLUMN"
    NEIGHBORS = "NEIGHBORS"
    EXPLICIT = "EXPLICIT"
    INTERSECTION = "INTERSECTION"
    BOUNDARY = "BOUNDARY"
    CORNERS = "CORNERS"
    COMMON_NEIGHBORS = "COMMON_NEIGHBORS"


@dataclass(frozen=True)
class Region:
    type: RegionType
    row: int | None = None
    column: str | None = None
    cell: str | None = None
    cells: tuple[str, ...] = ()
    regions: tuple["Region", ...] = ()


@dataclass(frozen=True)
class Clue:
    type: ClueType
    target: str | None = None
    other: str | None = None
    status: Status | None = None
    k: int | None = None
    parity: str | None = None
    region: Region | None = None


@dataclass(frozen=True)
class HiddenCharacter:
    cell: str
    name: str
    profession: str
    status: Status
    clue: Clue


@dataclass(frozen=True)
class Puzzle:
    id: str
    title: str
    size: int
    characters: tuple[HiddenCharacter, ...]
    initially_revealed: tuple[str, ...]

    def character_map(self) -> dict[str, HiddenCharacter]:
        return {character.cell: character for character in self.characters}

