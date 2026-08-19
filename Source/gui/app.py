"""A polished, card-first Tkinter interface around the public SAT APIs.

The visual design is deliberately independent from the reasoning layer.  Pencil marks,
selection, spotlighting, timers, and tutorial state never enter the knowledge base.
"""

from __future__ import annotations

import ctypes
from pathlib import Path
import sys
from time import monotonic
import tkinter as tk
import tkinter.font as tkfont
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

from game.engine import GameEngine, VerdictOutcome
from game.loader import PuzzleValidationError, load_puzzle
from game.models import Clue, ClueType, RegionType, Status
from game.public_state import PublicCharacter, PublicGameState
from logic.agent import ForcedMove, LogicAgent
from logic.cnf import CNFEncoder
from logic.entailment import Classification
from logic.semantics import referenced_cells


def fit_window_to_screen(screen_width: int, screen_height: int) -> tuple[int, int, int, int, int, int]:
    """Return a centered geometry and safe minimum size that fit inside the screen."""
    available_width = max(640, screen_width - 80)
    available_height = max(500, screen_height - 110)
    width = min(1280, available_width)
    height = min(800, available_height)
    x = max(0, (screen_width - width) // 2)
    y = max(0, (screen_height - height) // 3)
    return width, height, x, y, min(960, width), min(620, height)


def show_instruction_sidebar(body_width: int) -> bool:
    """Reserve the optional instruction panel only when the board remains comfortable."""
    return body_width >= 1100


def enable_windows_dpi_awareness() -> None:
    """Prevent Windows display scaling from bitmap-blurring Tk text."""
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError):
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            pass


def configure_tk_scaling(root: tk.Misc) -> float:
    """Match Tk point sizes to the display's physical DPI and return the scale."""
    scale = max(1.0, float(root.winfo_fpixels("1i")) / 72.0)
    root.tk.call("tk", "scaling", scale)
    return scale


def format_region(region) -> str:
    """Return a concise, GUI-friendly rendering of a structured region."""
    if region.type is RegionType.ROW:
        return f"row {region.row}"
    if region.type is RegionType.COLUMN:
        return f"column {region.column}"
    if region.type is RegionType.NEIGHBORS:
        return f"neighbors of {region.cell}"
    if region.type is RegionType.EXPLICIT:
        return ", ".join(region.cells)
    if region.type is RegionType.INTERSECTION:
        return "intersection of " + " and ".join(format_region(child) for child in region.regions)
    if region.type is RegionType.COMMON_NEIGHBORS:
        return f"common neighbors of {', '.join(region.cells)}"
    return region.type.value.lower()


def format_clue(clue: Clue) -> str:
    """Render every supported structured clue without natural-language parsing."""
    if clue.type is ClueType.FACT:
        prefix = "" if clue.status is Status.CRIMINAL else "not "
        return f"{clue.target} is {prefix}Criminal."
    if clue.type is ClueType.SAME:
        return f"{clue.target} and {clue.other} have the same status."
    if clue.type is ClueType.DIFFERENT:
        return f"{clue.target} and {clue.other} have different statuses."
    region = format_region(clue.region)
    if clue.type is ClueType.EXACTLY:
        return f"Exactly {clue.k} Criminal(s) in {region}."
    if clue.type is ClueType.AT_LEAST:
        return f"At least {clue.k} Criminal(s) in {region}."
    if clue.type is ClueType.AT_MOST:
        return f"At most {clue.k} Criminal(s) in {region}."
    return f"An {clue.parity.lower()} number of Criminals in {region}."


class GriductiveApp(ttk.Frame):
    """Warm mystery-board UI that delegates every logical decision to ``LogicAgent``."""

    PAPER = "#f2eadf"
    PAPER_LIGHT = "#fffaf2"
    INK = "#28221f"
    MUTED = "#756b63"
    LINE = "#423730"
    CORAL = "#ef887b"
    CORAL_DARK = "#a94440"
    SAGE = "#dcebd9"
    GREEN = "#28754a"
    RED = "#bd3e39"
    GOLD = "#d59b23"
    BLUE = "#3889bc"
    PURPLE = "#8151a6"
    FACE_DOWN = "#e5edf2"
    DIM = "#ddd6cd"
    MARK_COLORS = (None, "#f7d0cb", "#d7ead8", "#d4e8f4", "#eadcf0", "#f4e4b8")
    AVATAR_COLORS = ("#d98373", "#6e99a8", "#9b83a6", "#7b9b73", "#d39a58")

    def __init__(self, master: tk.Misc, puzzle_path: str | Path):
        super().__init__(master)
        self.display_scale = configure_tk_scaling(master)
        self.master.title("Griductive - The No-Guess Mystery")
        self.master.configure(bg=self.PAPER)
        screen_width = self.master.winfo_screenwidth()
        screen_height = self.master.winfo_screenheight()
        window_width, window_height, x, y, minimum_width, minimum_height = fit_window_to_screen(
            screen_width, screen_height
        )
        self.master.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.master.minsize(minimum_width, minimum_height)
        self._resolve_fonts()

        self.current_path = Path(puzzle_path).resolve()
        self.engine = GameEngine(load_puzzle(self.current_path))
        self.agent = LogicAgent()
        self.selected_cell: str | None = None
        self.spotlight_owner: str | None = None
        self.highlighted: set[str] = set()
        self.marks: dict[str, int] = {}
        self.terminal = "PLAYING"
        self.auto_running = False
        self.started_at = monotonic()
        self.hint_stage = 0
        self.hint_move: ForcedMove | None = None
        self._resize_job: str | None = None
        self._last_board_size = (0, 0)
        self._info_visible = True
        self.card_buttons: dict[str, tk.Widget] = {}
        self.clue_rows: list[tuple[str, Clue]] = []

        self.status_var = tk.StringVar(
            value="Case opened. Every visible statement is true - prove before you call."
        )
        self.metrics_var = tk.StringVar()
        self.case_var = tk.StringVar()
        self.timer_var = tk.StringVar(value="00:00")
        self.progress_var = tk.StringVar()
        self.detail_title_var = tk.StringVar(value="Select a card")
        self.detail_var = tk.StringVar(value="Face-down cards hide status and clue.")

        self._configure_styles()
        self._build_shell()
        self.pack(fill="both", expand=True)
        self.render()
        self._tick_timer()

    # ---------- shell ----------

    def _resolve_fonts(self) -> None:
        """Select installed fonts and avoid missing-family/glyph layout surprises."""
        installed = {family.casefold(): family for family in tkfont.families(self.master)}

        def choose(*candidates: str) -> str:
            for candidate in candidates:
                if candidate.casefold() in installed:
                    return installed[candidate.casefold()]
            return tkfont.nametofont("TkDefaultFont").actual("family")

        self.ui_family = choose("Segoe UI", "Arial", "Liberation Sans")
        self.heading_family = choose("Georgia", "Times New Roman", "DejaVu Serif")
        self.mono_family = choose("Consolas", "Courier New", "DejaVu Sans Mono")

    def _font(self, role: str, size: int, weight: str = "normal") -> tuple[str, int, str]:
        family = {
            "ui": self.ui_family,
            "heading": self.heading_family,
            "mono": self.mono_family,
        }[role]
        return family, size, weight

    def _configure_styles(self) -> None:
        style = ttk.Style(self.master)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure("Mystery.TFrame", background=self.PAPER)
        style.configure("Paper.TFrame", background=self.PAPER_LIGHT)
        style.configure(
            "Mystery.TButton",
            background=self.PAPER_LIGHT,
            foreground=self.INK,
            bordercolor=self.LINE,
            font=self._font("ui", 9, "bold"),
            padding=(11, 7),
        )
        style.map("Mystery.TButton", background=[("active", "#eadfd2")])
        style.configure(
            "Primary.TButton",
            background=self.CORAL,
            foreground=self.INK,
            bordercolor=self.LINE,
            font=self._font("ui", 9, "bold"),
            padding=(12, 7),
        )
        style.map("Primary.TButton", background=[("active", "#f39b91")])

    def _build_shell(self) -> None:
        self.configure(style="Mystery.TFrame")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._build_topbar()
        body = tk.Frame(self, bg=self.PAPER)
        self.body = body
        body.grid(row=1, column=0, sticky="nsew", padx=14, pady=(9, 5))
        body.grid_columnconfigure(0, minsize=238, weight=0)
        body.grid_columnconfigure(1, weight=1)
        body.grid_columnconfigure(2, minsize=310, weight=0)
        body.grid_rowconfigure(0, weight=1)

        self.info_panel = tk.Frame(body, bg=self.PAPER, width=238, padx=12, pady=12)
        self.info_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.info_panel.pack_propagate(False)
        self.board_panel = tk.Frame(body, bg=self.PAPER)
        self.board_panel.grid(row=0, column=1, sticky="nsew")
        self.board_panel.bind("<Configure>", self._on_board_resize)
        self.logic_panel = tk.Frame(
            body,
            bg=self.PAPER_LIGHT,
            width=310,
            padx=14,
            pady=14,
            highlightbackground="#d6cabc",
            highlightthickness=1,
        )
        self.logic_panel.grid(row=0, column=2, sticky="nsew", padx=(10, 0))
        self.logic_panel.pack_propagate(False)
        body.bind("<Configure>", self._on_body_resize)

        self._build_info_panel()
        self._build_logic_panel()
        self._build_actionbar()

    def _build_topbar(self) -> None:
        top = tk.Frame(self, bg=self.PAPER_LIGHT, height=60, highlightbackground="#d6cabc", highlightthickness=1)
        top.grid(row=0, column=0, sticky="ew")
        top.pack_propagate(False)
        tk.Label(
            top,
            text="GRIDUCTIVE",
            bg=self.PAPER_LIGHT,
            fg=self.INK,
            font=self._font("heading", 18, "bold"),
        ).pack(side="left", padx=24)
        center = tk.Frame(top, bg=self.PAPER_LIGHT)
        center.pack(side="left", expand=True)
        tk.Label(
            center,
            textvariable=self.case_var,
            bg=self.PAPER_LIGHT,
            fg=self.MUTED,
            font=self._font("mono", 8, "bold"),
        ).pack(side="left", padx=8)
        ttk.Button(center, text="Next Fixed Case", command=self.next_case, style="Primary.TButton").pack(side="left", padx=4)
        ttk.Button(center, text="Load JSON", command=self.load, style="Mystery.TButton").pack(side="left", padx=4)
        right = tk.Frame(top, bg=self.PAPER_LIGHT)
        right.pack(side="right", padx=20)
        tk.Label(
            right,
            textvariable=self.timer_var,
            bg=self.PAPER_LIGHT,
            fg=self.INK,
            font=self._font("mono", 12, "bold"),
        ).pack(side="left", padx=10)
        ttk.Button(right, text="? How to play", command=self.show_tutorial, style="Mystery.TButton").pack(side="left")

    def _build_info_panel(self) -> None:
        tk.Label(self.info_panel, text="THE DAILY CASE", bg=self.PAPER, fg=self.MUTED, font=self._font("mono", 8, "bold")).pack(anchor="w")
        self.info_title_label = tk.Label(
            self.info_panel,
            text="Griductive",
            bg=self.PAPER,
            fg=self.INK,
            anchor="w",
            font=self._font("heading", 18, "bold"),
        )
        self.info_title_label.pack(fill="x", pady=(4, 0))
        self.info_intro_label = tk.Label(
            self.info_panel,
            text="A grid-deduction mystery.\nNo guesses. Only proof.",
            bg=self.PAPER,
            fg=self.INK,
            justify="left",
            anchor="w",
            wraplength=205,
            font=self._font("ui", 9),
        )
        self.info_intro_label.pack(fill="x", pady=(2, 14))
        tk.Frame(self.info_panel, bg="#cfc1b3", width=55, height=1).pack(anchor="w", pady=(0, 15))
        tk.Label(self.info_panel, text="HOW TO PLAY", bg=self.PAPER, fg=self.MUTED, font=self._font("mono", 8, "bold")).pack(anchor="w")
        rules = (
            "1. Select a face-down suspect.",
            "2. Call only a verdict the clues prove.",
            "3. Select a public clue to inspect its reach.",
            "4. Marks are visual notes only.",
            "5. Hint nudges first, then gives a verdict.",
        )
        for rule in rules:
            tk.Label(
                self.info_panel,
                text=rule,
                bg=self.PAPER,
                fg=self.INK,
                justify="left",
                anchor="w",
                wraplength=215,
                font=self._font("ui", 8),
                pady=4,
            ).pack(fill="x")
        self.case_badge = tk.Label(
            self.info_panel,
            bg="#eadfd2",
            fg=self.INK,
            padx=11,
            pady=10,
            justify="left",
            font=self._font("mono", 8, "bold"),
        )
        self.case_badge.pack(fill="x", pady=(18, 8))
        self.progress_canvas = tk.Canvas(self.info_panel, bg=self.PAPER, height=25, highlightthickness=0)
        self.progress_canvas.pack(fill="x")
        tk.Label(
            self.info_panel,
            textvariable=self.progress_var,
            bg=self.PAPER,
            fg=self.MUTED,
            justify="left",
            wraplength=215,
            font=self._font("ui", 8),
        ).pack(anchor="w", pady=(6, 0))

    def _build_logic_panel(self) -> None:
        self.logic_title_label = tk.Label(
            self.logic_panel,
            text="PUBLIC KNOWLEDGE",
            bg=self.PAPER_LIGHT,
            fg=self.INK,
            anchor="w",
            justify="left",
            wraplength=270,
            font=self._font("heading", 11, "bold"),
        )
        self.logic_title_label.pack(fill="x")
        tk.Label(
            self.logic_panel,
            textvariable=self.detail_title_var,
            bg=self.PAPER_LIGHT,
            fg=self.CORAL_DARK,
            font=self._font("ui", 9, "bold"),
            wraplength=276,
            justify="left",
        ).pack(anchor="w", pady=(8, 2))
        tk.Label(
            self.logic_panel,
            textvariable=self.detail_var,
            bg=self.PAPER_LIGHT,
            fg=self.MUTED,
            font=self._font("ui", 8),
            wraplength=276,
            justify="left",
            height=4,
            anchor="nw",
        ).pack(fill="x")
        ttk.Button(self.logic_panel, text="Clear spotlight", command=self.clear_spotlight, style="Mystery.TButton").pack(fill="x", pady=(3, 8))

        self.logic_tabs = ttk.Notebook(self.logic_panel)
        self.logic_tabs.pack(fill="both", expand=True, pady=(4, 0))
        clue_frame = tk.Frame(self.logic_tabs, bg=self.PAPER_LIGHT, padx=4, pady=4)
        trace_frame = tk.Frame(self.logic_tabs, bg=self.PAPER_LIGHT, padx=4, pady=4)
        metrics_frame = tk.Frame(self.logic_tabs, bg=self.PAPER_LIGHT, padx=8, pady=8)
        self.logic_tabs.add(clue_frame, text="Clues")
        self.logic_tabs.add(trace_frame, text="Trace")
        self.logic_tabs.add(metrics_frame, text="Metrics")
        self.clue_list = tk.Listbox(
            clue_frame,
            bg="#f8f1e8",
            fg=self.INK,
            selectbackground="#ead8c6",
            selectforeground=self.INK,
            relief="flat",
            highlightbackground="#d6cabc",
            highlightthickness=1,
            activestyle="none",
            font=self._font("ui", 8),
            exportselection=False,
        )
        clue_scroll = ttk.Scrollbar(clue_frame, orient="vertical", command=self.clue_list.yview)
        self.clue_list.configure(yscrollcommand=clue_scroll.set)
        self.clue_list.pack(side="left", fill="both", expand=True)
        clue_scroll.pack(side="right", fill="y")
        self.clue_list.bind("<<ListboxSelect>>", self.select_clue)
        tk.Label(
            metrics_frame,
            textvariable=self.metrics_var,
            bg=self.PAPER_LIGHT,
            fg=self.MUTED,
            font=self._font("mono", 8),
            justify="left",
        ).pack(anchor="nw", fill="both", expand=True)
        self.trace_text = ScrolledText(
            trace_frame,
            height=10,
            wrap="word",
            state="disabled",
            bg="#f8f1e8",
            fg=self.INK,
            relief="flat",
            font=self._font("mono", 8),
        )
        self.trace_text.pack(fill="both", expand=True)

    def _build_actionbar(self) -> None:
        bar = tk.Frame(self, bg=self.PAPER, pady=8)
        bar.grid(row=2, column=0, sticky="ew")
        self.action_bar = bar
        actions = tk.Frame(bar, bg=self.PAPER)
        actions.pack()
        ttk.Button(actions, text="INNOCENT", command=lambda: self.call(Status.INNOCENT), style="Mystery.TButton").pack(side="left", padx=4)
        ttk.Button(actions, text="CRIMINAL", command=lambda: self.call(Status.CRIMINAL), style="Mystery.TButton").pack(side="left", padx=4)
        ttk.Button(actions, text="Mark", command=self.mark_selected, style="Mystery.TButton").pack(side="left", padx=4)
        ttk.Button(actions, text="Hint", command=self.hint, style="Mystery.TButton").pack(side="left", padx=4)
        ttk.Button(actions, text="Auto Solve", command=self.auto_solve, style="Primary.TButton").pack(side="left", padx=4)
        ttk.Button(actions, text="Restart", command=self.restart, style="Mystery.TButton").pack(side="left", padx=4)
        tk.Label(
            bar,
            textvariable=self.status_var,
            bg=self.PAPER,
            fg=self.MUTED,
            font=self._font("ui", 8),
            wraplength=950,
        ).pack(pady=(7, 0))

    # ---------- rendering ----------

    def render(self) -> None:
        state = self.engine.public_state()
        self._draw_board(state)
        self._draw_sidebars(state)

    def _draw_board(self, state: PublicGameState) -> None:
        for widget in self.board_panel.winfo_children():
            widget.destroy()
        self.card_buttons.clear()
        width = max(self.board_panel.winfo_width(), 640)
        height = max(self.board_panel.winfo_height(), 590)
        card_width = max(68, int((width - 55) / state.size))
        card_height = max(82, int((height - 65) / state.size))
        compact = card_width < 150 or card_height < 155

        heading = tk.Frame(self.board_panel, bg=self.PAPER)
        heading.pack(fill="x", pady=(0, 5))
        tk.Label(
            heading,
            text=state.title,
            bg=self.PAPER,
            fg=self.INK,
            font=self._font("heading", 16 if width > 600 else 13, "bold"),
        ).pack(side="left")
        tk.Label(
            heading,
            text="Gold: clue owner  |  Blue: referenced cells",
            bg=self.PAPER,
            fg=self.MUTED,
            font=self._font("ui", 7),
        ).pack(side="right")

        grid = tk.Frame(self.board_panel, bg=self.PAPER)
        grid.pack(fill="both", expand=True)
        for column in range(state.size):
            grid.grid_columnconfigure(column + 1, weight=1, uniform="cards")
            tk.Label(grid, text=chr(65 + column), bg=self.PAPER, fg=self.MUTED, font=self._font("mono", 9, "bold")).grid(row=0, column=column + 1, pady=2)
        for row in range(state.size):
            grid.grid_rowconfigure(row + 1, weight=1, uniform="cards")
            tk.Label(grid, text=str(row + 1), bg=self.PAPER, fg=self.MUTED, font=self._font("mono", 9, "bold")).grid(row=row + 1, column=0, padx=4)

        for character in state.characters:
            column = ord(character.cell[0]) - 65
            row = int(character.cell[1:]) - 1
            background, border, thickness = self._card_colors(character)
            card = tk.Frame(
                grid,
                bg=background,
                width=card_width,
                height=card_height,
                highlightbackground=border,
                highlightcolor=border,
                highlightthickness=thickness,
                cursor="hand2",
            )
            card.grid(row=row + 1, column=column + 1, sticky="nsew", padx=4, pady=4)
            card.pack_propagate(False)
            self.card_buttons[character.cell] = card
            self._populate_card(card, character, compact, card_width, card_height)
            self._bind_tree(card, lambda _event, cell=character.cell: self.select_card(cell))

    def _card_colors(self, character: PublicCharacter) -> tuple[str, str, int]:
        if character.revealed:
            background = "#f6d4d0" if character.proved_status is Status.CRIMINAL else self.SAGE
            border = self.RED if character.proved_status is Status.CRIMINAL else self.GREEN
        else:
            mark = self.marks.get(character.cell, 0)
            background = self.MARK_COLORS[mark] if mark else self.FACE_DOWN
            border = self.LINE
        thickness = 2
        if self.spotlight_owner:
            if character.cell == self.spotlight_owner:
                border, thickness = self.GOLD, 5
            elif character.cell in self.highlighted:
                border, thickness = self.BLUE, 5
            else:
                background, border = self.DIM, "#a79d93"
        elif character.cell == self.selected_cell:
            border, thickness = self.PURPLE, 5
        return background, border, thickness

    def _populate_card(
        self,
        card: tk.Frame,
        character: PublicCharacter,
        compact: bool,
        card_width: int,
        card_height: int,
    ) -> None:
        background = card.cget("bg")
        top = tk.Frame(card, bg=background)
        top.pack(fill="x", padx=6, pady=(4, 0))
        tk.Label(top, text=character.cell, bg=background, fg=self.MUTED, font=self._font("mono", 7, "bold")).pack(side="left")
        if self.marks.get(character.cell, 0):
            tk.Label(top, text="M", bg=background, fg=self.INK, font=self._font("ui", 7, "bold")).pack(side="right")
        if not character.revealed:
            avatar_size = 30 if compact else 50
            canvas = tk.Canvas(card, width=avatar_size, height=avatar_size, bg=background, highlightthickness=0)
            canvas.pack(expand=True, pady=(1, 0))
            color = self.AVATAR_COLORS[(ord(character.cell[0]) + int(character.cell[1:])) % len(self.AVATAR_COLORS)]
            canvas.create_oval(2, 2, avatar_size - 2, avatar_size - 2, fill=color, outline=self.LINE, width=1)
            initials = "".join(part[0] for part in character.name.split()[:2]).upper()
            canvas.create_text(avatar_size / 2, avatar_size / 2, text=initials, fill=self.PAPER_LIGHT, font=self._font("heading", 10 if compact else 14, "bold"))
            tk.Label(card, text=character.name, bg=background, fg=self.INK, font=self._font("ui", 8 if compact else 10, "bold")).pack()
            tk.Label(
                card,
                text=character.profession.upper(),
                bg=background,
                fg=self.MUTED,
                wraplength=max(70, card_width - 20),
                font=self._font("mono", 7 if compact else 8, "bold"),
            ).pack(pady=(0, 2))
            if not compact:
                tk.Label(card, text="FACE-DOWN", bg=background, fg=self.MUTED, font=self._font("mono", 6, "bold")).pack(pady=(0, 4))
            return
        status_color = self.RED if character.proved_status is Status.CRIMINAL else self.GREEN
        tk.Label(card, text=character.name, bg=background, fg=self.INK, font=self._font("ui", 8 if compact else 10, "bold")).pack(pady=(1, 0))
        tk.Label(card, text=character.proved_status.value, bg=background, fg=status_color, font=self._font("mono", 7 if compact else 9, "bold")).pack()
        clue_text = format_clue(character.revealed_clue)
        if compact and len(clue_text) > 78:
            clue_text = clue_text[:75].rstrip() + "..."
        clue_font = 7 if compact else 8
        tk.Label(
            card,
            text=clue_text,
            bg=background,
            fg=self.INK,
            wraplength=max(70, card_width - 18),
            justify="center",
            anchor="center",
            font=self._font("ui", clue_font),
        ).pack(fill="both", expand=True, padx=5, pady=(2, 5))

    def _draw_sidebars(self, state: PublicGameState) -> None:
        total = len(state.characters)
        revealed = len(state.revealed_cells)
        self.case_var.set(f"FIXED JSON CASE | {state.size}x{state.size} | {state.puzzle_id}")
        self.case_badge.configure(
            text=f"CASE  {state.size}x{state.size}\n{revealed:02d} CLEARED | {total - revealed:02d} OPEN\n{state.puzzle_id}"
        )
        self.progress_var.set(f"{revealed}/{total} verdicts proved | {len(state.active_clues)} clues public")
        self._draw_progress(revealed, total)
        self.clue_rows = list(state.active_clues)
        self.clue_list.delete(0, "end")
        for clue_id, clue in self.clue_rows:
            self.clue_list.insert("end", f"{clue_id}  {format_clue(clue)}")
        formula = CNFEncoder(state.size).encode_public_state(state)
        self.metrics_var.set(
            f"PRIMARY VARS   {formula.primary_count}\n"
            f"AUX VARS       {formula.auxiliary_count}\n"
            f"CNF CLAUSES    {formula.clause_count}\n"
            f"SAT CALLS      {self.agent.metrics.sat_calls}\n"
            f"DECISIONS      {self.agent.metrics.decisions}\n"
            f"PROPAGATIONS   {self.agent.metrics.propagations}\n"
            f"BACKTRACKS     {self.agent.metrics.backtracks}\n"
            f"STEPS          {self.agent.metrics.deduction_steps}\n"
            f"STATE          {self.terminal}"
        )
        self.trace_text.configure(state="normal")
        self.trace_text.delete("1.0", "end")
        self.trace_text.insert("1.0", self.agent.trace_text() or "No automated deductions yet.")
        self.trace_text.configure(state="disabled")

    def _draw_progress(self, revealed: int, total: int) -> None:
        self.progress_canvas.delete("all")
        width = max(190, self.progress_canvas.winfo_width())
        spacing = min(17, (width - 12) / max(total, 1))
        for index in range(total):
            color = self.CORAL if index < revealed else "#c7bbb0"
            x = 6 + index * spacing
            self.progress_canvas.create_oval(x, 7, x + 8, 15, fill=color, outline="")

    @staticmethod
    def _bind_tree(widget: tk.Widget, callback) -> None:
        widget.bind("<Button-1>", callback)
        for child in widget.winfo_children():
            GriductiveApp._bind_tree(child, callback)

    def _on_board_resize(self, _event=None) -> None:
        current = (self.board_panel.winfo_width(), self.board_panel.winfo_height())
        if current == self._last_board_size or current[0] < 50 or current[1] < 50:
            return
        self._last_board_size = current
        if self._resize_job is not None:
            self.after_cancel(self._resize_job)
        self._resize_job = self.after(140, self.render)

    def _on_body_resize(self, event) -> None:
        """Collapse the instructional sidebar before the board becomes cramped."""
        should_show = show_instruction_sidebar(event.width)
        if should_show == self._info_visible:
            return
        self._info_visible = should_show
        if should_show:
            self.body.grid_columnconfigure(0, minsize=238, weight=0)
            self.info_panel.grid()
        else:
            self.info_panel.grid_remove()
            self.body.grid_columnconfigure(0, minsize=0, weight=0)
        self.after_idle(self.render)

    # ---------- interaction ----------

    def select_card(self, cell: str) -> None:
        if self.auto_running:
            return
        state = self.engine.public_state()
        character = next(item for item in state.characters if item.cell == cell)
        self.selected_cell = cell
        if character.revealed_clue is not None:
            self.spotlight_owner = cell
            self.highlighted = set(referenced_cells(character.revealed_clue, state.size))
            self.detail_title_var.set(f"CLUE_{cell} | {character.name}")
            self.detail_var.set(
                f"{format_clue(character.revealed_clue)}\nGold marks the clue owner; blue marks every referenced cell."
            )
            self.status_var.set(f"Clue spotlight active for CLUE_{cell}.")
        else:
            self.spotlight_owner = None
            self.highlighted.clear()
            self.detail_title_var.set(f"{cell} | {character.name}")
            self.detail_var.set(
                f"{character.profession}. This card is face-down; neither its status nor clue is public."
            )
            self.status_var.set(f"Selected {cell}. Submit only a logically forced verdict.")
        self.render()

    def select_clue(self, _event=None) -> None:
        selection = self.clue_list.curselection()
        if not selection:
            return
        clue_id, clue = self.clue_rows[selection[0]]
        owner = clue_id.removeprefix("CLUE_")
        self.spotlight_owner = owner
        self.selected_cell = owner
        self.highlighted = set(referenced_cells(clue, self.engine.public_state().size))
        self.detail_title_var.set(clue_id)
        self.detail_var.set(format_clue(clue))
        self.status_var.set(f"Spotlight: {clue_id} references {', '.join(sorted(self.highlighted))}.")
        self.render()

    def clear_spotlight(self) -> None:
        self.spotlight_owner = None
        self.highlighted.clear()
        self.status_var.set("Clue spotlight cleared.")
        self.render()

    def call(self, status: Status) -> None:
        if self.auto_running:
            return
        if not self.selected_cell:
            self.status_var.set("Select a face-down card first.")
            return
        state = self.engine.public_state()
        if self.selected_cell not in state.unresolved_cells:
            self.status_var.set(f"{self.selected_cell} is already revealed.")
            return
        result = self.agent.classify(state, self.selected_cell)
        outcome = self.engine.submit_proved_verdict(self.selected_cell, status, result.classification.value)
        if outcome is VerdictOutcome.ACCEPTED:
            self.status_var.set(
                f"ACCEPTED - {self.selected_cell} is {status.value}. Its public clue is now revealed."
            )
            self.marks.pop(self.selected_cell, None)
            self._reset_hint()
        elif outcome is VerdictOutcome.NOT_PROVABLE:
            self.status_var.set(
                f"NOT_PROVABLE - both statuses remain consistent for {self.selected_cell}; nothing was revealed."
            )
        elif outcome is VerdictOutcome.CONTRADICTED:
            self.status_var.set(
                f"CONTRADICTED - public knowledge forces the opposite verdict; nothing was revealed."
            )
        else:
            self.terminal = "INCONSISTENT"
            self.status_var.set("INCONSISTENT - the public knowledge base has no model.")
        if self.engine.solved:
            self.terminal = "SOLVED"
            self.status_var.set("Case solved - every verdict followed from public knowledge, with zero guesses.")
        self.render()

    def mark_selected(self) -> None:
        if self.selected_cell is None:
            self.status_var.set("Select an unresolved card before adding a pencil mark.")
            return
        if self.selected_cell not in self.engine.public_state().unresolved_cells:
            self.status_var.set("Pencil marks are only available on face-down cards.")
            return
        self.marks[self.selected_cell] = (self.marks.get(self.selected_cell, 0) + 1) % len(self.MARK_COLORS)
        mark = self.marks[self.selected_cell]
        self.status_var.set(
            f"Pencil mark on {self.selected_cell}: {'cleared' if mark == 0 else f'color {mark}'}. It never enters the KB."
        )
        self.render()

    def hint(self) -> None:
        state = self.engine.public_state()
        if self.hint_move is None or self.hint_move.cell not in state.unresolved_cells:
            self.hint_move = self.agent.hint(state)
            self.hint_stage = 0
        move = self.hint_move
        if move is None:
            self.status_var.set("No logically provable move is currently available.")
            return
        if move.result.classification is Classification.INCONSISTENT:
            self.terminal = "INCONSISTENT"
            self.status_var.set("The current public knowledge base is inconsistent.")
            self.render()
            return
        related = next(
            (
                (clue_id, clue)
                for clue_id, clue in state.active_clues
                if move.cell in referenced_cells(clue, state.size)
            ),
            None,
        )
        if self.hint_stage == 0 and related is not None:
            clue_id, clue = related
            self.spotlight_owner = clue_id.removeprefix("CLUE_")
            self.highlighted = set(referenced_cells(clue, state.size))
            self.detail_title_var.set(f"Hint 1/2 | inspect {clue_id}")
            self.detail_var.set(format_clue(clue))
            self.status_var.set(f"Hint 1/2 - this public clue is relevant to {move.cell}.")
            self.hint_stage = 1
        else:
            self.spotlight_owner = None
            self.highlighted.clear()
            self.selected_cell = move.cell
            self.detail_title_var.set("Hint 2/2 | forced verdict")
            self.detail_var.set(
                f"{move.cell} must be {move.status.value}; assuming the opposite makes the public KB UNSAT."
            )
            self.status_var.set(
                f"Hint 2/2 - {move.cell} is provably {move.status.value}. No hidden solution was consulted."
            )
            self.hint_stage = 0
        self.render()

    def auto_solve(self) -> None:
        if self.auto_running:
            return
        self.auto_running = True
        self.spotlight_owner = None
        self.highlighted.clear()
        self.status_var.set("Auto Solve is deriving one public verdict at a time...")
        self.after(120, self._auto_step)

    def _auto_step(self) -> None:
        if self.engine.solved:
            self.auto_running = False
            self.terminal = "SOLVED"
            self.status_var.set("Auto Solve completed the case without guessing.")
            self.render()
            return
        before = set(self.engine.public_state().revealed_cells)
        outcome = self.agent.apply_next(self.engine)
        after = set(self.engine.public_state().revealed_cells)
        newly_revealed = tuple(after - before)
        if outcome is VerdictOutcome.INCONSISTENT:
            self.auto_running = False
            self.terminal = "INCONSISTENT"
            self.status_var.set("Auto Solve stopped: public KB is inconsistent.")
        elif outcome is None:
            self.auto_running = False
            self.terminal = "STALLED"
            self.status_var.set("Auto Solve stopped: no provable move is available.")
        elif outcome is VerdictOutcome.ACCEPTED:
            self.selected_cell = newly_revealed[0] if newly_revealed else self.selected_cell
            self._reset_hint()
            self.status_var.set(f"ACCEPTED - revealed {self.selected_cell} from an UNSAT refutation.")
        else:
            self.auto_running = False
            self.terminal = "STALLED"
            self.status_var.set(f"Auto Solve stopped: {outcome.value}.")
        self.render()
        if self.auto_running:
            self.after(380, self._auto_step)

    # ---------- case controls ----------

    def _normal_puzzle_paths(self) -> list[Path]:
        normal = Path(__file__).resolve().parents[1] / "puzzles" / "normal"
        return sorted(normal.glob("*.json"))

    def next_case(self) -> None:
        paths = self._normal_puzzle_paths()
        if not paths:
            self.status_var.set("No fixed JSON puzzles were found.")
            return
        try:
            index = paths.index(self.current_path)
        except ValueError:
            index = -1
        self._replace_case(paths[(index + 1) % len(paths)])

    def load(self) -> None:
        path = filedialog.askopenfilename(
            title="Load Griductive puzzle",
            initialdir=str(self.current_path.parent),
            filetypes=(("JSON puzzle", "*.json"),),
        )
        if path:
            self._replace_case(Path(path))

    def _replace_case(self, path: Path) -> None:
        try:
            engine = GameEngine(load_puzzle(path))
        except PuzzleValidationError as exc:
            messagebox.showerror("Invalid puzzle", str(exc))
            return
        self.current_path = path.resolve()
        self.engine = engine
        self.agent.reset()
        self._reset_view_state()
        self.status_var.set(f"Loaded fixed case {self.engine.public_state().puzzle_id}.")
        self.render()

    def restart(self) -> None:
        self.auto_running = False
        self.engine.restart()
        self.agent.reset()
        self._reset_view_state()
        self.status_var.set("Case restarted. Timer, trace, spotlight, and pencil marks were cleared.")
        self.render()

    def _reset_view_state(self) -> None:
        self.selected_cell = None
        self.spotlight_owner = None
        self.highlighted.clear()
        self.marks.clear()
        self.terminal = "PLAYING"
        self.started_at = monotonic()
        self._reset_hint()

    def _reset_hint(self) -> None:
        self.hint_stage = 0
        self.hint_move = None

    # ---------- help and time ----------

    def show_tutorial(self) -> None:
        modal = tk.Toplevel(self.master)
        modal.title("How to play Griductive")
        modal.configure(bg=self.PAPER_LIGHT)
        modal.transient(self.master)
        modal.grab_set()
        modal.geometry("650x570")
        modal.minsize(560, 480)
        header = tk.Frame(modal, bg=self.PAPER_LIGHT)
        header.pack(fill="x", padx=24, pady=(20, 8))
        tk.Label(header, text="How to investigate", bg=self.PAPER_LIGHT, fg=self.INK, font=self._font("heading", 19, "bold")).pack(side="left")
        tk.Button(header, text="X", command=modal.destroy, bg=self.PAPER_LIGHT, fg=self.INK, relief="flat", font=self._font("ui", 13, "bold")).pack(side="right")
        sections = (
            ("THE LOOP", "Select a face-down card and call a verdict only when every model of the public clues agrees. An accepted call reveals that card's always-true clue."),
            ("REJECTIONS", "NOT_PROVABLE means both statuses remain possible. CONTRADICTED means the opposite is forced. Neither outcome changes the game or reveals hidden information."),
            ("CLUE SPOTLIGHT", "Select a revealed card or clue. Gold marks its owner, blue marks referenced cells, and unrelated cards dim."),
            ("PENCIL MARKS", "Cycle visual note colors on unresolved cards. These notes never enter PublicGameState or the SAT knowledge base."),
            ("TWO-STAGE HINT", "The first hint spotlights a relevant public clue. The next identifies a forced verdict through an UNSAT contradiction."),
            ("AUTO SOLVE", "The agent reveals one row-major forced verdict at a time and records DPLL statistics and a deduction trace. It never guesses."),
            ("FIXED CASES", "Next Fixed Case cycles the validated JSON dataset. Load JSON keeps strict schema validation and never replaces the fixed benchmark collection."),
        )
        content = tk.Frame(modal, bg=self.PAPER_LIGHT)
        content.pack(fill="both", expand=True, padx=28, pady=4)
        for heading, text in sections:
            tk.Label(content, text=heading, bg=self.PAPER_LIGHT, fg=self.CORAL_DARK, font=self._font("mono", 8, "bold")).pack(anchor="w")
            tk.Label(content, text=text, bg=self.PAPER_LIGHT, fg=self.MUTED, wraplength=570, justify="left", font=self._font("ui", 9)).pack(anchor="w", pady=(2, 9))
        ttk.Button(modal, text="Open the case", command=modal.destroy, style="Primary.TButton").pack(fill="x", padx=28, pady=(4, 20))
        modal.bind("<Escape>", lambda _event: modal.destroy())

    def _tick_timer(self) -> None:
        try:
            elapsed = max(0, int(monotonic() - self.started_at))
            self.timer_var.set(f"{elapsed // 60:02d}:{elapsed % 60:02d}")
            self.after(1000, self._tick_timer)
        except tk.TclError:
            return


def run(puzzle_path: str | Path) -> None:
    enable_windows_dpi_awareness()
    root = tk.Tk()
    GriductiveApp(root, puzzle_path)
    root.mainloop()
