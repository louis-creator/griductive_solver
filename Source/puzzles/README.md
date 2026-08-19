# Puzzle JSON schema

Each file has `id`, `title`, integer `size`, exactly `size * size` characters, and a list of
`initially_revealed` cells. A character has `cell`, `name`, `profession`, hidden `status`, and one
structured `clue`.

Core clue shapes:

- `{"type":"FACT","target":"A1","status":"CRIMINAL"}`
- `{"type":"SAME","target":"A1","other":"B1"}` (or `DIFFERENT`)
- `{"type":"EXACTLY","k":1,"region":{...}}` (also `AT_LEAST`, `AT_MOST`)
- `{"type":"PARITY","parity":"ODD","region":{...}}`

Regions are `ROW` (`row`), `COLUMN` (`column`), `NEIGHBORS` (`cell`), `EXPLICIT` (`cells`),
`BOUNDARY`, `CORNERS`, `INTERSECTION` (`regions`), or `COMMON_NEIGHBORS` (`cells`). The loader
rejects missing cells, bad coordinates, duplicates, invalid bounds, and malformed structures.

Files under `normal/` are gameplay/benchmark cases. Files under `fixtures/` deliberately test
inconsistency and non-uniqueness. Regenerate the fixed collection with:

```bash
python tools/generate_dataset.py
```

`normal/3x3_dpll_showcase_01.json` is intentionally constructed so the first satisfiable DPLL
query tries a failing `True` branch before backtracking. It provides a reproducible GUI demonstration
where both the Decisions and Backtracks metrics are non-zero while Auto Solve still never guesses.
