# Software requirement audit

| Requirement | Status | Evidence |
|---|---|---|
| Python application and playable GUI | PASS | `main.py`, responsive card-first `gui/app.py`; 3x3/4x4 GUI smoke workflows |
| Grid, coordinates, names, professions, face states | PASS | `GriductiveApp.render`; `tests/test_regions_loader.py` |
| Manual verdict protocol and unchanged rejection | PASS | `GameEngine.submit_proved_verdict`; engine and GUI workflow tests |
| Six core clues | PASS | `game.models.ClueType`, `logic.semantics`, `logic.cnf`; exhaustive tests |
| Required regions | PASS | `game.regions.resolve_region`; row/column/neighbor/explicit tests |
| Two or more extensions | PASS | PARITY plus INTERSECTION/BOUNDARY/CORNERS/COMMON_NEIGHBORS and tests |
| Strong structured puzzle loading | PASS | `game.loader`; valid and malformed test cases |
| Independent direct semantics | PASS | `logic.semantics.evaluate_clue`; no CNF/SAT imports |
| Automatic CNF and deterministic map | PASS | `logic.cnf`; exhaustive semantic equivalence tests |
| Variable/clause statistics | PASS | `CNFFormula` properties; GUI and benchmark output |
| Self-implemented deterministic DPLL | PASS | `logic.dpll`; fixed and 250 randomized brute-force comparisons |
| Entailment by UNSAT refutation | PASS | `logic.entailment`; four classification tests |
| Engine/agent information isolation | PASS | immutable `PublicGameState`; security regression tests |
| Hint and progressive Auto Solve without guessing | PASS | two-stage public Hint in `gui.app`, `logic.agent`; progressive/stalled tests and all normal puzzles |
| Deduction trace | PASS | `TraceEntry`, text/JSON export; benchmark representative trace |
| Primary-only uniqueness checker | PASS | `logic.uniqueness`; unique/non-unique/inconsistent tests |
| Several 3x3 and 4x4 puzzles | PASS | 5 normal 3x3 and 4 normal 4x4 JSON files |
| Puzzle validation and experiments | PASS | `experiments.validate_puzzles`, `experiments.benchmark` |
| README and reproducible commands | PASS | `README.md`, `experiments/README.md`, `puzzles/README.md` |

No mandatory software requirement in the official PDF is currently known to be FAIL or PARTIAL.
The separately graded academic report and demonstration video are intentionally outside this source
implementation and remain team responsibilities.
