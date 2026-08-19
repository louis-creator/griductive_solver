"""Direct clue semantics, intentionally independent of CNF and SAT."""

from __future__ import annotations

from game.models import Clue, ClueType, Status
from game.regions import resolve_region


def referenced_cells(clue: Clue, size: int) -> tuple[str, ...]:
    if clue.type is ClueType.FACT:
        return (clue.target,)  # type: ignore[return-value]
    if clue.type in (ClueType.SAME, ClueType.DIFFERENT):
        return (clue.target, clue.other)  # type: ignore[return-value]
    if clue.region is None:
        raise ValueError(f"{clue.type.value} requires a region")
    return resolve_region(clue.region, size)


def evaluate_clue(clue: Clue, assignment: dict[str, bool], size: int) -> bool:
    """Evaluate one clue directly under a complete primary assignment."""
    cells = referenced_cells(clue, size)
    missing = [cell for cell in cells if cell not in assignment]
    if missing:
        raise ValueError(f"assignment is missing cells: {', '.join(missing)}")
    if clue.type is ClueType.FACT:
        expected = clue.status is Status.CRIMINAL
        return assignment[cells[0]] is expected
    if clue.type is ClueType.SAME:
        return assignment[cells[0]] == assignment[cells[1]]
    if clue.type is ClueType.DIFFERENT:
        return assignment[cells[0]] != assignment[cells[1]]
    count = sum(assignment[cell] for cell in cells)
    if clue.type is ClueType.EXACTLY:
        return count == clue.k
    if clue.type is ClueType.AT_LEAST:
        return count >= clue.k  # type: ignore[operator]
    if clue.type is ClueType.AT_MOST:
        return count <= clue.k  # type: ignore[operator]
    if clue.type is ClueType.PARITY:
        return (count % 2 == 0) if clue.parity == "EVEN" else (count % 2 == 1)
    raise ValueError(f"unsupported clue type: {clue.type}")

