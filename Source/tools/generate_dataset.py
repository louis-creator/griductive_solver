"""Generate the fixed, deterministic puzzle dataset used by tests and experiments."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NORMAL = ROOT / "puzzles" / "normal"
FIXTURES = ROOT / "puzzles" / "fixtures"

NAMES = [
    "Avery", "Blake", "Casey", "Devon", "Emery", "Finley", "Gray", "Harper",
    "Indigo", "Jordan", "Kai", "Logan", "Morgan", "Noel", "Oakley", "Parker",
    "Quinn", "Riley", "Sawyer", "Taylor", "Uma", "Vale", "Winter", "Xen",
    "Yael", "Zion",
]
PROFESSIONS = [
    "Architect", "Baker", "Chemist", "Doctor", "Engineer", "Florist", "Guide", "Historian",
    "Illustrator", "Journalist", "Keeper", "Librarian", "Mechanic", "Nurse", "Optician",
    "Pilot", "Researcher", "Sailor", "Teacher", "Urbanist", "Veterinarian", "Writer",
]


def cells(size: int) -> list[str]:
    return [f"{chr(65 + column)}{row}" for row in range(1, size + 1) for column in range(size)]


def pair_clue(kind: str, owner: str, target: str, statuses: dict[str, bool]) -> dict:
    if kind == "FACT":
        return {"type": "FACT", "target": target, "status": "CRIMINAL" if statuses[target] else "INNOCENT"}
    if kind == "BINARY":
        return {
            "type": "SAME" if statuses[owner] == statuses[target] else "DIFFERENT",
            "target": owner,
            "other": target,
        }
    region = {"type": "EXPLICIT", "cells": [owner, target]}
    if kind == "EXACTLY":
        return {"type": "EXACTLY", "k": int(statuses[owner]) + int(statuses[target]), "region": region}
    if kind == "BOUND":
        if statuses[target]:
            return {"type": "AT_LEAST", "k": int(statuses[owner]) + 1, "region": region}
        return {"type": "AT_MOST", "k": int(statuses[owner]), "region": region}
    if kind == "PARITY":
        parity = "ODD" if (int(statuses[owner]) + int(statuses[target])) % 2 else "EVEN"
        return {"type": "PARITY", "parity": parity, "region": region}
    raise ValueError(kind)


def final_clue(size: int, statuses: dict[str, bool], advanced: str, first: str) -> dict:
    board = cells(size)
    if advanced == "CORNERS":
        selected = [board[0], board[size - 1], board[-size], board[-1]]
        region = {"type": "CORNERS"}
    elif advanced == "BOUNDARY":
        selected = [
            cell for index, cell in enumerate(board)
            if index // size in (0, size - 1) or index % size in (0, size - 1)
        ]
        region = {"type": "BOUNDARY"}
    elif advanced == "INTERSECTION":
        selected = [first, board[1]]
        region = {
            "type": "INTERSECTION",
            "regions": [
                {"type": "BOUNDARY"},
                {"type": "EXPLICIT", "cells": selected},
            ],
        }
    else:
        selected = [f"B1", f"B2"]
        region = {"type": "COMMON_NEIGHBORS", "cells": ["A1", "C1"]}
    return {"type": "EXACTLY", "k": sum(statuses[cell] for cell in selected), "region": region}


def advanced_pair_clue(owner: str, target: str, statuses: dict[str, bool]) -> dict:
    """An INTERSECTION extension that still forces target once owner is known."""
    region = {
        "type": "INTERSECTION",
        "regions": [
            {"type": "BOUNDARY"},
            {"type": "EXPLICIT", "cells": [owner, target]},
        ],
    }
    return {
        "type": "EXACTLY",
        "k": int(statuses[owner]) + int(statuses[target]),
        "region": region,
    }


def puzzle(
    puzzle_id: str,
    title: str,
    size: int,
    pattern: str,
    styles: list[str],
    advanced: str,
) -> dict:
    board = cells(size)
    values = [(char == "1") for char in (pattern * (len(board) // len(pattern) + 1))[: len(board)]]
    statuses = dict(zip(board, values))
    characters = []
    for index, cell in enumerate(board):
        facts_only = set(styles) == {"FACT"}
        if index + 1 == len(board):
            clue = (
                final_clue(size, statuses, advanced, board[0])
                if facts_only
                else {"type": "FACT", "target": board[0], "status": "CRIMINAL" if statuses[board[0]] else "INNOCENT"}
            )
        elif index + 2 == len(board) and not facts_only:
            clue = advanced_pair_clue(cell, board[index + 1], statuses)
        else:
            clue = pair_clue(styles[index % len(styles)], cell, board[index + 1], statuses)
        characters.append({
            "cell": cell,
            "name": NAMES[index],
            "profession": PROFESSIONS[index % len(PROFESSIONS)],
            "status": "CRIMINAL" if statuses[cell] else "INNOCENT",
            "clue": clue,
        })
    return {
        "id": puzzle_id,
        "title": title,
        "size": size,
        "characters": characters,
        "initially_revealed": [board[0]],
    }


def fixture(puzzle_id: str, inconsistent: bool) -> dict:
    board = cells(2)
    characters = []
    for index, cell in enumerate(board):
        if inconsistent:
            clue = {"type": "FACT", "target": "A1", "status": "CRIMINAL" if index % 2 == 0 else "INNOCENT"}
        else:
            clue = {"type": "SAME", "target": "A1", "other": "B1"}
        characters.append({
            "cell": cell, "name": NAMES[index], "profession": PROFESSIONS[index],
            "status": "CRIMINAL" if index % 2 == 0 else "INNOCENT", "clue": clue,
        })
    return {
        "id": puzzle_id,
        "title": "Inconsistent Fixture" if inconsistent else "Non-unique Fixture",
        "size": 2,
        "characters": characters,
        "initially_revealed": ["A1"],
    }


def solver_showcase() -> dict:
    """A progressive case whose first DPLL model requires a failed branch/backtrack."""
    statuses = {
        "A1": "CRIMINAL",
        "B1": "INNOCENT",
        "C1": "INNOCENT",
        "A2": "CRIMINAL",
        "B2": "CRIMINAL",
        "C2": "INNOCENT",
        "A3": "INNOCENT",
        "B3": "CRIMINAL",
        "C3": "INNOCENT",
    }
    clues = {
        "A1": {"type": "SAME", "target": "B1", "other": "C1"},
        "B1": {"type": "FACT", "target": "A1", "status": "CRIMINAL"},
        "C1": {"type": "FACT", "target": "A2", "status": "CRIMINAL"},
        "A2": {"type": "FACT", "target": "B2", "status": "CRIMINAL"},
        "B2": {"type": "FACT", "target": "C2", "status": "INNOCENT"},
        "C2": {"type": "FACT", "target": "B3", "status": "CRIMINAL"},
        "A3": {
            "type": "AT_MOST",
            "k": 1,
            "region": {"type": "EXPLICIT", "cells": ["B1", "C1"]},
        },
        "B3": {"type": "FACT", "target": "C3", "status": "INNOCENT"},
        "C3": {"type": "FACT", "target": "A3", "status": "INNOCENT"},
    }
    return {
        "id": "3x3_dpll_showcase_01",
        "title": "DPLL Backtracking Lab",
        "size": 3,
        "characters": [
            {
                "cell": cell,
                "name": NAMES[index],
                "profession": PROFESSIONS[index],
                "status": statuses[cell],
                "clue": clues[cell],
            }
            for index, cell in enumerate(cells(3))
        ],
        "initially_revealed": ["A1", "A3"],
    }


PUZZLES = [
    solver_showcase(),
    puzzle("3x3_easy_01", "Easy Investigation", 3, "101001011", ["FACT"], "INTERSECTION"),
    puzzle("3x3_binary_01", "Partners and Opposites", 3, "110010101", ["BINARY"], "CORNERS"),
    puzzle("3x3_counting_01", "Counting the Evidence", 3, "101101000", ["EXACTLY", "BOUND"], "BOUNDARY"),
    puzzle("3x3_mixed_01", "Mixed Testimony", 3, "101110010", ["BINARY", "EXACTLY", "BOUND", "FACT"], "INTERSECTION"),
    puzzle("3x3_extensions_01", "Parity Patrol", 3, "100111010", ["PARITY", "BINARY"], "COMMON_NEIGHBORS"),
    puzzle("4x4_easy_01", "Larger Easy Case", 4, "10100110", ["FACT"], "INTERSECTION"),
    puzzle("4x4_medium_01", "Sixteen Suspects", 4, "11010010", ["BINARY", "EXACTLY"], "CORNERS"),
    puzzle("4x4_mixed_01", "Mixed City Case", 4, "10111000", ["BINARY", "BOUND", "PARITY", "EXACTLY"], "BOUNDARY"),
    puzzle("4x4_counting_01", "Counting Heavy", 4, "10110100", ["EXACTLY", "BOUND", "EXACTLY"], "CORNERS"),
]


def main() -> None:
    NORMAL.mkdir(parents=True, exist_ok=True)
    FIXTURES.mkdir(parents=True, exist_ok=True)
    for data in PUZZLES:
        (NORMAL / f"{data['id']}.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    for data in (fixture("fixture_inconsistent", True), fixture("fixture_non_unique", False)):
        (FIXTURES / f"{data['id']}.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"Generated {len(PUZZLES)} normal puzzles and 2 fixtures")


if __name__ == "__main__":
    main()
