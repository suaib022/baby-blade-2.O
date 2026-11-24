"""Title screen: live AI demo battle behind the logo and main menu."""

from __future__ import annotations

import math
import random

import pygame

from babyblade.game import assets as A
from babyblade.game import inputs, ui
from babyblade.game.app import Scene
from babyblade.game.arena_view import ArenaView
from babyblade.game.match import ai_side
from babyblade.game.profile import IS_WEB, AI_LOOKS
from babyblade.sim.blades import BladeType, StadiumType


class TitleScene(Scene):
    def __init__(self) -> None:
        self.t = 0.0
        self.world = pygame.Surface((A.W, A.H))
        self.shade = pygame.Surface((A.W, A.H), pygame.SRCALPHA)
        for x in range(A.W):  # dark on the left (menu), lighter on the right (demo)
            a = int(225 * max(0.0, 1 - x / (A.W * 0.62)) + 70)
            pygame.draw.line(self.shade, (4, 7, 16, min(255, a)), (x, 0), (x, A.H))
        self.demo = None
        self.view = None
        self._new_demo()
        x, y, w, h, gap = 72, 230, 360, 48, 8
        items = [
            ("Play", "Human vs AI", "ATTACK", A.BLUE, self._play),
            ("Championship", "Beat seven AIs to win the cup", "SPECIAL", A.GOLD, self._championship),
            ("AI vs AI", "Watch Ironclad and Cyclone duel", "GUARD", A.RED, self._aivai),
            ("AI Benchmark", "Compare the two AIs over many matches", None, A.CYAN, self._tournament),
            ("Customize", "Build your blade", "CHARGE", A.GREEN, self._customize),
            ("How to play", "Actions, counters, controls", "DODGE", A.PURPLE, self._howto),
            ("Settings", "Audio, coach hints, display", None, A.MUTED, self._settings),
        ]
        if not IS_WEB:
            items.append(("Quit", "", None, A.DIM, self._quit))
        widgets = []
        for i, (label, sub, icon, accent, fn) in enumerate(items):
            widgets.append(ui.Button((x, y + i * (h + gap), w, h), label, fn, icon=icon, sub=sub, accent=accent, size=22))
        self.menu = ui.Menu(widgets)

    def _new_demo(self) -> None:
        from babyblade.ai.agents import Cyclone, Ironclad
        from babyblade.sim.battle import Battle
        seed = random.randint(0, 9999)
        self.demo = Battle(BladeType.DEFENDER, BladeType.ATTACKER, random.choice(list(StadiumType)),
                           controllers=(Ironclad("Easy", seed), Cyclone("Easy", seed + 1)), seed=seed)
        self.view = ArenaView(self.demo, (AI_LOOKS["Ironclad"], AI_LOOKS["Cyclone"]), ("IRONCLAD", "CYCLONE"), silent=True)

    # navigation targets
    def _play(self) -> None:
        from babyblade.game.scenes.setup import SetupScene
        self.app.push(SetupScene(human=True))

    def _aivai(self) -> None:
        from babyblade.game.scenes.setup import SetupScene
        self.app.push(SetupScene(human=False))

    def _championship(self) -> None:
        from babyblade.game.scenes.championship import ChampionshipScene
        self.app.push(ChampionshipScene())

    def _tournament(self) -> None:
        from babyblade.game.scenes.tournament import TournamentScene
        self.app.push(TournamentScene())

    def _customize(self) -> None:
        from babyblade.game.scenes.customize import CustomizeScene
        self.app.push(CustomizeScene())

    def _howto(self) -> None:
        from babyblade.game.scenes.howto import HowToScene
        self.app.push(HowToScene())

    def _settings(self) -> None:
        from babyblade.game.scenes.settings import SettingsScene
        self.app.push(SettingsScene())

    def _quit(self) -> None:
        self.app.quit()

    def event(self, e: pygame.event.Event) -> None:
        cmd = inputs.nav(e)
        if cmd == "back":
            return
        if cmd in ("up", "down", "confirm"):
            self.menu.nav(cmd)
        self.menu.handle(e)

    def update(self, dt: float) -> None:
        self.t += dt
        self.menu.update(dt)
        if self.demo is not None and self.view is not None:
            sim = dt * self.view.camera.time_scale()
            self.demo.update(sim, think_budget=0.003)
            self.view.consume_events()
            self.view.update(dt, sim)
            if self.demo.over and self.view.finish_t > 3.0:
                self._new_demo()

    def draw(self, screen: pygame.Surface) -> None:
        if self.view is not None:
            self.view.draw(self.world)
            screen.blit(A.stage_background(), (0, 0))
            ox, oy = self.view.camera.offset()
            screen.blit(self.world, (200 + ox, oy))  # demo sits to the right of the menu
        screen.blit(self.shade, (0, 0))
        # Logo: BABY in white, BLADE in neon blue → red, like the deck's title slide.
        A.glow_text(screen, "BABY", 96, A.WHITE, (60, 110, 200), (72, 62), anchor="topleft", strength=3)
        bx = 72 + A.font(96, "bold").size("BABY ")[0]
        A.glow_text(screen, "BLADE", 96, A.BLUE_HI, A.BLUE, (bx, 62), anchor="topleft", strength=4)
        bx2 = bx + A.font(96, "bold").size("BLADE")[0] + 12
        badge = pygame.Rect(bx2, 92, 64, 34)
        pygame.draw.rect(screen, A.RED, badge, border_radius=8)
        A.text(screen, "2.0", 22, A.WHITE, badge.center, weight="bold")
        sub = "  ".join("AI-POWERED SPINNING TOP BATTLE STADIUM".split(" "))
        A.text(screen, sub, 18, A.MUTED, (76, 190), anchor="topleft", weight="regular")
        pygame.draw.line(screen, A.RED, (76, 222), (196, 222), 3)
        self.menu.draw(screen)
        A.text(screen, "ARROWS / D-PAD to move  ·  ENTER / A to select  ·  M to mute", 14, A.DIM, (76, A.H - 28), anchor="midleft")
        pulse = 0.5 + 0.5 * math.sin(self.t * 2)
        A.text(screen, "LIVE: IRONCLAD vs CYCLONE", 14, A.mix(A.MUTED, A.WHITE, pulse), (A.W - 24, A.H - 28), anchor="midright", weight="bold")
