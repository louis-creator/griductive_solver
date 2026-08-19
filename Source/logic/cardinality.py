"""Reusable direct combinatorial CNF encodings for small regions."""

from __future__ import annotations

from itertools import combinations, product

Clause = tuple[int, ...]


def at_most(literals: tuple[int, ...], k: int) -> list[Clause]:
    if not 0 <= k <= len(literals):
        raise ValueError("k is outside cardinality range")
    return [tuple(-literal for literal in subset) for subset in combinations(literals, k + 1)]


def at_least(literals: tuple[int, ...], k: int) -> list[Clause]:
    if not 0 <= k <= len(literals):
        raise ValueError("k is outside cardinality range")
    return [tuple(subset) for subset in combinations(literals, len(literals) - k + 1)]


def exactly(literals: tuple[int, ...], k: int) -> list[Clause]:
    return at_most(literals, k) + at_least(literals, k)


def parity(literals: tuple[int, ...], odd: bool) -> list[Clause]:
    """Forbid every primary assignment having the wrong parity."""
    clauses: list[Clause] = []
    for values in product((False, True), repeat=len(literals)):
        if (sum(values) % 2 == 1) != odd:
            clauses.append(tuple(-literal if value else literal for literal, value in zip(literals, values)))
    return clauses

