"""Griductive desktop application entry point."""

from __future__ import annotations

import argparse
from pathlib import Path

from gui.app import run


def main() -> None:
    parser = argparse.ArgumentParser(description="Play Griductive with a no-guess SAT agent")
    parser.add_argument(
        "puzzle",
        nargs="?",
        type=Path,
        default=Path(__file__).resolve().parent / "puzzles" / "normal" / "3x3_easy_01.json",
        help="path to a puzzle JSON file",
    )
    args = parser.parse_args()
    run(args.puzzle)


if __name__ == "__main__":
    main()

