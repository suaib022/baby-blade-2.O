"""Settings: audio, screen shake, FPS counter, fullscreen."""

from __future__ import annotations

import pygame

from babyblade.game import assets as A
from babyblade.game import inputs, ui
from babyblade.game.app import Scene
from babyblade.game.audio import AUDIO
from babyblade.game.profile import IS_WEB, PROFILE

LEVELS = [0, 20, 40, 60, 80, 100]


class SettingsScene(Scene):
    def __init__(self) -> None:
        s = PROFILE.settings
        x, w, h, gap = A.W // 2 - 280, 560, 68, 12
        y = 150
        rows = []

        def choice(label, opts, idx, fn):
            nonlocal y
            c = ui.Choice((x, y, w, h), label, opts, idx, on_change=fn)
            y += h + gap
            rows.append(c)
            return c

        near = lambda v: min(range(len(LEVELS)), key=lambda i: abs(LEVELS[i] - v * 100))
        choice("Master volume", [f"{v}%" for v in LEVELS], near(s.master), self._master)
        choice("Effects volume", [f"{v}%" for v in LEVELS], near(s.sfx), self._sfx)
        choice("Screen shake", ["Off", "On"], 1 if s.shake else 0, lambda i: setattr(PROFILE.settings, "shake", i == 1))
        choice("FPS counter", ["Off", "On"], 1 if s.show_fps else 0, lambda i: setattr(PROFILE.settings, "show_fps", i == 1))
        choice("Coach hints", ["Off", "On"], 1 if s.coach else 0, lambda i: setattr(PROFILE.settings, "coach", i == 1))
        if not IS_WEB:
            choice("Fullscreen (next launch)", ["Off", "On"], 1 if s.fullscreen else 0,
                   lambda i: setattr(PROFILE.settings, "fullscreen", i == 1))
        back = ui.Button((A.W // 2 - 150, y + 12, 300, 58), "Save & back", self._back, accent=A.GREEN)
        self.menu = ui.Menu(rows + [back])

    def _master(self, i: int) -> None:
        PROFILE.settings.master = LEVELS[i] / 100
        AUDIO.master = PROFILE.settings.master
        AUDIO.play("select")

    def _sfx(self, i: int) -> None:
        PROFILE.settings.sfx = LEVELS[i] / 100
        AUDIO.sfx_vol = PROFILE.settings.sfx
        AUDIO.clash(0.8)

    def _back(self) -> None:
        PROFILE.save()
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

    def draw(self, screen: pygame.Surface) -> None:
        screen.blit(A.stage_background(), (0, 0))
        A.glow_text(screen, "SETTINGS", 54, A.WHITE, A.BLUE, (A.W / 2, 80))
        self.menu.draw(screen)
