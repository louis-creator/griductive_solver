from __future__ import annotations

import json

import pytest

from conftest import base_raw
from game.loader import PuzzleValidationError, load_puzzle, parse_puzzle
from game.models import Region, RegionType
from game.regions import all_cells, parse_cell, resolve_region


def test_coordinates_and_all_cells():
    assert parse_cell("C2", 3) == (2, 1)
    assert all_cells(2) == ("A1", "B1", "A2", "B2")
    with pytest.raises(ValueError, match="outside"):
        parse_cell("D1", 3)
    with pytest.raises(ValueError, match="invalid"):
        parse_cell("1A", 3)


def test_required_regions():
    assert resolve_region(Region(RegionType.ROW, row=2), 3) == ("A2", "B2", "C2")
    assert resolve_region(Region(RegionType.COLUMN, column="B"), 3) == ("B1", "B2", "B3")
    assert resolve_region(Region(RegionType.NEIGHBORS, cell="B2"), 3) == (
        "A1", "B1", "C1", "A2", "C2", "A3", "B3", "C3"
    )
    assert resolve_region(Region(RegionType.NEIGHBORS, cell="B1"), 3) == (
        "A1", "C1", "A2", "B2", "C2"
    )
    assert resolve_region(Region(RegionType.NEIGHBORS, cell="A1"), 3) == (
        "B1", "A2", "B2"
    )
    assert resolve_region(Region(RegionType.EXPLICIT, cells=("C3", "A1")), 3) == ("A1", "C3")


def test_advanced_regions():
    intersection = Region(
        RegionType.INTERSECTION,
        regions=(Region(RegionType.ROW, row=1), Region(RegionType.BOUNDARY)),
    )
    assert resolve_region(intersection, 4) == ("A1", "B1", "C1", "D1")
    assert resolve_region(Region(RegionType.BOUNDARY), 3) == (
        "A1", "B1", "C1", "A2", "C2", "A3", "B3", "C3"
    )
    assert resolve_region(Region(RegionType.CORNERS), 4) == ("A1", "D1", "A4", "D4")
    common = Region(RegionType.COMMON_NEIGHBORS, cells=("A1", "C1"))
    assert resolve_region(common, 3) == ("B1", "B2")


def test_valid_loader_and_file(tmp_path):
    raw = base_raw()
    puzzle = parse_puzzle(raw)
    assert puzzle.size == 2 and len(puzzle.characters) == 4
    path = tmp_path / "puzzle.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    assert load_puzzle(path).id == "sample"


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda raw: raw["characters"].__setitem__(1, raw["characters"][0]), "duplicate"),
        (lambda raw: raw["characters"][0].__setitem__("cell", "Z9"), "invalid"),
        (lambda raw: raw["characters"][0].__setitem__("status", "MAYBE"), "must be one"),
        (lambda raw: raw["characters"][0].__setitem__("clue", {"type": "MAGIC"}), "must be one"),
        (lambda raw: raw.__setitem__("initially_revealed", ["Z9"]), "invalid"),
    ],
)
def test_loader_rejects_bad_data(mutate, message):
    raw = base_raw()
    mutate(raw)
    with pytest.raises(PuzzleValidationError, match=message):
        parse_puzzle(raw)


def test_loader_rejects_invalid_region_k_and_malformed_json(tmp_path):
    raw = base_raw()
    raw["characters"][0]["clue"] = {
        "type": "EXACTLY", "k": 3, "region": {"type": "ROW", "row": 1}
    }
    with pytest.raises(PuzzleValidationError, match="from 0 to region size"):
        parse_puzzle(raw)
    raw = base_raw()
    raw["characters"][0]["clue"] = {
        "type": "EXACTLY", "k": 1,
        "region": {"type": "EXPLICIT", "cells": ["A1", "A1"]},
    }
    with pytest.raises(PuzzleValidationError, match="duplicate"):
        parse_puzzle(raw)
    path = tmp_path / "bad.json"
    path.write_text("{broken", encoding="utf-8")
    with pytest.raises(PuzzleValidationError, match="malformed JSON"):
        load_puzzle(path)

