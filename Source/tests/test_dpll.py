from __future__ import annotations

from itertools import product
from random import Random

import pytest

from logic.dpll import DPLLSolver


@pytest.mark.parametrize(
    ("clauses", "sat"),
    [
        ([], True),
        ([()], False),
        ([(1,)], True),
        ([(-1,)], True),
        ([(1,), (-1,)], False),
        ([(1, 2), (-1, 2)], True),
        ([(1, 2), (-1, 2), (1, -2), (-1, -2)], False),
    ],
)
def test_basic_sat_unsat(clauses, sat):
    assert DPLLSolver().solve(clauses).satisfiable is sat


def test_propagation_chain_and_complete_assignment():
    result = DPLLSolver().solve([(1,), (-1, 2), (-2, 3)], num_variables=4)
    assert result.satisfiable
    assert result.assignment == {1: True, 2: True, 3: True, 4: False}
    assert result.propagations == 3


def test_branching_backtracking_statistics_and_determinism():
    clauses = [(1, 2), (-1, 2), (-1, -2)]
    first = DPLLSolver().solve(clauses)
    second = DPLLSolver().solve(clauses)
    assert first.satisfiable and first.assignment == second.assignment
    assert first.decisions >= 1 and first.backtracks >= 1
    assert first.runtime_seconds >= 0


def _brute_force(clauses, variables):
    for values in product((False, True), repeat=variables):
        if all(any(values[abs(lit) - 1] == (lit > 0) for lit in clause) for clause in clauses):
            return True
    return False


def test_random_formulas_match_brute_force():
    random = Random(14003)
    solver = DPLLSolver()
    for _ in range(250):
        variables = random.randint(1, 5)
        clauses = []
        for _ in range(random.randint(0, 10)):
            clause = tuple(
                variable if random.choice((True, False)) else -variable
                for variable in random.sample(
                    range(1, variables + 1), random.randint(0, min(3, variables))
                )
            )
            clauses.append(clause)
        assert solver.solve(clauses, num_variables=variables).satisfiable is _brute_force(
            clauses, variables
        )


def test_assumptions_and_invalid_literal():
    solver = DPLLSolver()
    assert not solver.solve([(1,)], assumptions=(-1,)).satisfiable
    with pytest.raises(ValueError, match="literal 0"):
        solver.solve([(0,)])

