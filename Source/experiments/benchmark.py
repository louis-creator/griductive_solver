"""Run the fixed normal collection and export actual solver measurements."""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from time import perf_counter

from game.engine import GameEngine
from game.loader import load_puzzle
from logic.agent import LogicAgent
from logic.cnf import CNFEncoder

ROOT = Path(__file__).resolve().parents[1]
RESULTS = Path(__file__).resolve().parent / "results"
REPORT = Path(__file__).resolve().parent / "report_material"


def run_case(path: Path) -> tuple[dict, LogicAgent]:
    puzzle = load_puzzle(path)
    full_formula = CNFEncoder(puzzle.size).encode_complete_puzzle(puzzle)
    engine, agent = GameEngine(puzzle), LogicAgent()
    started = perf_counter()
    terminal = agent.auto_solve(engine)
    elapsed = perf_counter() - started
    row = {
        "puzzle_id": puzzle.id,
        "grid_size": puzzle.size,
        "primary_variables": full_formula.primary_count,
        "auxiliary_variables": full_formula.auxiliary_count,
        "cnf_clauses": full_formula.clause_count,
        "sat_calls": agent.metrics.sat_calls,
        "decisions": agent.metrics.decisions,
        "propagations": agent.metrics.propagations,
        "backtracks": agent.metrics.backtracks,
        "deduction_steps": agent.metrics.deduction_steps,
        "solver_runtime_seconds": round(agent.metrics.runtime_seconds, 9),
        "total_runtime_seconds": round(elapsed, 9),
        "final_status": terminal.value,
    }
    return row, agent


def main() -> int:
    RESULTS.mkdir(parents=True, exist_ok=True)
    REPORT.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    clue_coverage: Counter[str] = Counter()
    representative: LogicAgent | None = None
    showcase: LogicAgent | None = None
    for path in sorted((ROOT / "puzzles" / "normal").glob("*.json")):
        row, agent = run_case(path)
        puzzle = load_puzzle(path)
        clue_coverage.update(character.clue.type.value for character in puzzle.characters)
        rows.append(row)
        if representative is None or row["puzzle_id"] == "3x3_mixed_01":
            representative = agent
        if row["puzzle_id"] == "3x3_dpll_showcase_01":
            showcase = agent
        print(
            f"{row['puzzle_id']}: {row['final_status']} steps={row['deduction_steps']} "
            f"SAT calls={row['sat_calls']} runtime={row['total_runtime_seconds']:.6f}s"
        )
    csv_path, json_path = RESULTS / "results.csv", RESULTS / "results.json"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    with (REPORT / "benchmark_results.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    json_text = json.dumps(rows, indent=2) + "\n"
    json_path.write_text(json_text, encoding="utf-8")
    (REPORT / "benchmark_results.json").write_text(json_text, encoding="utf-8")
    (REPORT / "representative_trace.txt").write_text(
        representative.trace_text() + "\n" if representative else "No trace generated.\n",
        encoding="utf-8",
    )
    (REPORT / "dpll_showcase_trace.txt").write_text(
        showcase.trace_text() + "\n" if showcase else "No showcase trace generated.\n",
        encoding="utf-8",
    )
    summary = {
        "puzzles": len(rows),
        "all_solved": all(row["final_status"] == "SOLVED" for row in rows),
        "sizes": sorted({row["grid_size"] for row in rows}),
        "total_sat_calls": sum(row["sat_calls"] for row in rows),
        "total_deduction_steps": sum(row["deduction_steps"] for row in rows),
    }
    (REPORT / "puzzle_statistics.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    (REPORT / "clue_coverage.json").write_text(
        json.dumps(dict(sorted(clue_coverage.items())), indent=2) + "\n", encoding="utf-8"
    )
    return 0 if summary["all_solved"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
