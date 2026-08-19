# Griductive Solver — CSC14003 Project 2

Griductive is a no-guess deduction game played on a grid of character cards. Every character is
secretly either **Criminal** or **Innocent**, and every revealed clue is true. A verdict is accepted
only when it follows logically from all currently public information.

This project provides a complete Python implementation with a responsive Tkinter interface,
structured JSON puzzles, an independent semantic evaluator, automatic CNF encoding, a
self-implemented DPLL SAT solver, a public-knowledge-only logic agent, Hint, Auto Solve, deduction
traces, uniqueness checking, automated tests, and reproducible benchmarks.

## Key features

- Responsive, card-first Tkinter interface with Windows HiDPI support.
- Manual Criminal/Innocent verdicts with four explicit outcomes.
- Fixed puzzle navigation, JSON loading, Restart, Mark, Hint, and Auto Solve.
- Clue spotlighting with shared region semantics.
- Five visual pencil-mark colors that never enter the logical knowledge base.
- Two-stage Hint: a relevant public clue first, then a logically forced verdict.
- Progressive Auto Solve that reveals exactly one proved card at a time and never guesses.
- Deduction traces and solver metrics: SAT calls, decisions, propagations, backtracks, and runtime.
- Six required core clue types, parity constraints, and advanced region expressions.
- Six validated 3×3 puzzles, four validated 4×4 puzzles, and two deliberate test fixtures.
- Every normal puzzle is schema-valid, unique, and progressively solvable without guessing.

## System requirements

- Python 3.11 or newer.
- Tkinter:
  - Included with standard Python installations on Windows and macOS.
  - Some Linux distributions require the separate `python3-tk` package.
- No third-party package is required to run the application.
- `pytest` is included in `requirements.txt` for running the test suite.

## Installation

From the project root:

```powershell
cd Source
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

On macOS or Linux, activate the environment with:

```bash
source .venv/bin/activate
```

## Running the application

Start the default puzzle:

```powershell
python main.py
```

Start a specific puzzle:

```powershell
python main.py puzzles/normal/4x4_mixed_01.json
```

Main interface controls:

- **Next Fixed Case** cycles through the validated built-in JSON collection.
- **Load JSON** validates and loads another puzzle file.
- **How to play** opens the in-application tutorial.
- **Clues**, **Trace**, and **Metrics** provide public logical information.
- **Restart** restores the exact initial state and clears marks, trace, timer, and metrics.

The interface fits its initial size to the detected screen. On narrower windows, the optional
instruction panel collapses automatically so that the board retains enough space. Card typography
uses Windows DPI awareness, installed-font fallbacks, and readable minimum font sizes.

## Manual gameplay

1. Select a face-down character card.
2. Read the currently revealed clues.
3. Choose **INNOCENT** or **CRIMINAL** only when the public clues prove that verdict.
4. An accepted verdict flips the card and reveals its always-true clue.
5. Continue until every character has been identified.

| Outcome | Meaning | State change |
|---|---|---|
| `ACCEPTED` | The requested verdict is logically entailed | Reveal the status and clue |
| `NOT_PROVABLE` | Both statuses remain possible | No change and no hidden information revealed |
| `CONTRADICTED` | The opposite verdict is logically entailed | No change and no hidden information revealed |
| `INCONSISTENT` | The public knowledge base has no satisfying model | Stop deduction |

### Clue spotlight

Select a revealed card or an entry in the **Clues** tab:

- Gold identifies the clue owner.
- Blue identifies every referenced or counted cell.
- Unrelated cards are visually dimmed.

The GUI uses the same `RegionResolver` as semantic evaluation and CNF encoding. Region behavior is
not duplicated in the interface.

### Pencil marks

Select an unresolved card and press **Mark** to cycle through five note colors. These colors are
purely visual. They are never stored in `PublicGameState` and are never used by CNF, Hint, or
Auto Solve.

### Hint

Hint has two stages:

1. The first press spotlights a revealed clue related to the next forced character.
2. The next press identifies the forced verdict and explains that the opposite assumption is UNSAT.

Hint receives only public information and cannot access hidden statuses or unrevealed clues.

### Auto Solve

Auto Solve repeats the following process:

1. Build CNF from revealed clues and proved verdicts.
2. Inspect unresolved cells in deterministic row-major order.
3. Find a verdict that is logically forced through UNSAT refutation.
4. Send exactly one proved verdict to `GameEngine`.
5. Reveal the new clue only after the verdict is accepted.
6. Rebuild the public knowledge base and continue.

Auto Solve stops at `SOLVED`, `STALLED`, or `INCONSISTENT`. It never guesses.

## Decisions and backtracks showcase

The **DPLL Backtracking Lab** puzzle is designed to exercise non-zero `Decisions` and `Backtracks`
metrics:

```powershell
python main.py puzzles/normal/3x3_dpll_showcase_01.json
```

Press **Auto Solve**, then open the **Metrics** tab. The reproducible result is:

```text
Puzzle: 3x3_dpll_showcase_01
Final status: SOLVED
Deduction steps: 7
SAT calls: 21
Decisions: 1
Propagations: 129
Backtracks: 1
```

Its initially revealed constraints include:

```text
SAME(B1, C1)
AT_MOST(1, {B1, C1})
```

Together, they force `B1 = C1 = INNOCENT`. DPLL deterministically tries `B1 = True` first, reaches a
conflict, backtracks, and then finds the satisfying `False` branch. These values are generated by the
actual solver; they are not predefined metrics.

## Architecture and information isolation

```text
Complete Puzzle
    |
    v
GameEngine  [hidden statuses + unrevealed clues]
    |
    | immutable public snapshot
    v
PublicGameState  [metadata + proved statuses + revealed clues]
    |
    v
LogicAgent -> CNFEncoder -> DPLLSolver -> EntailmentChecker
    |
    | proved verdict only
    v
GameEngine -> ACCEPTED -> reveal status/clue -> next PublicGameState
```

The critical isolation rules are:

- `GameEngine` is the only component that owns the complete puzzle and hidden solution.
- `LogicAgent` receives only immutable `PublicGameState` snapshots.
- An unrevealed public character contains neither its status nor its clue.
- Hint and Auto Solve use the same public reasoning mechanism.
- A rejected verdict leaves the game state unchanged.

At deduction step `t`, the knowledge base is exactly:

```text
KB_t = CNF(revealed clues) AND unit clauses(proved verdicts)
```

Hidden statuses and unrevealed clues are never included in `KB_t`.

## Clue language

### Required core clues

| Clue | Logical meaning |
|---|---|
| `FACT` | A named character has a stated status |
| `SAME` | Two characters have the same status |
| `DIFFERENT` | Two characters have different statuses |
| `EXACTLY(k, R)` | Exactly `k` Criminals are in region `R` |
| `AT_LEAST(k, R)` | At least `k` Criminals are in region `R` |
| `AT_MOST(k, R)` | At most `k` Criminals are in region `R` |

### Extensions

- `PARITY`: the number of Criminals in a region is `EVEN` or `ODD`.
- Advanced regions:
  - `INTERSECTION`
  - `BOUNDARY`
  - `CORNERS`
  - `COMMON_NEIGHBORS`

### Required regions

| Region | Meaning |
|---|---|
| `ROW` | Every cell in one row |
| `COLUMN` | Every cell in one column |
| `NEIGHBORS` | Up to eight horizontally, vertically, or diagonally touching cells; excludes the center |
| `EXPLICIT` | A list of valid, distinct cell coordinates |

`RegionResolver` is the single source of truth for region membership and is shared by direct
semantics, CNF encoding, and GUI highlighting.

## Direct semantic evaluator

`logic.semantics.evaluate_clue` evaluates a structured clue directly under a complete primary
assignment. It does not call the CNF encoder or SAT solver.

This evaluator acts as an independent oracle in exhaustive tests: for every small assignment, the
direct semantic result must match CNF satisfiability under the same fixed primary values.

## Automatic CNF encoding

`logic.cnf.CNFEncoder`:

- Creates deterministic row-major primary-variable mappings.
- Keeps primary and auxiliary variables separate.
- Converts structured clues to CNF automatically.
- Uses reusable combinatorial cardinality and parity encodings.
- Adds proved verdicts as unit clauses.
- Exposes primary-variable, auxiliary-variable, total-variable, and clause counts.

There are no puzzle-specific hard-coded CNF formulas. The current small-board combinatorial encoding
uses no auxiliary variables, so the dataset has an auxiliary-variable count of `0`.

## DPLL SAT solver

`logic.dpll.DPLLSolver` is implemented locally and does not use Z3, PySAT, pycosat, Minisat, or any
other external SAT solver.

Implemented behavior includes:

- Partial assignments.
- Clause evaluation and conflict detection.
- Cascading unit propagation.
- Deterministic smallest-variable selection.
- Recursive branching and backtracking.
- Temporary assumptions.
- SAT with a complete assignment or UNSAT.
- Decisions, propagations, backtracks, and runtime statistics.

The automated tests cross-check DPLL against brute-force truth tables on 250 small random CNF
formulas.

## Logical consequence by refutation

A satisfying model is only one possible world and cannot be used directly as a verdict. The agent
uses refutation:

```text
KB |= Criminal(C) iff KB AND NOT Criminal(C) is UNSAT
KB |= Innocent(C) iff KB AND Criminal(C) is UNSAT
```

Classification results:

- `CRIMINAL`: assuming Innocent is UNSAT.
- `INNOCENT`: assuming Criminal is UNSAT.
- `UNKNOWN`: both assumptions are SAT.
- `INCONSISTENT`: the base knowledge itself is UNSAT.

## Uniqueness checking

Puzzle uniqueness is checked independently using the complete clue set:

1. Solve the full CNF and obtain the first model.
2. Add a blocking clause that excludes exactly that primary assignment.
3. Solve again.
4. If the second solve is UNSAT, the puzzle is `UNIQUE`; otherwise it is `NON_UNIQUE`.

The blocking clause contains primary variables only, so differences in auxiliary values cannot
produce false non-uniqueness.

## Puzzle JSON format

Minimal example:

```json
{
  "id": "example_3x3",
  "title": "Example Case",
  "size": 3,
  "characters": [
    {
      "cell": "A1",
      "name": "Avery",
      "profession": "Architect",
      "status": "CRIMINAL",
      "clue": {
        "type": "EXACTLY",
        "k": 1,
        "region": {"type": "ROW", "row": 1}
      }
    }
  ],
  "initially_revealed": ["A1"]
}
```

A real puzzle must contain exactly `size × size` character entries. The loader rejects:

- Malformed JSON.
- Missing characters or duplicate cells.
- Coordinates outside the board.
- Invalid statuses, clue types, or region types.
- Counting values where `k < 0` or `k > |R|`.
- Duplicate cells in explicit regions.
- Invalid initial reveals.

See [`puzzles/README.md`](puzzles/README.md) for the complete schema guide.

## Puzzle collection

### Normal 3×3 puzzles

- `3x3_binary_01`
- `3x3_counting_01`
- `3x3_dpll_showcase_01`
- `3x3_easy_01`
- `3x3_extensions_01`
- `3x3_mixed_01`

### Normal 4×4 puzzles

- `4x4_counting_01`
- `4x4_easy_01`
- `4x4_medium_01`
- `4x4_mixed_01`

### Deliberate fixtures

- `fixture_inconsistent`: the complete clue set has no model.
- `fixture_non_unique`: the complete clue set has multiple models.

Regenerate the deterministic collection with:

```powershell
python tools/generate_dataset.py
```

## Running the tests

From `Source/`:

```powershell
python -m pytest -q
```

Latest verified result:

```text
56 passed in 0.31s
```

The suite covers:

- Coordinates and all region types.
- Puzzle loading and malformed inputs.
- Direct clue semantics.
- Exhaustive semantic/CNF equivalence.
- DPLL propagation, branching, backtracking, SAT, UNSAT, and random brute-force comparison.
- Criminal, Innocent, Unknown, and Inconsistent entailment classifications.
- Engine verdict transitions and rejected-action state invariance.
- Public-state information isolation.
- Hint, Auto Solve, progressive reveal, deterministic ordering, and no-guess behavior.
- Unique, non-unique, and inconsistent puzzle detection.
- Every normal dataset puzzle.
- GUI formatting, screen fitting, and responsive layout calculations.
- A regression requiring non-zero decisions and backtracks in the DPLL showcase puzzle.

## Validating the puzzle collection

```powershell
python -m experiments.validate_puzzles
```

Current result:

```text
10/10 normal puzzles:
- schema valid
- every clue true under the declared assignment
- UNIQUE
- Auto Solve SOLVED
```

The validator also displays each puzzle's clue coverage and deduction-step count.

## Running benchmarks

```powershell
python -m experiments.benchmark
```

Each benchmark row contains:

- Puzzle ID and grid size.
- Primary and auxiliary variable counts.
- CNF clause count.
- SAT calls.
- Decisions, propagations, and backtracks.
- Deduction steps.
- Solver and total runtime.
- Final status.

Generated benchmark files:

```text
experiments/results/results.csv
experiments/results/results.json
```

All 10 normal puzzles currently finish with `SOLVED`.

## Project structure

```text
Source/
├── main.py
├── README.md
├── requirements.txt
├── pyproject.toml
├── game/
│   ├── engine.py
│   ├── loader.py
│   ├── models.py
│   ├── public_state.py
│   └── regions.py
├── logic/
│   ├── agent.py
│   ├── cardinality.py
│   ├── cnf.py
│   ├── dpll.py
│   ├── entailment.py
│   ├── semantics.py
│   └── uniqueness.py
├── gui/
│   └── app.py
├── puzzles/
│   ├── normal/
│   └── fixtures/
├── experiments/
│   ├── benchmark.py
│   ├── validate_puzzles.py
│   └── results/
├── tests/
└── tools/
    └── generate_dataset.py
```

## Known limitations

- Direct parity CNF grows exponentially with region size. It is correct and practical for the
  supplied 3×3 and 4×4 puzzles, but a sequential XOR encoding would scale better to larger boards.
- The GUI requires a graphical desktop and Tkinter. Domain tests, validation, and benchmarks can run
  headlessly.
- Coordinates intentionally support single-letter columns from `A` through `Z`.

## Quick command reference

From the project root:

```powershell
cd Source
python main.py
python -m pytest -q
python -m experiments.validate_puzzles
python -m experiments.benchmark
```
