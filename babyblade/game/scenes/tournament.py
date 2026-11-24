"""Tournament screen: configure, run live, and read the statistics."""

from __future__ import annotations

import os
import time

import pygame

from babyblade.game import assets as A
from babyblade.game import inputs, ui
from babyblade.game.app import Scene
from babyblade.game.profile import IS_WEB
from babyblade.sim.blades import SPECS, STADIUM_NAMES, BladeType, StadiumType
from babyblade.tournament import Tournament, TournamentConfig

AGENTS = ["Ironclad", "Cyclone"]
DIFFS = ["Easy", "Medium", "Hard"]
KINDS = list(BladeType)
COUNTS = [5, 10, 20, 50]
FIN_COL = {"RING_OUT": A.GOLD, "BURST": A.RED, "SPIN_OUT": A.CYAN, "POINTS": A.GREEN, "DRAW": A.MUTED}


class TournamentScene(Scene):
    def __init__(self) -> None:
        self.t = None
        self.message = ""
        x, w, h, gap = 60, 380, 56, 6
        y = 120
        rows = []

        def choice(label, opts, idx, accent):
            nonlocal y
            c = ui.Choice((x, y, w, h), label, opts, idx, accent=accent)
            y += h + gap
            rows.append(c)
            return c

        self.aa = choice("Agent A", AGENTS, 0, A.BLUE)
        self.da = choice("A difficulty", DIFFS, 1, A.BLUE)
        self.ka = choice("A blade", [SPECS[k].name for k in KINDS], 0, A.BLUE)
        self.ab = choice("Agent B", AGENTS, 1, A.RED)
        self.db = choice("B difficulty", DIFFS, 1, A.RED)
        self.kb = choice("B blade", [SPECS[k].name for k in KINDS], 0, A.RED)
        self.st = choice("Stadium", [STADIUM_NAMES[s] for s in StadiumType], 0, A.GOLD)
        self.n = choice("Matches", [str(c) for c in COUNTS], 1, A.GOLD)
        self.run_btn = ui.Button((x, y + 6, 186, 54), "Run", self._run, icon="PLAY", accent=A.GREEN)
        self.export_btn = ui.Button((x + 194, y + 6, 186, 54), "Export", self._export, accent=A.GOLD, enabled=not IS_WEB)
        self.back_btn = ui.Button((A.W - 60 - 160, A.H - 76, 160, 52), "Back", self._back, accent=A.MUTED)
        self.menu = ui.Menu(rows + [self.run_btn, self.export_btn, self.back_btn])

    def _config(self) -> TournamentConfig:
        return TournamentConfig(AGENTS[self.aa.index], AGENTS[self.ab.index], DIFFS[self.da.index], DIFFS[self.db.index],
                                KINDS[self.ka.index].value, KINDS[self.kb.index].value, list(StadiumType)[self.st.index].value,
                                COUNTS[self.n.index], seed=int(time.time()) % 100000)

    def _run(self) -> None:
        if self.t is not None and not self.t.done:
            self.t.cancelled = True
            self.run_btn.label = "Run"
            return
        self.t = Tournament(self._config())
        self.run_btn.label = "Stop"
        self.message = ""

    def _export(self) -> None:
        if self.t is None or not self.t.summary.played:
            self.message = "Run a tournament first."
            return
        folder = os.path.join(os.getcwd(), "tournament_results", time.strftime("%Y%m%d-%H%M%S"))
        self.t.summary.export(folder)
        self.message = f"Saved to {folder}"

    def _back(self) -> None:
        self.app.pop()

    def event(self, e: pygame.event.Event) -> None:
        cmd = inputs.nav(e)
        if cmd == "back":
            self._back()
            return
        if cmd:
            self.menu.nav(cmd)
        self.menu.handle(e)

    def update(self, dt: float) -> None:
        self.menu.update(dt)
        if self.t is not None and not self.t.done:
            deadline = time.perf_counter() + 0.012  # keep the UI at 60 fps
            while time.perf_counter() < deadline and not self.t.done:
                self.t.step(1.5)
            if self.t.done:
                self.run_btn.label = "Run"

    def draw(self, screen: pygame.Surface) -> None:
        screen.blit(A.stage_background(), (0, 0))
        A.glow_text(screen, "AI BENCHMARK", 54, A.WHITE, A.CYAN, (60, 34), anchor="topleft")
        A.text(screen, "Ironclad vs Cyclone on identical rules · sides alternate every match", 17, A.MUTED, (64, 96), anchor="topleft")
        self.menu.draw(screen)
        r = pygame.Rect(470, 120, A.W - 530, 520)
        ui.panel(screen, r, alpha=190, title="Results")
        if self.t is None:
            A.text(screen, "Configure the series and press RUN.", 20, A.MUTED, r.center)
            return
        s = self.t.summary
        cfg = self.t.config
        total = cfg.matches
        ui.bar(screen, pygame.Rect(r.x + 20, r.y + 44, r.w - 40, 14), s.played / total, A.GREEN)
        A.text(screen, f"{s.played} / {total} matches", 15, A.MUTED, (r.right - 20, r.y + 72), anchor="topright")
        names = (f"A: {cfg.agent_a} ({cfg.diff_a})", f"B: {cfg.agent_b} ({cfg.diff_b})")
        y = r.y + 100
        for who, name, col in (("A", names[0], A.BLUE), ("B", names[1], A.RED)):
            A.text(screen, name, 22, col, (r.x + 20, y), anchor="topleft", weight="bold")
            wr = s.win_rate(who)
            ui.bar(screen, pygame.Rect(r.x + 20, y + 34, r.w - 200, 18), wr, col)
            A.text(screen, f"{s.wins(who)} W  ·  {s.played - s.wins(who) - s.draws} L  ·  {wr * 100:.0f}%", 17, A.WHITE,
                   (r.right - 20, y + 43), anchor="midright", weight="bold")
            A.text(screen, f"avg decision {s.avg_think_ms(who):.1f} ms", 14, A.MUTED, (r.x + 20, y + 58), anchor="topleft")
            y += 92
        A.text(screen, f"Draws {s.draws}   ·   avg duration {s.avg_seconds:.1f}s ({s.avg_rounds:.1f} rounds)", 17, A.WHITE,
               (r.x + 20, y), anchor="topleft")
        y += 40
        A.text(screen, "FINISH TYPES", 15, A.MUTED, (r.x + 20, y), anchor="topleft", weight="bold")
        y += 26
        fins = s.finishes()
        mx = max(1, max(fins.values()))
        for name, cnt in fins.items():
            A.text(screen, name.replace("_", "-"), 15, A.WHITE, (r.x + 20, y + 9), anchor="midleft", weight="bold")
            ui.bar(screen, pygame.Rect(r.x + 140, y, r.w - 220, 18), cnt / mx, FIN_COL[name])
            A.text(screen, str(cnt), 15, A.WHITE, (r.right - 20, y + 9), anchor="midright", weight="bold")
            y += 28
        if self.message:
            A.text(screen, self.message, 14, A.GOLD, (r.x + 20, r.bottom - 22), anchor="midleft")
