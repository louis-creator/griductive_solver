"""Strict JSON puzzle loading and validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import Clue, ClueType, HiddenCharacter, Puzzle, Region, RegionType, Status
from .regions import all_cells, parse_cell, resolve_region


class PuzzleValidationError(ValueError):
    """Raised with a user-facing explanation for malformed puzzle data."""


def _enum(enum_type: type, raw: Any, label: str):
    try:
        return enum_type(raw)
    except (ValueError, TypeError) as exc:
        choices = ", ".join(item.value for item in enum_type)
        raise PuzzleValidationError(f"{label} must be one of: {choices}") from exc


def _region(raw: Any, size: int) -> Region:
    if not isinstance(raw, dict):
        raise PuzzleValidationError("region must be an object")
    region_type = _enum(RegionType, raw.get("type"), "region.type")
    regions_raw = raw.get("regions", [])
    if not isinstance(regions_raw, list):
        raise PuzzleValidationError("region.regions must be a list")
    children = tuple(_region(child, size) for child in regions_raw)
    cells_raw = raw.get("cells", [])
    if not isinstance(cells_raw, list):
        raise PuzzleValidationError("region.cells must be a list")
    region = Region(
        type=region_type,
        row=raw.get("row"),
        column=raw.get("column"),
        cell=raw.get("cell"),
        cells=tuple(cells_raw),
        regions=children,
    )
    try:
        resolve_region(region, size)
    except (ValueError, TypeError) as exc:
        raise PuzzleValidationError(f"invalid {region_type.value} region: {exc}") from exc
    return region


def _valid_cell(raw: Any, size: int, label: str) -> str:
    if not isinstance(raw, str):
        raise PuzzleValidationError(f"{label} must be a cell string")
    try:
        parse_cell(raw, size)
    except ValueError as exc:
        raise PuzzleValidationError(f"invalid {label}: {exc}") from exc
    return raw


def _clue(raw: Any, size: int) -> Clue:
    if not isinstance(raw, dict):
        raise PuzzleValidationError("clue must be an object")
    clue_type = _enum(ClueType, raw.get("type"), "clue.type")
    if clue_type is ClueType.FACT:
        return Clue(
            clue_type,
            target=_valid_cell(raw.get("target"), size, "FACT target"),
            status=_enum(Status, raw.get("status"), "FACT status"),
        )
    if clue_type in (ClueType.SAME, ClueType.DIFFERENT):
        target = _valid_cell(raw.get("target"), size, f"{clue_type.value} target")
        other = _valid_cell(raw.get("other"), size, f"{clue_type.value} other")
        if target == other:
            raise PuzzleValidationError(f"{clue_type.value} requires two distinct cells")
        return Clue(clue_type, target=target, other=other)
    region = _region(raw.get("region"), size)
    region_size = len(resolve_region(region, size))
    if clue_type in (ClueType.EXACTLY, ClueType.AT_LEAST, ClueType.AT_MOST):
        k = raw.get("k")
        if isinstance(k, bool) or not isinstance(k, int) or not 0 <= k <= region_size:
            raise PuzzleValidationError(
                f"{clue_type.value}.k must be an integer from 0 to region size {region_size}"
            )
        return Clue(clue_type, k=k, region=region)
    parity = raw.get("parity")
    if parity not in ("EVEN", "ODD"):
        raise PuzzleValidationError("PARITY.parity must be EVEN or ODD")
    return Clue(clue_type, parity=parity, region=region)


def parse_puzzle(raw: Any) -> Puzzle:
    if not isinstance(raw, dict):
        raise PuzzleValidationError("puzzle root must be an object")
    size = raw.get("size")
    if isinstance(size, bool) or not isinstance(size, int) or not 1 <= size <= 26:
        raise PuzzleValidationError("size must be an integer from 1 to 26")
    puzzle_id, title = raw.get("id"), raw.get("title")
    if not isinstance(puzzle_id, str) or not puzzle_id.strip():
        raise PuzzleValidationError("id must be a non-empty string")
    if not isinstance(title, str) or not title.strip():
        raise PuzzleValidationError("title must be a non-empty string")
    characters_raw = raw.get("characters")
    if not isinstance(characters_raw, list) or len(characters_raw) != size * size:
        raise PuzzleValidationError(f"characters must contain exactly {size * size} entries")
    characters: list[HiddenCharacter] = []
    seen: set[str] = set()
    for index, item in enumerate(characters_raw):
        if not isinstance(item, dict):
            raise PuzzleValidationError(f"characters[{index}] must be an object")
        cell = _valid_cell(item.get("cell"), size, f"characters[{index}].cell")
        if cell in seen:
            raise PuzzleValidationError(f"duplicate character cell: {cell}")
        seen.add(cell)
        name, profession = item.get("name"), item.get("profession")
        if not isinstance(name, str) or not name.strip():
            raise PuzzleValidationError(f"character {cell} has invalid name")
        if not isinstance(profession, str) or not profession.strip():
            raise PuzzleValidationError(f"character {cell} has invalid profession")
        characters.append(HiddenCharacter(
            cell=cell,
            name=name,
            profession=profession,
            status=_enum(Status, item.get("status"), f"character {cell} status"),
            clue=_clue(item.get("clue"), size),
        ))
    expected = set(all_cells(size))
    if seen != expected:
        missing = ", ".join(sorted(expected - seen))
        raise PuzzleValidationError(f"characters do not cover board; missing: {missing}")
    initially = raw.get("initially_revealed", [])
    if not isinstance(initially, list) or len(set(initially)) != len(initially):
        raise PuzzleValidationError("initially_revealed must be a list of distinct cells")
    for cell in initially:
        _valid_cell(cell, size, "initially_revealed cell")
    return Puzzle(puzzle_id, title, size, tuple(characters), tuple(initially))


def load_puzzle(path: str | Path) -> Puzzle:
    try:
        with Path(path).open("r", encoding="utf-8") as handle:
            raw = json.load(handle)
    except json.JSONDecodeError as exc:
        raise PuzzleValidationError(f"malformed JSON at line {exc.lineno}: {exc.msg}") from exc
    except OSError as exc:
        raise PuzzleValidationError(f"cannot read puzzle: {exc}") from exc
    return parse_puzzle(raw)
