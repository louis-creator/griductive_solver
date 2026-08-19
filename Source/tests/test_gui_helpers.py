from __future__ import annotations

from game.models import Clue, ClueType, Region, RegionType, Status
from gui.app import (
    fit_window_to_screen,
    format_clue,
    format_region,
    show_instruction_sidebar,
)


def test_gui_clue_formatting_and_shared_region_language():
    assert format_clue(Clue(ClueType.FACT, target="A1", status=Status.INNOCENT)) == "A1 is not Criminal."
    region = Region(RegionType.INTERSECTION, regions=(
        Region(RegionType.ROW, row=1), Region(RegionType.BOUNDARY)
    ))
    assert "intersection" in format_region(region)
    assert "Exactly 1" in format_clue(Clue(ClueType.EXACTLY, k=1, region=region))


def test_window_geometry_never_exceeds_common_screen_sizes():
    for screen_width, screen_height in ((1920, 1080), (1366, 768), (1280, 800), (1024, 768), (800, 600)):
        width, height, x, y, minimum_width, minimum_height = fit_window_to_screen(
            screen_width, screen_height
        )
        assert 0 < minimum_width <= width <= screen_width
        assert 0 < minimum_height <= height <= screen_height
        assert x >= 0 and y >= 0
        assert x + width <= screen_width and y + height <= screen_height


def test_instruction_sidebar_collapses_before_board_becomes_cramped():
    assert not show_instruction_sidebar(1099)
    assert show_instruction_sidebar(1100)
