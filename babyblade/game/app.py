"""Application shell: window, scene stack, main loop (sync for desktop, async for the browser)."""

from __future__ import annotations

import asyncio
import warnings
import os
import sys
from typing import List, Optional

import pygame

from babyblade.game import assets as A
from babyblade.game import inputs
from babyblade.game.audio import AUDIO
from babyblade.game.profile import IS_WEB, PROFILE


class Scene:
    """Base scene. `app` is set when pushed."""

    app: "App"

    def enter(self) -> None:
        pass

    def exit(self) -> None:
        pass

    def event(self, e: pygame.event.Event) -> None:
        pass

    def update(self, dt: float) -> None:
        pass

    def draw(self, screen: pygame.Surface) -> None:
        pass


class App:
    def __init__(self, max_frames: Optional[int] = None, shot: Optional[str] = None,
                 first_scene: Optional[Scene] = None) -> None:
        self.max_frames = max_frames
        self.shot = shot
        self.stack: List[Scene] = []
        self.running = False
        self.frame = 0
        self._first = first_scene
        self.clock: Optional[pygame.time.Clock] = None
        self.screen: Optional[pygame.Surface] = None
        self.fps = 60.0

    # ---- scenes -----------------------------------------------------------------------------
    @property
    def scene(self) -> Optional[Scene]:
        return self.stack[-1] if self.stack else None

    def push(self, scene: Scene) -> None:
        scene.app = self
        self.stack.append(scene)
        scene.enter()

    def pop(self) -> None:
        if self.stack:
            self.stack.pop().exit()
        if self.scene:
            self.scene.enter()

    def replace(self, scene: Scene) -> None:
        if self.stack:
            self.stack.pop().exit()
        self.push(scene)

    def reset_to(self, scene: Scene) -> None:
        while self.stack:
            self.stack.pop().exit()
        self.push(scene)

    def quit(self) -> None:
        if not IS_WEB:
            self.running = False

    # ---- lifecycle ----------------------------------------------------------------------------
    def setup(self) -> None:
        warnings.filterwarnings("ignore", message="no fast renderer")
        pygame.init()
        flags = pygame.SCALED | pygame.RESIZABLE
        if PROFILE.settings.fullscreen and not IS_WEB:
            flags |= pygame.FULLSCREEN
        try:
            self.screen = pygame.display.set_mode((A.W, A.H), flags)
        except Exception:
            self.screen = pygame.display.set_mode((A.W, A.H))
        pygame.display.set_caption("BABY BLADE 2.0")
        self.clock = pygame.time.Clock()
        inputs.init()
        AUDIO.init()
        AUDIO.master = PROFILE.settings.master
        AUDIO.sfx_vol = PROFILE.settings.sfx
        from babyblade.game.scenes.title import TitleScene
        self.push(self._first or TitleScene())
        self.running = True

    def tick(self) -> bool:
        assert self.clock is not None and self.screen is not None
        dt = min(self.clock.tick(60) / 1000.0, 1 / 20)
        self.fps = self.clock.get_fps() or self.fps
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                if not IS_WEB:
                    self.running = False
                continue
            if e.type in (pygame.JOYDEVICEADDED, pygame.JOYDEVICEREMOVED):
                inputs.handle_device(e)
            if e.type == pygame.KEYDOWN and e.key == pygame.K_F11 and not IS_WEB:
                pygame.display.toggle_fullscreen()
                PROFILE.settings.fullscreen = not PROFILE.settings.fullscreen
                continue
            if e.type == pygame.KEYDOWN and e.key == pygame.K_m:
                AUDIO.muted = not AUDIO.muted
                if AUDIO.muted:
                    AUDIO.stop_hums()
            if self.scene:
                self.scene.event(e)
        AUDIO.pump(0.004)
        if self.scene:
            self.scene.update(dt)
        if self.scene:
            self.scene.draw(self.screen)
        if PROFILE.settings.show_fps:
            A.text(self.screen, f"{self.fps:.0f} FPS", 14, A.GREEN, (A.W - 10, A.H - 10), anchor="bottomright")
        pygame.display.flip()
        self.frame += 1
        if self.max_frames is not None and self.frame >= self.max_frames:
            self.running = False
        return self.running and bool(self.stack)

    @staticmethod
    def _log_crash() -> None:
        """Write the traceback next to the profile so a crash can be reported."""
        try:
            import traceback
            path = os.path.join(os.path.expanduser("~"), ".babyblade2.log")
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(traceback.format_exc() + "\n")
        except Exception:
            pass

    def teardown(self) -> None:
        if self.shot and self.screen is not None:
            try:
                pygame.image.save(self.screen, self.shot)
            except Exception:
                pass
        PROFILE.save()
        if pygame.get_init():
            pygame.quit()

    def run(self) -> int:
        try:
            self.setup()
            while self.tick():
                pass
            return 0
        except Exception:
            self._log_crash()
            raise
        finally:
            self.teardown()

    async def run_async(self) -> int:
        try:
            self.setup()
            while self.tick():
                await asyncio.sleep(0)
            return 0
        finally:
            self.teardown()
