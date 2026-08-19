"""Automatic CNF encoding from structured public clues."""

from __future__ import annotations

from dataclasses import dataclass

from game.models import Clue, ClueType, Puzzle, Status
from game.public_state import PublicGameState
from game.regions import all_cells, resolve_region

from .cardinality import at_least, at_most, exactly, parity

Clause = tuple[int, ...]


@dataclass(frozen=True)
class VariableMap:
    primary: dict[str, int]
    auxiliary: dict[str, int]

    @classmethod
    def for_size(cls, size: int) -> "VariableMap":
        return cls({cell: index + 1 for index, cell in enumerate(all_cells(size))}, {})

    @property
    def total_variables(self) -> int:
        return len(self.primary) + len(self.auxiliary)


@dataclass(frozen=True)
class CNFFormula:
    clauses: tuple[Clause, ...]
    variables: VariableMap

    @property
    def primary_count(self) -> int:
        return len(self.variables.primary)

    @property
    def auxiliary_count(self) -> int:
        return len(self.variables.auxiliary)

    @property
    def total_variables(self) -> int:
        return self.variables.total_variables

    @property
    def clause_count(self) -> int:
        return len(self.clauses)


class CNFEncoder:
    def __init__(self, size: int):
        self.size = size
        self.variables = VariableMap.for_size(size)

    def encode_clue(self, clue: Clue) -> list[Clause]:
        variable = self.variables.primary
        if clue.type is ClueType.FACT:
            literal = variable[clue.target]  # type: ignore[index]
            return [(literal if clue.status is Status.CRIMINAL else -literal,)]
        if clue.type is ClueType.SAME:
            left, right = variable[clue.target], variable[clue.other]  # type: ignore[index]
            return [(-left, right), (left, -right)]
        if clue.type is ClueType.DIFFERENT:
            left, right = variable[clue.target], variable[clue.other]  # type: ignore[index]
            return [(left, right), (-left, -right)]
        if clue.region is None:
            raise ValueError(f"{clue.type.value} requires a region")
        literals = tuple(variable[cell] for cell in resolve_region(clue.region, self.size))
        if clue.type is ClueType.EXACTLY:
            return exactly(literals, clue.k)  # type: ignore[arg-type]
        if clue.type is ClueType.AT_LEAST:
            return at_least(literals, clue.k)  # type: ignore[arg-type]
        if clue.type is ClueType.AT_MOST:
            return at_most(literals, clue.k)  # type: ignore[arg-type]
        if clue.type is ClueType.PARITY:
            return parity(literals, odd=clue.parity == "ODD")
        raise ValueError(f"unsupported clue type: {clue.type}")

    def encode(self, clues: tuple[Clue, ...], verdicts: tuple[tuple[str, Status], ...] = ()) -> CNFFormula:
        clauses: list[Clause] = []
        for clue in clues:
            clauses.extend(self.encode_clue(clue))
        for cell, status in verdicts:
            variable = self.variables.primary[cell]
            clauses.append((variable if status is Status.CRIMINAL else -variable,))
        return CNFFormula(tuple(clauses), self.variables)

    def encode_public_state(self, state: PublicGameState) -> CNFFormula:
        clues = tuple(clue for _, clue in state.active_clues)
        return self.encode(clues, state.proved_statuses)

    def encode_complete_puzzle(self, puzzle: Puzzle) -> CNFFormula:
        if puzzle.size != self.size:
            raise ValueError("puzzle size does not match encoder")
        return self.encode(tuple(character.clue for character in puzzle.characters))

