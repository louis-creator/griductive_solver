from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def base_raw() -> dict:
    cells = ["A1", "B1", "A2", "B2"]
    statuses = ["CRIMINAL", "INNOCENT", "CRIMINAL", "INNOCENT"]
    return {
        "id": "sample",
        "title": "Sample",
        "size": 2,
        "characters": [
            {
                "cell": cell,
                "name": f"Person {cell}",
                "profession": "Tester",
                "status": status,
                "clue": {"type": "FACT", "target": cell, "status": status},
            }
            for cell, status in zip(cells, statuses)
        ],
        "initially_revealed": ["A1"],
    }

