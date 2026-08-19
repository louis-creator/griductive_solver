"""Coordinate parsing and the single authoritative region resolver."""

from __future__ import annotations

import re

from .models import Region, RegionType

_CELL_RE = re.compile(r"^([A-Z])(\d+)$")


def cell_id(column_index: int, row: int) -> str:
    if not 0 <= column_index < 26 or row < 1:
        raise ValueError("cell indices are out of range")
    return f"{chr(ord('A') + column_index)}{row}"


def parse_cell(cell: str, size: int) -> tuple[int, int]:
    match = _CELL_RE.fullmatch(cell)
    if not match:
        raise ValueError(f"invalid cell coordinate: {cell!r}")
    column = ord(match.group(1)) - ord("A")
    row = int(match.group(2)) - 1
    if not (0 <= column < size and 0 <= row < size):
        raise ValueError(f"cell {cell!r} is outside the {size}x{size} board")
    return column, row


def all_cells(size: int) -> tuple[str, ...]:
    return tuple(cell_id(column, row) for row in range(1, size + 1) for column in range(size))


def row_major_key(cell: str, size: int) -> tuple[int, int]:
    column, row = parse_cell(cell, size)
    return row, column


def resolve_region(region: Region, size: int) -> tuple[str, ...]:
    """Resolve a structured region deterministically in row-major order."""
    cells: set[str]
    if region.type is RegionType.ROW:
        if region.row is None or not 1 <= region.row <= size:
            raise ValueError(f"row must be between 1 and {size}")
        cells = {cell_id(column, region.row) for column in range(size)}
    elif region.type is RegionType.COLUMN:
        if region.column is None or len(region.column) != 1:
            raise ValueError("column must be one uppercase letter")
        column = ord(region.column) - ord("A")
        if not 0 <= column < size:
            raise ValueError(f"column {region.column!r} is outside the board")
        cells = {cell_id(column, row) for row in range(1, size + 1)}
    elif region.type is RegionType.NEIGHBORS:
        if region.cell is None:
            raise ValueError("NEIGHBORS requires cell")
        column, row = parse_cell(region.cell, size)
        cells = {
            cell_id(c, r + 1)
            for r in range(max(0, row - 1), min(size, row + 2))
            for c in range(max(0, column - 1), min(size, column + 2))
            if (c, r) != (column, row)
        }
    elif region.type is RegionType.EXPLICIT:
        if len(set(region.cells)) != len(region.cells):
            raise ValueError("EXPLICIT region contains duplicate cells")
        for cell in region.cells:
            parse_cell(cell, size)
        cells = set(region.cells)
    elif region.type is RegionType.INTERSECTION:
        if len(region.regions) < 2:
            raise ValueError("INTERSECTION requires at least two regions")
        resolved = [set(resolve_region(child, size)) for child in region.regions]
        cells = set.intersection(*resolved)
    elif region.type is RegionType.BOUNDARY:
        cells = {
            cell_id(column, row + 1)
            for row in range(size)
            for column in range(size)
            if row in (0, size - 1) or column in (0, size - 1)
        }
    elif region.type is RegionType.CORNERS:
        cells = {
            cell_id(0, 1), cell_id(size - 1, 1),
            cell_id(0, size), cell_id(size - 1, size),
        }
    elif region.type is RegionType.COMMON_NEIGHBORS:
        if len(region.cells) < 2 or len(set(region.cells)) != len(region.cells):
            raise ValueError("COMMON_NEIGHBORS requires at least two distinct cells")
        neighbor_sets = [
            set(resolve_region(Region(RegionType.NEIGHBORS, cell=cell), size))
            for cell in region.cells
        ]
        cells = set.intersection(*neighbor_sets)
    else:  # pragma: no cover - enum exhaustiveness guard
        raise ValueError(f"unsupported region type: {region.type}")
    return tuple(sorted(cells, key=lambda item: row_major_key(item, size)))

