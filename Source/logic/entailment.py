"""Logical consequence classification by SAT refutation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from game.public_state import PublicGameState

from .cnf import CNFEncoder, CNFFormula
from .dpll import DPLLSolver, SatResult


class Classification(str, Enum):
    CRIMINAL = "CRIMINAL"
    INNOCENT = "INNOCENT"
    UNKNOWN = "UNKNOWN"
    INCONSISTENT = "INCONSISTENT"


@dataclass(frozen=True)
class ClassificationResult:
    cell: str
    classification: Classification
    formula: CNFFormula
    base_result: SatResult
    criminal_assumption_result: SatResult | None
    innocent_assumption_result: SatResult | None

    @property
    def sat_calls(self) -> int:
        return 1 + int(self.criminal_assumption_result is not None) + int(
            self.innocent_assumption_result is not None
        )


class EntailmentChecker:
    def __init__(self, solver: DPLLSolver | None = None):
        self.solver = solver or DPLLSolver()

    def classify(self, state: PublicGameState, cell: str) -> ClassificationResult:
        if cell not in state.unresolved_cells:
            raise ValueError(f"cell {cell} is already resolved or absent")
        formula = CNFEncoder(state.size).encode_public_state(state)
        variable = formula.variables.primary[cell]
        base = self.solver.solve(formula.clauses, num_variables=formula.total_variables)
        if not base.satisfiable:
            return ClassificationResult(
                cell, Classification.INCONSISTENT, formula, base, None, None
            )
        assume_innocent = self.solver.solve(
            formula.clauses, assumptions=(-variable,), num_variables=formula.total_variables
        )
        assume_criminal = self.solver.solve(
            formula.clauses, assumptions=(variable,), num_variables=formula.total_variables
        )
        if not assume_innocent.satisfiable:
            classification = Classification.CRIMINAL
        elif not assume_criminal.satisfiable:
            classification = Classification.INNOCENT
        else:
            classification = Classification.UNKNOWN
        return ClassificationResult(
            cell, classification, formula, base, assume_criminal, assume_innocent
        )

    def classify_all(self, state: PublicGameState) -> tuple[ClassificationResult, ...]:
        return tuple(self.classify(state, cell) for cell in state.unresolved_cells)

