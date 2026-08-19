"""Small, deterministic, self-contained DPLL SAT solver."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Iterable

Clause = tuple[int, ...]


@dataclass(frozen=True)
class SatResult:
    satisfiable: bool
    assignment: dict[int, bool] | None
    decisions: int
    propagations: int
    backtracks: int
    runtime_seconds: float


class DPLLSolver:
    """DPLL with cascading unit propagation and smallest-variable branching."""

    def solve(
        self,
        clauses: Iterable[Iterable[int]],
        assumptions: Iterable[int] = (),
        num_variables: int | None = None,
    ) -> SatResult:
        started = perf_counter()
        normalized: tuple[Clause, ...] = tuple(tuple(dict.fromkeys(clause)) for clause in clauses)
        assumption_tuple = tuple(assumptions)
        if any(literal == 0 for clause in normalized for literal in clause) or any(
            literal == 0 for literal in assumption_tuple
        ):
            raise ValueError("literal 0 is invalid")
        formula = normalized + tuple((literal,) for literal in assumption_tuple)
        maximum = max((abs(literal) for clause in formula for literal in clause), default=0)
        count = maximum if num_variables is None else num_variables
        if count < maximum:
            raise ValueError("num_variables is smaller than a referenced variable")
        counters = {"decisions": 0, "propagations": 0, "backtracks": 0}
        model = self._search(formula, {}, counters)
        if model is not None:
            for variable in range(1, count + 1):
                model.setdefault(variable, False)
        return SatResult(
            model is not None,
            dict(sorted(model.items())) if model is not None else None,
            counters["decisions"],
            counters["propagations"],
            counters["backtracks"],
            perf_counter() - started,
        )

    @staticmethod
    def _clause_state(clause: Clause, assignment: dict[int, bool]) -> tuple[bool, list[int]]:
        unassigned: list[int] = []
        for literal in clause:
            value = assignment.get(abs(literal))
            if value is None:
                unassigned.append(literal)
            elif value is (literal > 0):
                return True, []
        return False, unassigned

    def _propagate(
        self, clauses: tuple[Clause, ...], assignment: dict[int, bool], counters: dict[str, int]
    ) -> bool:
        while True:
            unit: int | None = None
            for clause in clauses:
                satisfied, unassigned = self._clause_state(clause, assignment)
                if satisfied:
                    continue
                if not unassigned:
                    return False
                if len(unassigned) == 1:
                    unit = unassigned[0]
                    break
            if unit is None:
                return True
            variable, value = abs(unit), unit > 0
            existing = assignment.get(variable)
            if existing is not None and existing is not value:
                return False
            if existing is None:
                assignment[variable] = value
                counters["propagations"] += 1

    def _search(
        self, clauses: tuple[Clause, ...], assignment: dict[int, bool], counters: dict[str, int]
    ) -> dict[int, bool] | None:
        if not self._propagate(clauses, assignment, counters):
            return None
        unsatisfied: list[Clause] = []
        for clause in clauses:
            satisfied, unassigned = self._clause_state(clause, assignment)
            if not satisfied:
                unsatisfied.append(tuple(unassigned))
        if not unsatisfied:
            return assignment
        variable = min(abs(literal) for clause in unsatisfied for literal in clause)
        counters["decisions"] += 1
        for value in (True, False):
            branch = dict(assignment)
            branch[variable] = value
            model = self._search(clauses, branch, counters)
            if model is not None:
                return model
            counters["backtracks"] += 1
        return None

