from __future__ import annotations

from dataclasses import fields

from conftest import base_raw
from game.engine import GameEngine, VerdictOutcome
from game.loader import parse_puzzle
from game.models import Clue, ClueType, Status
from game.public_state import PublicCharacter, PublicGameState
from logic.agent import AgentTerminal, LogicAgent
from logic.entailment import Classification, EntailmentChecker


def _state(clues=(), statuses=(), unresolved=("A1", "B1")):
    characters = []
    for cell in ("A1", "B1", "A2", "B2"):
        status = dict(statuses).get(cell)
        clue = dict(clues).get(cell)
        revealed = status is not None or clue is not None
        characters.append(PublicCharacter(cell, cell, "Test", revealed, status, clue))
    # Explicit unresolved lets inconsistency tests retain a target.
    characters = [
        PublicCharacter(c.cell, c.name, c.profession, c.cell not in unresolved, c.proved_status, c.revealed_clue)
        if c.cell in unresolved else c
        for c in characters
    ]
    return PublicGameState("x", "x", 2, tuple(characters))


def test_entailment_four_classifications():
    checker = EntailmentChecker()
    criminal = _state(clues=(("A2", Clue(ClueType.FACT, target="A1", status=Status.CRIMINAL)),))
    innocent = _state(clues=(("A2", Clue(ClueType.FACT, target="A1", status=Status.INNOCENT)),))
    unknown = _state()
    inconsistent = _state(clues=(
        ("A2", Clue(ClueType.FACT, target="A1", status=Status.CRIMINAL)),
        ("B2", Clue(ClueType.FACT, target="A1", status=Status.INNOCENT)),
    ))
    assert checker.classify(criminal, "A1").classification is Classification.CRIMINAL
    assert checker.classify(innocent, "A1").classification is Classification.INNOCENT
    assert checker.classify(unknown, "A1").classification is Classification.UNKNOWN
    assert checker.classify(inconsistent, "A1").classification is Classification.INCONSISTENT


def test_public_state_has_no_hidden_fields_or_unrevealed_clues():
    engine = GameEngine(parse_puzzle(base_raw()))
    state = engine.public_state()
    names = {field.name for field in fields(state.characters[0])}
    assert "status" not in names and "clue" not in names
    hidden = next(character for character in state.characters if character.cell == "B1")
    assert hidden.proved_status is None and hidden.revealed_clue is None


def test_engine_outcomes_and_rejected_state_unchanged():
    engine = GameEngine(parse_puzzle(base_raw()))
    before = engine.public_state()
    assert engine.submit_proved_verdict("B1", Status.INNOCENT, "UNKNOWN") is VerdictOutcome.NOT_PROVABLE
    assert engine.public_state() == before
    assert engine.submit_proved_verdict("B1", Status.CRIMINAL, "INNOCENT") is VerdictOutcome.CONTRADICTED
    assert engine.public_state() == before
    assert engine.submit_proved_verdict("B1", Status.INNOCENT, "INNOCENT") is VerdictOutcome.ACCEPTED
    revealed = next(item for item in engine.public_state().characters if item.cell == "B1")
    assert revealed.revealed and revealed.revealed_clue is not None
    assert engine.restart() == before


def test_agent_progressive_solve_deterministic_and_trace():
    raw = base_raw()
    raw["characters"][0]["clue"] = {"type": "FACT", "target": "B1", "status": "INNOCENT"}
    raw["characters"][1]["clue"] = {"type": "FACT", "target": "A2", "status": "CRIMINAL"}
    raw["characters"][2]["clue"] = {"type": "FACT", "target": "B2", "status": "INNOCENT"}
    engine = GameEngine(parse_puzzle(raw))
    agent = LogicAgent()
    hint = agent.hint(engine.public_state())
    assert hint and hint.cell == "B1" and hint.status is Status.INNOCENT
    agent.reset()
    assert agent.auto_solve(engine) is AgentTerminal.SOLVED
    assert [entry.target for entry in agent.trace] == ["B1", "A2", "B2"]
    assert all(entry.assumption_result == "UNSAT" for entry in agent.trace)
    assert "Step 1" in agent.trace_text()


def test_agent_stalls_without_guessing():
    raw = base_raw()
    raw["characters"][0]["clue"] = {"type": "SAME", "target": "A2", "other": "B2"}
    engine = GameEngine(parse_puzzle(raw))
    before = engine.public_state()
    assert LogicAgent().auto_solve(engine) is AgentTerminal.STALLED
    assert engine.public_state() == before

