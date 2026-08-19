"""Full-clue uniqueness checking with a primary-only blocking clause."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from game.models import Puzzle, Status

from .cnf import CNFEncoder
from .dpll import DPLLSolver, SatResult


class UniquenessResult(str, Enum):
    UNIQUE = "UNIQUE"
    NON_UNIQUE = "NON_UNIQUE"
    INCONSISTENT = "INCONSISTENT"


@dataclass(frozen=True)
class UniquenessCheck:
    result: UniquenessResult
    solution: dict[str, Status] | None
    first_solve: SatResult
    second_solve: SatResult | None


def check_uniqueness(puzzle: Puzzle, solver: DPLLSolver | None = None) -> UniquenessCheck:
    encoder = CNFEncoder(puzzle.size)
    formula = encoder.encode_complete_puzzle(puzzle)
    dpll = solver or DPLLSolver()
    first = dpll.solve(formula.clauses, num_variables=formula.total_variables)
    if not first.satisfiable or first.assignment is None:
        return UniquenessCheck(UniquenessResult.INCONSISTENT, None, first, None)
    solution = {
        cell: Status.CRIMINAL if first.assignment[variable] else Status.INNOCENT
        for cell, variable in formula.variables.primary.items()
    }
    blocking = tuple(
        -variable if first.assignment[variable] else variable
        for variable in formula.variables.primary.values()
    )
    second = dpll.solve(
        formula.clauses + (blocking,), num_variables=formula.total_variables
    )
    result = UniquenessResult.NON_UNIQUE if second.satisfiable else UniquenessResult.UNIQUE
    return UniquenessCheck(result, solution, first, second)

