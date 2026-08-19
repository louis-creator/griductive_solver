# Architecture evidence

- `game.loader` validates structured JSON into immutable puzzle models.
- `game.engine.GameEngine` alone owns hidden status and unrevealed clues.
- `game.public_state.PublicGameState` exposes immutable public metadata, proved statuses, and only
  revealed clues.
- `logic.semantics` is an independent direct oracle.
- `logic.cnf` automatically encodes public clues and known verdict unit clauses.
- `logic.dpll` is a self-contained deterministic SAT solver.
- `logic.entailment` classifies through UNSAT refutation.
- `logic.agent` progressively requests one row-major forced verdict and records a trace.
- `logic.uniqueness` blocks only the first model's primary assignment.
- `gui.app` renders a responsive card-first board, fixed-case navigation, pencil marks, staged Hint,
  spotlighting, timer, metrics, and trace while delegating all reasoning to these APIs. GUI-only
  marks and selection state never enter `PublicGameState` or CNF.
