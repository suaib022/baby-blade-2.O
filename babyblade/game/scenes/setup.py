"""Match setup for Human vs AI and AI vs AI."""

from __future__ import annotations

import random
from dataclasses import replace

import pygame

from babyblade.game import assets as A
from babyblade.game import inputs, ui
from babyblade.game.app import Scene
from babyblade.game.match import MatchSetup, ai_side, human_side
from babyblade.game.profile import PROFILE, art_for
from babyblade.sim.blades import SPECS, STADIUM_BLURBS, STADIUM_NAMES, BladeType, StadiumType

AGENTS = ["Ironclad", "Cyclone"]
AGENT_NOTES = ["Minimax · alpha-beta · iterative deepening", "Monte Carlo Tree Search · UCB1"]
DIFFS = ["Easy", "Medium", "Hard"]
KINDS = list(BladeType)
KIND_NAMES = [SPECS[k].name for k in KINDS]
KIND_NOTES = [SPECS[k].blurb for k in KINDS]
STADIUMS = list(StadiumType)


class SetupScene(Scene):
    def __init__(self, human: bool = True) -> None:
        self.human = human
        self.t = 0.0
        x, w, h, gap = 70, 520, 66, 10
        y = 132
        rows = []

        def choice(label, opts, idx, notes=None, accent=A.BLUE):
            nonlocal y
            c = ui.Choice((x, y, w, h), label, opts, idx, notes=notes, accent=accent)
            y += h + gap
            rows.append(c)
            return c

        if human:
            my_kind = KINDS.index(PROFILE.look.kind)
            self.opp = choice("Opponent", AGENTS, 0, AGENT_NOTES, A.RED)
            self.diff = choice("Difficulty", DIFFS, 1, None, A.RED)
            self.k1 = choice("Your blade", KIND_NAMES, my_kind, KIND_NOTES, A.BLUE)
            self.k2 = choice("Opponent blade", KIND_NAMES, 2, KIND_NOTES, A.RED)
        else:
            self.a1 = choice("Player 1 AI", AGENTS, 0, AGENT_NOTES, A.BLUE)
            self.d1 = choice("Player 1 difficulty", DIFFS, 1, None, A.BLUE)
            self.k1 = choice("Player 1 blade", KIND_NAMES, 2, KIND_NOTES, A.BLUE)
            self.a2 = choice("Player 2 AI", AGENTS, 1, AGENT_NOTES, A.RED)
            self.d2 = choice("Player 2 difficulty", DIFFS, 1, None, A.RED)
            self.k2 = choice("Player 2 blade", KIND_NAMES, 1, KIND_NOTES, A.RED)
        self.st = choice("Stadium", [STADIUM_NAMES[s] for s in STADIUMS], 0, [STADIUM_BLURBS[s] for s in STADIUMS], A.GOLD)
        self.go = ui.Button((A.W - 70 - 420, A.H - 104, 420, 64), "Let it rip!" if human else "Start duel",
                            self._start, icon="SPECIAL", accent=A.GOLD, size=26)
        self.back = ui.Button((A.W - 70 - 420, A.H - 172, 420, 52), "Back", self._back, accent=A.MUTED, size=20)
        self.menu = ui.Menu(rows + [self.go, self.back])

    def _setup(self) -> MatchSetup:
        stadium = STADIUMS[self.st.index]
        seed = random.randint(0, 99999)
        if self.human:
            me = human_side()
            me = replace(me, look=replace(me.look, archetype=KINDS[self.k1.index].value))
            opp = ai_side(AGENTS[self.opp.index], DIFFS[self.diff.index], KINDS[self.k2.index])
            return MatchSetup(me, opp, stadium, seed)
        p1 = ai_side(AGENTS[self.a1.index], DIFFS[self.d1.index], KINDS[self.k1.index])
        p2 = ai_side(AGENTS[self.a2.index], DIFFS[self.d2.index], KINDS[self.k2.index])
        if p1.controller == p2.controller:  # same agent on both sides: give P2 the other look
            from babyblade.game.profile import AI_LOOKS
            other = "Cyclone" if p1.controller == "Ironclad" else "Ironclad"
            p2 = replace(p2, look=replace(AI_LOOKS[other], archetype=KINDS[self.k2.index].value))
        return MatchSetup(p1, p2, stadium, seed)

    def _start(self) -> None:
        from babyblade.game.scenes.battle import BattleScene
        self.app.push(BattleScene(self._setup()))

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
        self.t += dt
        self.menu.update(dt)

    def draw(self, screen: pygame.Surface) -> None:
        screen.blit(A.stage_background(), (0, 0))
        title = "HUMAN vs AI" if self.human else "AI vs AI"
        A.glow_text(screen, title, 54, A.WHITE, A.BLUE if self.human else A.RED, (70, 40), anchor="topleft")
        A.text(screen, "Choose your battle", 18, A.MUTED, (74, 102), anchor="topleft")
        self.menu.draw(screen)
        # Preview panel
        pv = pygame.Rect(A.W - 70 - 420, 132, 420, 400)
        ui.panel(screen, pv, alpha=190, title="Preview")
        s = self._setup_preview()
        for i, (side, cx) in enumerate(((s[0], pv.x + 105), (s[1], pv.right - 105))):
            look, label, kind = side
            art = art_for(look, 46)
            screen.blit(A.glow(80, look.color, 0.7), (cx - 80, pv.y + 140 - 80), special_flags=pygame.BLEND_ADD)
            art.draw(screen, (cx, pv.y + 140), self.t * 11, 0.85)
            A.text(screen, label, 20, look.color, (cx, pv.y + 214), weight="bold")
            sp = SPECS[kind]
            A.text(screen, sp.name.upper(), 16, A.WHITE, (cx, pv.y + 240), weight="bold")
            for j, line in enumerate((f"Stability {sp.max_stability:.0f}", f"Spin loss {sp.energy_loss:.0f}/round", f"Power {sp.power:.2f}x")):
                A.text(screen, line, 15, A.MUTED, (cx, pv.y + 266 + j * 20))
        A.glow_text(screen, "VS", 44, A.WHITE, A.RED, (pv.centerx, pv.y + 140))
        st = STADIUMS[self.st.index]
        A.text(screen, STADIUM_NAMES[st].upper(), 18, A.GOLD, (pv.centerx, pv.bottom - 52), weight="bold")
        A.text(screen, STADIUM_BLURBS[st], 15, A.MUTED, (pv.centerx, pv.bottom - 28))
        A.text(screen, "LEFT/RIGHT change  ·  UP/DOWN move  ·  ENTER start  ·  ESC back", 14, A.DIM, (74, A.H - 28), anchor="midleft")

    def _setup_preview(self):
        if self.human:
            me = PROFILE.look
            from babyblade.game.profile import AI_LOOKS
            return ((me, "YOU", KINDS[self.k1.index]), (AI_LOOKS[AGENTS[self.opp.index]], AGENTS[self.opp.index].upper(), KINDS[self.k2.index]))
        from babyblade.game.profile import AI_LOOKS
        l1 = AI_LOOKS[AGENTS[self.a1.index]]
        l2 = AI_LOOKS[AGENTS[self.a2.index]]
        if AGENTS[self.a1.index] == AGENTS[self.a2.index]:
            l2 = AI_LOOKS["Cyclone" if AGENTS[self.a1.index] == "Ironclad" else "Ironclad"]
        return ((l1, AGENTS[self.a1.index].upper(), KINDS[self.k1.index]), (l2, AGENTS[self.a2.index].upper(), KINDS[self.k2.index]))
