"""Customize: build your blade from parts and pick its archetype (the rules)."""

from __future__ import annotations

from dataclasses import replace

import pygame

from babyblade.game import assets as A
from babyblade.game import inputs, ui
from babyblade.game.app import Scene
from babyblade.game.profile import BITS, DISKS, PROFILE, RING_COLORS, SHAPE_NOTES, art_for
from babyblade.sim.blades import SPECS, BladeType

KINDS = list(BladeType)
SHAPES = list(SHAPE_NOTES)
CLAWS = [2, 3, 4, 5]


class CustomizeScene(Scene):
    def __init__(self) -> None:
        self.t = 0.0
        lk = PROFILE.look
        x, w, h, gap = 60, 470, 66, 10
        y = 126
        rows = []

        def choice(label, opts, idx, notes=None, accent=A.BLUE):
            nonlocal y
            c = ui.Choice((x, y, w, h), label, opts, idx, on_change=lambda _i: self._apply(), notes=notes, accent=accent)
            y += h + gap
            rows.append(c)
            return c

        self.ring = choice("Attack ring", [n for n, _ in RING_COLORS], lk.ring)
        self.shape = choice("Blade shape", SHAPES, SHAPES.index(lk.shape) if lk.shape in SHAPES else 0, [SHAPE_NOTES[s] for s in SHAPES])
        self.claws = choice("Ratchet claws", [f"{c} claws" for c in CLAWS], CLAWS.index(lk.claws) if lk.claws in CLAWS else 1)
        self.disk = choice("Weight disk", [n for n, _ in DISKS], lk.disk)
        self.bit = choice("Bit", [n for n, _ in BITS], lk.bit)
        self.kind = choice("Archetype (rules)", [SPECS[k].name for k in KINDS], KINDS.index(lk.kind), [SPECS[k].blurb for k in KINDS], A.GOLD)
        self.done = ui.Button((A.W - 60 - 300, A.H - 84, 300, 58), "Save & back", self._back, accent=A.GREEN)
        self.menu = ui.Menu(rows + [self.done])

    def _apply(self) -> None:
        PROFILE.look = replace(PROFILE.look, ring=self.ring.index, shape=SHAPES[self.shape.index], claws=CLAWS[self.claws.index],
                               disk=self.disk.index, bit=self.bit.index, archetype=KINDS[self.kind.index].value)

    def _back(self) -> None:
        self._apply()
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
        self.t += dt
        self.menu.update(dt)

    def draw(self, screen: pygame.Surface) -> None:
        screen.blit(A.stage_background(), (0, 0))
        A.glow_text(screen, "CUSTOMIZE", 54, A.WHITE, PROFILE.look.color, (60, 36), anchor="topleft")
        A.text(screen, "Parts change the look. The archetype sets the rules.", 18, A.MUTED, (64, 98), anchor="topleft")
        self.menu.draw(screen)
        pv = pygame.Rect(570, 126, A.W - 630, 470)
        ui.panel(screen, pv, accent=PROFILE.look.color, alpha=190, title="Your blade")
        c = (pv.centerx, pv.y + 190)
        art = art_for(PROFILE.look, 110)
        screen.blit(A.glow(200, PROFILE.look.color, 0.55), (c[0] - 200, c[1] - 200), special_flags=pygame.BLEND_ADD)
        spin = 0.5 + 0.5 * (pygame.time.get_ticks() // 2500 % 2)  # alternates still detail and fast spin
        art.draw(screen, c, self.t * (2 if spin < 1 else 11), 0.0 if spin < 1 else 0.95)
        A.text(screen, "detail view" if spin < 1 else "spinning", 14, A.DIM, (c[0], c[1] + 128))
        sp = SPECS[KINDS[self.kind.index]]
        y = pv.bottom - 110
        stats = [("Max stability", f"{sp.max_stability:.0f}"), ("Spin loss / round", f"{sp.energy_loss:.0f}"),
                 ("Attack power", f"{sp.power:.2f}x"), ("Guard heals / Charge gives", f"{sp.guard_recovery:.0f} / {sp.charge_recovery:.0f}")]
        for i, (k, v) in enumerate(stats):
            col_x = pv.x + 30 + (i % 2) * (pv.w // 2)
            row_y = y + (i // 2) * 44
            A.text(screen, k, 15, A.MUTED, (col_x, row_y), anchor="topleft")
            A.text(screen, v, 20, A.WHITE, (col_x, row_y + 18), anchor="topleft", weight="bold")
