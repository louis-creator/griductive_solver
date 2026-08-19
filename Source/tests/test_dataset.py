from __future__ import annotations

from pathlib import Path

from experiments.validate_puzzles import validate
from game.loader import load_puzzle
from game.engine import GameEngine
from logic.agent import AgentTerminal, LogicAgent
from logic.uniqueness import UniquenessResult, check_uniqueness


ROOT = Path(__file__).resolve().parents[1]


def test_all_normal_puzzles_validate_unique_and_auto_solve():
    paths = sorted((ROOT / "puzzles" / "normal").glob("*.json"))
    assert len(paths) >= 8
    assert {load_puzzle(path).size for path in paths} >= {3, 4}
    for path in paths:
        assert validate(path)["passed"], path.name


def test_deliberate_fixtures():
    inconsistent = load_puzzle(ROOT / "puzzles" / "fixtures" / "fixture_inconsistent.json")
    non_unique = load_puzzle(ROOT / "puzzles" / "fixtures" / "fixture_non_unique.json")
    assert check_uniqueness(inconsistent).result is UniquenessResult.INCONSISTENT
    assert check_uniqueness(non_unique).result is UniquenessResult.NON_UNIQUE


def test_dpll_showcase_exercises_decision_and_backtrack_metrics():
    puzzle = load_puzzle(ROOT / "puzzles" / "normal" / "3x3_dpll_showcase_01.json")
    engine = GameEngine(puzzle)
    agent = LogicAgent()
    assert agent.auto_solve(engine) is AgentTerminal.SOLVED
    assert agent.metrics.decisions > 0
    assert agent.metrics.backtracks > 0
