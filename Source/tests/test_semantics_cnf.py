from __future__ import annotations

from itertools import product

import pytest

from game.models import Clue, ClueType, Region, RegionType, Status
from game.regions import all_cells
from logic.cnf import CNFEncoder
from logic.dpll import DPLLSolver
from logic.semantics import evaluate_clue


def clues() -> list[Clue]:
    explicit = Region(RegionType.EXPLICIT, cells=("A1", "B1", "A2"))
    advanced = Region(
        RegionType.INTERSECTION,
        regions=(Region(RegionType.ROW, row=1), Region(RegionType.BOUNDARY)),
    )
    return [
        Clue(ClueType.FACT, target="A1", status=Status.CRIMINAL),
        Clue(ClueType.FACT, target="A1", status=Status.INNOCENT),
        Clue(ClueType.SAME, target="A1", other="B1"),
        Clue(ClueType.DIFFERENT, target="A1", other="B1"),
        *(Clue(ClueType.EXACTLY, k=k, region=explicit) for k in range(4)),
        *(Clue(ClueType.AT_LEAST, k=k, region=explicit) for k in range(4)),
        *(Clue(ClueType.AT_MOST, k=k, region=explicit) for k in range(4)),
        Clue(ClueType.PARITY, parity="EVEN", region=explicit),
        Clue(ClueType.PARITY, parity="ODD", region=explicit),
        Clue(ClueType.EXACTLY, k=1, region=advanced),
        Clue(ClueType.EXACTLY, k=2, region=Region(RegionType.CORNERS)),
    ]


@pytest.mark.parametrize("clue", clues())
def test_cnf_matches_direct_semantics_exhaustively(clue):
    size = 2
    cells = all_cells(size)
    encoder = CNFEncoder(size)
    formula = encoder.encode((clue,))
    solver = DPLLSolver()
    for values in product((False, True), repeat=len(cells)):
        assignment = dict(zip(cells, values))
        assumptions = tuple(
            variable if assignment[cell] else -variable
            for cell, variable in formula.variables.primary.items()
        )
        sat = solver.solve(
            formula.clauses, assumptions=assumptions, num_variables=formula.total_variables
        ).satisfiable
        assert sat is evaluate_clue(clue, assignment, size)


def test_semantics_requires_complete_referenced_assignment():
    clue = Clue(ClueType.SAME, target="A1", other="B1")
    with pytest.raises(ValueError, match="missing"):
        evaluate_clue(clue, {"A1": True}, 2)


def test_cardinality_rejects_invalid_bounds():
    from logic.cardinality import at_least, at_most

    with pytest.raises(ValueError):
        at_least((1,), -1)
    with pytest.raises(ValueError):
        at_most((1,), 2)


def test_variable_map_and_statistics_are_deterministic():
    encoder = CNFEncoder(2)
    formula = encoder.encode((Clue(ClueType.SAME, target="A1", other="B1"),))
    assert formula.variables.primary == {"A1": 1, "B1": 2, "A2": 3, "B2": 4}
    assert formula.primary_count == 4
    assert formula.auxiliary_count == 0
    assert formula.total_variables == 4
    assert formula.clause_count == 2

