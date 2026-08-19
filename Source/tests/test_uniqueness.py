from __future__ import annotations

from conftest import base_raw
from game.loader import parse_puzzle
from logic.uniqueness import UniquenessResult, check_uniqueness


def test_unique_non_unique_inconsistent():
    unique = parse_puzzle(base_raw())
    assert check_uniqueness(unique).result is UniquenessResult.UNIQUE

    non_unique_raw = base_raw()
    for character in non_unique_raw["characters"]:
        character["clue"] = {"type": "SAME", "target": "A1", "other": "B1"}
    assert check_uniqueness(parse_puzzle(non_unique_raw)).result is UniquenessResult.NON_UNIQUE

    inconsistent_raw = base_raw()
    inconsistent_raw["characters"][0]["clue"] = {
        "type": "FACT", "target": "A1", "status": "CRIMINAL"
    }
    inconsistent_raw["characters"][1]["clue"] = {
        "type": "FACT", "target": "A1", "status": "INNOCENT"
    }
    assert check_uniqueness(parse_puzzle(inconsistent_raw)).result is UniquenessResult.INCONSISTENT

