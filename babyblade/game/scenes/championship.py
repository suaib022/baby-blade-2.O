"""Championship: you against seven AIs in a single-elimination bracket."""

from __future__ import annotations

import math
import random

import pygame

from babyblade.championship import ROUND_BEST_OF, ROUND_NAMES, Championship, Match
from babyblade.game import assets as A
from babyblade.game import inputs, ui
from babyblade.game.app import Scene
from babyblade.game.audio import AUDIO
from babyblade.game.match import MatchSetup, ai_side, human_side
from babyblade.game.profile import PROFILE
from babyblade.sim.blades import SPECS, STADIUM_NAMES

CARD_W, CARD_H = 350, 92
COL_X = [48, 462, 876]
QF_Y = [138, 262, 386, 510]


def _card_pos(r: int, i: int):
    if r == 0:
        y = QF_Y[i]
    elif r == 1:
        y = (QF_Y[2 * i] + QF_Y[2 * i + 1]) // 2
    else:
        y = ((QF_Y[0] + QF_Y[1]) // 2 + (QF_Y[2] + QF_Y[3]) // 2) // 2
    return COL_X[r], y


class ChampionshipScene(Scene):
    def __init__(self) -> None:
        self.champ = Championship(PROFILE.look.kind, seed=random.randint(0, 10 ** 6))
        self.t = 0.0
        self.counted = False
        self.confetti = []
        self.rng = random.Random(3)
        self.menu = ui.Menu([])
        self._build_menu()

    # ---- state ----------------------------------------------------------------------------
    def enter(self) -> None:
        """Called when the scene appears and again whenever a battle returns to it."""
        c = self.champ
        c.simulate_ai_matches()
        if c.player_eliminated and not c.over:
            c.finish_without_player()
        if c.over and not self.counted:
            self.counted = True
            st = PROFILE.stats
            st.championships += 1
            if c.champion is not None and c.champion.is_player:
                st.titles += 1
                self._burst()
                AUDIO.play("go")
                AUDIO.play("crowd", 0.8)
            PROFILE.save()
        self._build_menu()

    def _burst(self) -> None:
        for _ in range(160):
            self.confetti.append([self.rng.uniform(0, A.W), self.rng.uniform(-300, 0), self.rng.uniform(-30, 30),
                                  self.rng.uniform(80, 220), self.rng.choice([A.BLUE, A.RED, A.GOLD, A.GREEN, A.PURPLE]),
                                  self.rng.uniform(0, 6)])

    def _build_menu(self) -> None:
        c = self.champ
        y = A.H - 74
        widgets = []
        m = c.next_player_match()
        if m is not None and not c.over:
            label = f"Play {ROUND_NAMES[m.round]}" + (f" · game {m.game_number} of {m.best_of}" if m.best_of > 1 else "")
            widgets.append(ui.Button((A.W // 2 - 220, y, 440, 56), label, self._play_match, icon="SPECIAL", accent=A.GOLD, size=22))
        elif c.over:
            widgets.append(ui.Button((A.W // 2 - 220, y, 215, 56), "New championship", self._restart, accent=A.GREEN))
            widgets.append(ui.Button((A.W // 2 + 5, y, 215, 56), "Main menu", self._back, accent=A.MUTED))
        widgets.append(ui.Button((60, y, 170, 56), "Leave", self._back, accent=A.RED if not c.over else A.MUTED))
        self.menu = ui.Menu(widgets)

    # ---- actions --------------------------------------------------------------------------
    def _play_match(self) -> None:
        from babyblade.game.scenes.battle import BattleScene
        c = self.champ
        m = c.next_player_match()
        if m is None:
            return
        foe = m.b if m.a.is_player else m.a
        setup = MatchSetup(human_side(), ai_side(foe.agent, foe.difficulty, foe.archetype), c.stadium_for(m),
                           random.randint(0, 99999))

        def done(battle, match=m):
            c.record_player_battle(match, battle, player_side=1)
            st = PROFILE.stats
            st.battles += 1
            if battle.winner == 1:
                st.battles_won += 1

        setup.on_finish = done
        self.app.push(BattleScene(setup))

    def _restart(self) -> None:
        self.app.replace(ChampionshipScene())

    def _back(self) -> None:
        self.app.pop()

    # ---- input / update ----------------------------------------------------------------------
    def event(self, e: pygame.event.Event) -> None:
        cmd = inputs.nav(e)
        if cmd == "back":
            self._back()
            return
        if cmd in ("left", "right", "confirm"):
            self.menu.nav(cmd)
        self.menu.handle(e)

    def update(self, dt: float) -> None:
        self.t += dt
        self.menu.update(dt)
        for p in self.confetti:
            p[1] += p[3] * dt
            p[0] += p[2] * dt + math.sin(self.t * 3 + p[5]) * 20 * dt
            if p[1] > A.H + 20:
                p[1] = -20

    # ---- drawing ------------------------------------------------------------------------------
    def draw(self, screen: pygame.Surface) -> None:
        c = self.champ
        screen.blit(A.stage_background(), (0, 0))
        A.glow_text(screen, "CHAMPIONSHIP", 50, A.WHITE, A.GOLD, (A.W / 2, 44))
        A.text(screen, self._status(), 18, A.MUTED, (A.W / 2, 90))
        for r, name in enumerate(ROUND_NAMES):
            x = COL_X[r] + CARD_W // 2
            A.text(screen, f"{name.upper()}  ·  BEST OF {ROUND_BEST_OF[r]}", 15, A.GOLD if r == c.current_round and not c.over else A.DIM,
                   (x, 122), weight="bold")
        # connectors
        for r in (0, 1):
            for i, m in enumerate(c.rounds[r]):
                x0, y0 = _card_pos(r, i)
                x1, y1 = _card_pos(r + 1, i // 2)
                col = A.GOLD if m.winner is not None and m.winner.is_player else A.LINE
                mid = x0 + CARD_W + (x1 - x0 - CARD_W) // 2
                pygame.draw.lines(screen, col, False, [(x0 + CARD_W, y0 + CARD_H // 2), (mid, y0 + CARD_H // 2), (mid, y1 + CARD_H // 2), (x1, y1 + CARD_H // 2)], 2)
        nxt = c.next_player_match()
        for r, ms in enumerate(c.rounds):
            for i, m in enumerate(ms):
                x, y = _card_pos(r, i)
                self._match_card(screen, m, pygame.Rect(x, y, CARD_W, CARD_H), m is nxt and not c.over)
        # trophy
        ch = c.champion
        if ch is not None:
            self._champion_banner(screen)
        self.menu.draw(screen)
        for x, y, vx, vy, col, ph in self.confetti:
            pygame.draw.rect(screen, col, (int(x), int(y), 7, 4))
        st = PROFILE.stats
        A.text(screen, f"Titles {st.titles}  ·  Championships {st.championships}  ·  Battles won {st.battles_won}/{st.battles}", 14, A.DIM,
               (A.W - 40, A.H - 24), anchor="midright")

    def _status(self) -> str:
        c = self.champ
        if c.over:
            ch = c.champion
            return "You are the champion!" if ch.is_player else f"{ch.name} ({ch.label}) wins the cup. {c.player_result()}."
        m = c.next_player_match()
        if m is not None:
            foe = m.b if m.a.is_player else m.a
            return f"Next: {ROUND_NAMES[m.round]} vs {foe.name} ({foe.label}, {SPECS[foe.archetype].name}) in the {STADIUM_NAMES[c.stadium_for(m)]}"
        return "Waiting for the other matches…"

    def _match_card(self, screen: pygame.Surface, m: Match, r: pygame.Rect, highlight: bool) -> None:
        pulse = 0.5 + 0.5 * math.sin(self.t * 4)
        accent = A.GOLD if highlight else (A.LINE if m.winner is None else A.PANEL_HI)
        ui.panel(screen, r, accent=A.mix(A.GOLD, A.WHITE, pulse * 0.4) if highlight else accent, alpha=215, radius=12)
        for row, ent, wins in ((0, m.a, m.wins_a), (1, m.b, m.wins_b)):
            y = r.y + 24 + row * 40
            if ent is None:
                A.text(screen, "TBD", 18, A.DIM, (r.x + 18, y), anchor="midleft", weight="bold")
                continue
            won = m.winner is ent
            lost = m.winner is not None and not won
            col = A.GOLD if ent.is_player else (A.WHITE if not lost else A.DIM)
            A.text(screen, ent.name.upper(), 19, col, (r.x + 18, y - 6), anchor="midleft", weight="bold")
            sub = "YOUR BLADE" if ent.is_player else f"{ent.agent} {ent.difficulty} · {SPECS[ent.archetype].name}"
            A.text(screen, sub, 13, A.MUTED if not lost else A.DIM, (r.x + 18, y + 12), anchor="midleft")
            if m.best_of > 1 or won:
                txt = str(wins) if m.best_of > 1 else "WIN"
                A.text(screen, txt, 24 if m.best_of > 1 else 15, A.GREEN if won else (A.MUTED if not lost else A.DIM), (r.right - 20, y), anchor="midright", weight="bold")

    def _champion_banner(self, screen: pygame.Surface) -> None:
        ch = self.champ.champion
        mine = ch.is_player
        box = pygame.Rect(A.W // 2 - 300, 280, 600, 150)
        ui.panel(screen, box, accent=A.GOLD, alpha=240)
        if mine:
            A.glow_text(screen, "CHAMPION!", 64, A.WHITE, A.GOLD, (box.centerx, box.y + 52))
            A.text(screen, "You beat all seven AIs and won the cup.", 20, A.WHITE, (box.centerx, box.y + 104))
        else:
            A.text(screen, "TOURNAMENT OVER", 34, A.WHITE, (box.centerx, box.y + 38), weight="bold")
            A.text(screen, f"Champion: {ch.name} ({ch.label})", 22, A.GOLD, (box.centerx, box.y + 84), weight="bold")
            A.text(screen, self.champ.player_result(), 18, A.MUTED, (box.centerx, box.y + 116))
