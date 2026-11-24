"""Results: winner, finish type and match statistics."""

from __future__ import annotations

import pygame

from babyblade.game import assets as A
from babyblade.game import inputs, ui
from babyblade.game.app import Scene
from babyblade.game.arena_view import FINISH_TEXT
from babyblade.game.match import MatchSetup
from babyblade.game.profile import art_for
from babyblade.sim.actions import LABEL, ORDER
from babyblade.sim.battle import Battle
from babyblade.sim.blades import spec

REASON_TEXT = {
    "RING_OUT": "pushed out of the stadium",
    "BURST": "stability broke to zero",
    "SPIN_OUT": "ran out of spin energy",
    "DRAW": "both blades were eliminated together",
    "POINTS": "decided on points after 40 rounds",
}


class ResultsScene(Scene):
    def __init__(self, setup: MatchSetup, battle: Battle, tags) -> None:
        self.setup, self.battle, self.tags = setup, battle, tags
        self.t = 0.0
        cx = A.W // 2
        self.menu = ui.Menu([
            ui.Button((cx - 330, A.H - 92, 210, 58), "Rematch", self._rematch, icon="SPECIAL", accent=A.GOLD),
            ui.Button((cx - 105, A.H - 92, 210, 58), "Setup", self._setup, accent=A.BLUE),
            ui.Button((cx + 120, A.H - 92, 210, 58), "Main menu", self._menu, accent=A.MUTED),
        ], columns=3)
        if setup.on_finish is not None:  # championship match: report and go back to the bracket
            self.menu = ui.Menu([ui.Button((cx - 140, A.H - 92, 280, 58), "Continue", self._continue, icon="PLAY", accent=A.GREEN)])

    def _continue(self) -> None:
        if self.setup.on_finish is not None:
            self.setup.on_finish(self.battle)
        self.app.pop()

    def _rematch(self) -> None:
        from babyblade.game.scenes.battle import BattleScene
        import random
        from dataclasses import replace
        self.app.replace(BattleScene(replace(self.setup, seed=random.randint(0, 99999))))

    def _setup(self) -> None:
        self.app.pop()

    def _menu(self) -> None:
        from babyblade.game.scenes.title import TitleScene
        self.app.reset_to(TitleScene())

    def event(self, e: pygame.event.Event) -> None:
        cmd = inputs.nav(e)
        if cmd == "back":
            if self.setup.on_finish is not None:
                self._continue()
            else:
                self._menu()
            return
        if cmd in ("left", "right", "confirm"):
            self.menu.nav(cmd)
        self.menu.handle(e)

    def update(self, dt: float) -> None:
        self.t += dt
        self.menu.update(dt)

    def draw(self, screen: pygame.Surface) -> None:
        b = self.battle
        screen.blit(A.stage_background(), (0, 0))
        text, col = FINISH_TEXT.get(b.finish or "POINTS", ("FINISH", A.WHITE))
        A.glow_text(screen, text, 76, A.WHITE, col, (A.W / 2, 78), strength=3)
        if b.winner in (1, 2):
            side = self.setup.p1 if b.winner == 1 else self.setup.p2
            tag = self.tags[b.winner - 1]
            head = f"{'YOU WIN' if tag == 'YOU' else tag + ' WINS'}  ·  {side.title()}"
        else:
            head = "NO WINNER"
        A.text(screen, head, 30, A.WHITE, (A.W / 2, 146), weight="bold")
        A.text(screen, f"Finish: {REASON_TEXT.get(b.finish or 'POINTS', '')}  ·  {b.round} rounds  ·  {b.time:.1f}s", 18, A.MUTED, (A.W / 2, 182))
        for player, x in ((1, 90), (2, A.W - 90 - 500)):
            self._card(screen, player, pygame.Rect(x, 220, 500, 380))
        self.menu.draw(screen)

    def _card(self, screen: pygame.Surface, player: int, rect: pygame.Rect) -> None:
        b = self.battle
        top = b.t1 if player == 1 else b.t2
        side = self.setup.p1 if player == 1 else self.setup.p2
        won = b.winner == player
        ui.panel(screen, rect, accent=side.look.color if won else None, alpha=200)
        art = art_for(side.look, 44)
        c = (rect.x + 70, rect.y + 74)
        screen.blit(A.glow(80, side.look.color, 0.6 if won else 0.25), (c[0] - 80, c[1] - 80), special_flags=pygame.BLEND_ADD)
        art.draw(screen, c, self.t * (11 if won else 3), 0.9 if won else 0.1)
        A.text(screen, self.tags[player - 1], 16, side.look.color, (rect.x + 136, rect.y + 34), anchor="midleft", weight="bold")
        A.text(screen, side.title(), 26, A.WHITE, (rect.x + 136, rect.y + 64), anchor="midleft", weight="bold")
        A.text(screen, ("WINNER" if won else ("DRAW" if b.winner == 0 else "DEFEATED")) + f"  ·  {spec(top.kind).name}", 16,
               A.GOLD if won else A.MUTED, (rect.x + 136, rect.y + 94), anchor="midleft", weight="bold")
        st = top.stats
        rows = [
            ("Spin left", f"{max(0, top.energy):.0f} / 100"),
            ("Stability left", f"{max(0, top.stability):.0f} / {top.spec.max_stability:.0f}"),
            ("Hits landed", str(st.hits)),
            ("Damage dealt", f"{st.damage_dealt:.0f}"),
            ("Damage taken", f"{st.damage_taken:.0f}"),
        ]
        if not side.is_human and st.decisions:
            rows.append(("Avg decision time", f"{st.think_seconds / st.decisions * 1000:.1f} ms"))
        y = rect.y + 140
        for k, v in rows:
            A.text(screen, k, 17, A.MUTED, (rect.x + 30, y), anchor="midleft")
            A.text(screen, v, 18, A.WHITE, (rect.right - 30, y), anchor="midright", weight="bold")
            y += 30
        used = "  ".join(f"{LABEL[a][:3].upper()} {st.actions.get(a.value, 0)}" for a in ORDER)
        A.text(screen, used, 15, A.MUTED, (rect.centerx, rect.bottom - 26))
