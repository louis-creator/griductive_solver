# Reproducible experiments

Run from `Source/` with the same Python used for the application:

```bash
python -m experiments.validate_puzzles
python -m experiments.benchmark
```

Validation loads every normal JSON file, independently checks that every clue is true under its
declared hidden assignment, checks full-clue uniqueness, and runs progressive Auto Solve.

The benchmark measures the fixed normal collection without the GUI. It exports `results/results.csv`
and `results/results.json`. Timings are machine-dependent; SAT calls, deduction steps, and CNF sizes
are deterministic. Auxiliary-variable count is zero because the correct direct combinatorial
encoding uses primary literals only for these small boards.

