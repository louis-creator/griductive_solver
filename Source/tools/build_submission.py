"""Build a clean source-only archive without inventing student identifiers."""

from __future__ import annotations

import argparse
import re
import zipfile
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1]
DIST = SOURCE / "dist"
EXCLUDED_PARTS = {"__pycache__", ".pytest_cache", ".venv", "dist"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Package Griductive source for submission")
    parser.add_argument("team_folder", help="real underscore-separated student IDs")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9]+(?:_[A-Za-z0-9]+)+", args.team_folder):
        parser.error("team_folder must contain at least two underscore-separated alphanumeric IDs")
    DIST.mkdir(exist_ok=True)
    archive = DIST / f"{args.team_folder}.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as output:
        for path in sorted(SOURCE.rglob("*")):
            relative = path.relative_to(SOURCE)
            if path.is_dir() or EXCLUDED_PARTS.intersection(relative.parts) or path.name == "Report.pdf":
                continue
            arcname = Path(args.team_folder) / "Source" / relative
            output.write(path, arcname)
    print(archive)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

