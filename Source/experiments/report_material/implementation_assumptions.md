# Implementation assumptions

- Initially face-up cards expose both status and clue.
- Direct combinatorial cardinality and parity encodings are used because required boards are small.
- The supplied collection targets 3x3 and 4x4; the loader accepts sizes 1 through 26.
- Display names and professions are metadata unless future clue templates explicitly reference them.

# Known limitations

- Direct parity CNF grows exponentially with region size; it is suitable for the supplied small cases.
- The desktop GUI requires a graphical display and a Python build with tkinter.

