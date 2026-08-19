"""Validate schema, truth, uniqueness, coverage, and no-guess solve behavior."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from game.engine import GameEngine
from game.loader import load_puzzle
from logic.agent import AgentTerminal, LogicAgent
from logic.semantics import evaluate_clue
from logic.uniqueness import UniquenessResult, check_uniqueness

ROOT = Path(__file__).resolve().parents[1]


def validate(path: Path) -> dict:
    puzzle = load_puzzle(path)
    hidden = {character.cell: character.status.value == "CRIMINAL" for character in puzzle.characters}
    clues_true = all(evaluate_clue(character.clue, hidden, puzzle.size) for character in puzzle.characters)
    uniqueness = check_uniqueness(puzzle)
    engine = GameEngine(puzzle)
    agent = LogicAgent()
    terminal = agent.auto_solve(engine)
    coverage = Counter(character.clue.type.value for character in puzzle.characters)
    passed = clues_true and uniqueness.result is UniquenessResult.UNIQUE and terminal is AgentTerminal.SOLVED
    return {
        "puzzle_id": puzzle.id,
        "schema_valid": True,
        "clues_true": clues_true,
        "uniqueness": uniqueness.result.value,
        "auto_solve": terminal.value,
        "deduction_steps": agent.metrics.deduction_steps,
        "coverage": dict(sorted(coverage.items())),
        "passed": passed,
    }


def main() -> int:
    failures = 0
    for path in sorted((ROOT / "puzzles" / "normal").glob("*.json")):
        result = validate(path)
        mark = "PASS" if result["passed"] else "FAIL"
        print(
            f"{mark} {result['puzzle_id']}: schema=VALID clues={result['clues_true']} "
            f"unique={result['uniqueness']} auto={result['auto_solve']} "
            f"steps={result['deduction_steps']} coverage={result['coverage']}"
        )
        failures += int(not result["passed"])
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

