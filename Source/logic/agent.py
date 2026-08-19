"""Public-knowledge-only deductive agent, hints, auto solve, and traces."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path

from game.engine import GameEngine, VerdictOutcome
from game.models import Status
from game.public_state import PublicGameState

from .dpll import SatResult
from .entailment import Classification, ClassificationResult, EntailmentChecker


class AgentTerminal(str, Enum):
    SOLVED = "SOLVED"
    STALLED = "STALLED"
    INCONSISTENT = "INCONSISTENT"


@dataclass(frozen=True)
class ForcedMove:
    cell: str
    status: Status
    result: ClassificationResult


@dataclass(frozen=True)
class TraceEntry:
    step: int
    active_clue_ids: tuple[str, ...]
    target: str
    assumption_tested: str
    assumption_result: str
    verdict: str
    newly_revealed_clue: str
    sat_calls: int
    decisions: int
    propagations: int
    backtracks: int
    runtime_seconds: float


@dataclass
class AgentMetrics:
    sat_calls: int = 0
    decisions: int = 0
    propagations: int = 0
    backtracks: int = 0
    runtime_seconds: float = 0.0
    deduction_steps: int = 0


def _solver_results(result: ClassificationResult) -> tuple[SatResult, ...]:
    return tuple(
        item
        for item in (
            result.base_result,
            result.criminal_assumption_result,
            result.innocent_assumption_result,
        )
        if item is not None
    )


class LogicAgent:
    """The constructor and methods accept no full Puzzle or hidden solution."""

    def __init__(self, checker: EntailmentChecker | None = None):
        self.checker = checker or EntailmentChecker()
        self.trace: list[TraceEntry] = []
        self.metrics = AgentMetrics()

    def reset(self) -> None:
        self.trace.clear()
        self.metrics = AgentMetrics()

    def classify(self, state: PublicGameState, cell: str) -> ClassificationResult:
        result = self.checker.classify(state, cell)
        self._accumulate(result)
        return result

    def classify_all(self, state: PublicGameState) -> tuple[ClassificationResult, ...]:
        return tuple(self.classify(state, cell) for cell in state.unresolved_cells)

    def _accumulate(self, result: ClassificationResult) -> None:
        results = _solver_results(result)
        self.metrics.sat_calls += len(results)
        self.metrics.decisions += sum(item.decisions for item in results)
        self.metrics.propagations += sum(item.propagations for item in results)
        self.metrics.backtracks += sum(item.backtracks for item in results)
        self.metrics.runtime_seconds += sum(item.runtime_seconds for item in results)

    def next_forced_verdict(self, state: PublicGameState) -> ForcedMove | None:
        for cell in state.unresolved_cells:
            result = self.classify(state, cell)
            if result.classification is Classification.INCONSISTENT:
                return ForcedMove(cell, Status.INNOCENT, result)
            if result.classification is Classification.CRIMINAL:
                return ForcedMove(cell, Status.CRIMINAL, result)
            if result.classification is Classification.INNOCENT:
                return ForcedMove(cell, Status.INNOCENT, result)
        return None

    def hint(self, state: PublicGameState) -> ForcedMove | None:
        return self.next_forced_verdict(state)

    def apply_next(self, engine: GameEngine) -> VerdictOutcome | None:
        before = engine.public_state()
        if not before.unresolved_cells:
            return None
        move = self.next_forced_verdict(before)
        if move is None:
            return None
        classification = move.result.classification
        if classification is Classification.INCONSISTENT:
            return VerdictOutcome.INCONSISTENT
        outcome = engine.submit_proved_verdict(move.cell, move.status, classification.value)
        if outcome is VerdictOutcome.ACCEPTED:
            after = engine.public_state()
            revealed = next(item for item in after.characters if item.cell == move.cell)
            assumption_result = (
                move.result.innocent_assumption_result
                if move.status is Status.CRIMINAL
                else move.result.criminal_assumption_result
            )
            results = _solver_results(move.result)
            self.metrics.deduction_steps += 1
            self.trace.append(TraceEntry(
                step=self.metrics.deduction_steps,
                active_clue_ids=tuple(clue_id for clue_id, _ in before.active_clues),
                target=move.cell,
                assumption_tested=(
                    f"{move.cell}=INNOCENT" if move.status is Status.CRIMINAL
                    else f"{move.cell}=CRIMINAL"
                ),
                assumption_result="UNSAT" if assumption_result and not assumption_result.satisfiable else "SAT",
                verdict=move.status.value,
                newly_revealed_clue=f"CLUE_{revealed.cell}",
                sat_calls=len(results),
                decisions=sum(item.decisions for item in results),
                propagations=sum(item.propagations for item in results),
                backtracks=sum(item.backtracks for item in results),
                runtime_seconds=sum(item.runtime_seconds for item in results),
            ))
        return outcome

    def auto_solve(self, engine: GameEngine) -> AgentTerminal:
        while not engine.solved:
            outcome = self.apply_next(engine)
            if outcome is VerdictOutcome.INCONSISTENT:
                return AgentTerminal.INCONSISTENT
            if outcome is None:
                return AgentTerminal.STALLED
            if outcome is not VerdictOutcome.ACCEPTED:
                return AgentTerminal.STALLED
        return AgentTerminal.SOLVED

    def trace_text(self) -> str:
        blocks = []
        for item in self.trace:
            blocks.append(
                f"Step {item.step}\nActive clues: {', '.join(item.active_clue_ids)}\n"
                f"Target: {item.target}\nTest: KB AND {item.assumption_tested}\n"
                f"Result: {item.assumption_result}\nTherefore: {item.target} = {item.verdict}\n"
                f"New clue revealed: {item.newly_revealed_clue}"
            )
        return "\n\n".join(blocks)

    def export_trace_json(self, path: str | Path) -> None:
        with Path(path).open("w", encoding="utf-8") as handle:
            json.dump([asdict(item) for item in self.trace], handle, indent=2)

