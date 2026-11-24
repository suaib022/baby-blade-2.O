"""UI kit: panels, gauges, focusable buttons/choices, menus and a touch joystick.

Every interactive widget works with mouse/touch, keyboard and gamepad. Menus keep one focused
widget; focus is drawn differently from hover (game-ui-ux skill).
"""

from __future__ import annotations

import math
from typing import Callable, List, Optional, Sequence, Tuple

import pygame

from babyblade.game import assets as A
from babyblade.game.audio import AUDIO

Color = Tuple[int, int, int]


def panel(surf: pygame.Surface, rect: pygame.Rect, accent: Optional[Color] = None, alpha: int = 200,
          radius: int = 14, title: str = "") -> None:
    s = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(s, A.PANEL + (alpha,), s.get_rect(), border_radius=radius)
    hl = pygame.Surface((rect.w, rect.h // 2), pygame.SRCALPHA)
    pygame.draw.rect(hl, (255, 255, 255, 10), hl.get_rect(), border_top_left_radius=radius, border_top_right_radius=radius)
    s.blit(hl, (0, 0))
    pygame.draw.rect(s, (accent or A.LINE) + (220,), s.get_rect(), width=2, border_radius=radius)
    surf.blit(s, rect.topleft)
    if title:
        A.text(surf, title.upper(), 15, accent or A.MUTED, (rect.x + 16, rect.y + 10), anchor="topleft", weight="bold")


def bar(surf: pygame.Surface, rect: pygame.Rect, frac: float, color: Color, segments: int = 0,
        back: Color = (8, 12, 24), flash: float = 0.0) -> None:
    frac = max(0.0, min(1.0, frac))
    pygame.draw.rect(surf, back, rect, border_radius=rect.h // 2)
    if frac > 0:
        fill = pygame.Rect(rect.x, rect.y, max(rect.h, int(rect.w * frac)), rect.h)
        top = A.mix(color, (255, 255, 255), 0.35 + 0.4 * flash)
        pygame.draw.rect(surf, color, fill, border_radius=rect.h // 2)
        pygame.draw.rect(surf, top, (fill.x + 3, fill.y + 2, max(0, fill.w - 6), max(1, rect.h // 3)), border_radius=rect.h // 3)
    if segments:
        for i in range(1, segments):
            x = rect.x + rect.w * i / segments
            pygame.draw.line(surf, back, (x, rect.y), (x, rect.bottom - 1), 2)
    pygame.draw.rect(surf, A.LINE, rect, width=1, border_radius=rect.h // 2)


def ring(surf: pygame.Surface, center: Tuple[int, int], radius: int, frac: float, color: Color, width: int = 5,
         back: Color = (24, 32, 54)) -> None:
    rect = pygame.Rect(center[0] - radius, center[1] - radius, radius * 2, radius * 2)
    pygame.draw.circle(surf, back, center, radius, width)
    if frac > 0.001:
        start = math.pi / 2 - 2 * math.pi * min(1.0, frac)
        pygame.draw.arc(surf, color, rect, start, math.pi / 2, width)


class Widget:
    rect: pygame.Rect
    enabled: bool = True
    focusable: bool = True

    def handle(self, event: pygame.event.Event) -> bool:
        return False

    def activate(self) -> None:
        pass

    def nudge(self, step: int) -> None:
        pass

    def update(self, dt: float) -> None:
        pass

    def draw(self, surf: pygame.Surface, focused: bool) -> None:
        pass


class Button(Widget):
    def __init__(self, rect, label: str, on_click: Optional[Callable[[], None]] = None, icon: Optional[str] = None,
                 sub: str = "", accent: Color = A.BLUE, key_hint: str = "", size: int = 22, enabled: bool = True) -> None:
        self.rect = pygame.Rect(rect)
        self.label, self.on_click, self.icon, self.sub = label, on_click, icon, sub
        self.accent, self.key_hint, self.size, self.enabled = accent, key_hint, size, enabled
        self.hover = False
        self.press = 0.0
        self.glow = 0.0

    def handle(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos):
            self.activate()
            return True
        return False

    def activate(self) -> None:
        if not self.enabled:
            AUDIO.play("dodge_fail", 0.4)
            return
        self.press = 1.0
        AUDIO.play("select")
        if self.on_click:
            self.on_click()

    def update(self, dt: float) -> None:
        self.press = max(0.0, self.press - dt * 5)

    def draw(self, surf: pygame.Surface, focused: bool) -> None:
        target = 1.0 if (focused or self.hover) and self.enabled else 0.0
        self.glow += (target - self.glow) * 0.25
        r = self.rect.inflate(int(-6 * self.press), int(-4 * self.press))
        base = A.mix(A.PANEL, self.accent, 0.10 + 0.22 * self.glow) if self.enabled else (12, 16, 28)
        s = pygame.Surface(r.size, pygame.SRCALPHA)
        pygame.draw.rect(s, base + (235,), s.get_rect(), border_radius=12)
        pygame.draw.rect(s, (255, 255, 255, 14), (0, 0, r.w, r.h // 2), border_top_left_radius=12, border_top_right_radius=12)
        border = A.mix(A.LINE, self.accent, self.glow) if self.enabled else (30, 38, 56)
        pygame.draw.rect(s, border + (255,), s.get_rect(), width=2, border_radius=12)
        surf.blit(s, r.topleft)
        if focused and self.enabled:
            pygame.draw.rect(surf, self.accent, r.inflate(8, 8), width=2, border_radius=15)
        col = A.WHITE if self.enabled else A.DIM
        x = r.x + 18
        if self.icon:
            A.draw_icon(surf, self.icon, (r.x + 30, r.centery), min(30, r.h * 0.5), self.accent if self.enabled else A.DIM)
            x = r.x + 56
        if self.sub:
            A.text(surf, self.label.upper(), self.size, col, (x, r.centery - 10), anchor="midleft", weight="bold")
            A.text(surf, self.sub, 14, A.MUTED if self.enabled else A.DIM, (x, r.centery + 14), anchor="midleft")
        else:
            anchor = "midleft" if self.icon else "center"
            pos = (x, r.centery) if self.icon else r.center
            A.text(surf, self.label.upper(), self.size, col, pos, anchor=anchor, weight="bold")
        if self.key_hint:
            A.text(surf, self.key_hint, 14, A.GOLD if self.enabled else A.DIM, (r.right - 12, r.centery), anchor="midright", weight="bold")


class Choice(Widget):
    """A labelled selector cycled with left/right (or by clicking its arrows)."""

    def __init__(self, rect, label: str, options: Sequence[str], index: int = 0,
                 on_change: Optional[Callable[[int], None]] = None, accent: Color = A.BLUE,
                 notes: Optional[Sequence[str]] = None) -> None:
        self.rect = pygame.Rect(rect)
        self.label, self.options, self.index = label, list(options), index
        self.on_change, self.accent, self.notes = on_change, accent, list(notes) if notes else None
        self.hover = False

    @property
    def value(self) -> str:
        return self.options[self.index]

    def nudge(self, step: int) -> None:
        self.index = (self.index + step) % len(self.options)
        AUDIO.play("tick")
        if self.on_change:
            self.on_change(self.index)

    def activate(self) -> None:
        self.nudge(1)

    def handle(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos):
            self.nudge(-1 if event.pos[0] < self.rect.centerx - self.rect.w * 0.15 else 1)
            return True
        return False

    def draw(self, surf: pygame.Surface, focused: bool) -> None:
        r = self.rect
        panel(surf, r, accent=self.accent if (focused or self.hover) else None, alpha=210, radius=12)
        A.text(surf, self.label.upper(), 14, A.MUTED, (r.x + 16, r.y + 8), anchor="topleft", weight="bold")
        vy = r.y + r.h * (0.36 if self.notes else 0.45)
        A.text(surf, self.value, 24, A.WHITE, (r.centerx + 30, vy), weight="bold")
        if self.notes:
            A.text(surf, self.notes[self.index], 14, A.MUTED, (r.centerx + 30, r.y + r.h * 0.70))
        for sgn in (-1, 1):
            cx = r.x + 150 if sgn < 0 else r.right - 24
            cy = r.y + r.h * (0.36 if self.notes else 0.45)
            col = self.accent if focused else A.DIM
            pygame.draw.polygon(surf, col, [(cx - 7 * sgn, cy - 9), (cx + 7 * sgn, cy), (cx - 7 * sgn, cy + 9)])
        dots_y = r.bottom - 7
        n = len(self.options)
        for i in range(n):
            x = r.x + 20 + i * 10
            pygame.draw.circle(surf, self.accent if i == self.index else A.LINE, (int(x), dots_y), 2)


class Menu:
    """A list of widgets with keyboard/gamepad focus and mouse hover."""

    def __init__(self, widgets: List[Widget], columns: int = 1) -> None:
        self.widgets = widgets
        self.focus = next((i for i, w in enumerate(widgets) if w.focusable and w.enabled), 0)
        self.columns = columns

    def move(self, dy: int, dx: int = 0) -> None:
        if not self.widgets:
            return
        if dx and isinstance(self.widgets[self.focus], Choice):
            self.widgets[self.focus].nudge(dx)
            return
        step = dy if dy else dx * (1 if self.columns == 1 else 1)
        if self.columns > 1 and dy:
            step = dy * self.columns
        n = len(self.widgets)
        i = self.focus
        for _ in range(n):
            i = (i + step) % n
            if self.widgets[i].focusable and self.widgets[i].enabled:
                self.focus = i
                AUDIO.play("tick", 0.6)
                return

    def handle(self, event: pygame.event.Event) -> None:
        for i, w in enumerate(self.widgets):
            if event.type == pygame.MOUSEMOTION and w.rect.collidepoint(event.pos) and w.focusable and w.enabled:
                if self.focus != i:
                    self.focus = i
            if w.handle(event):
                self.focus = i
                return

    def nav(self, cmd: str) -> None:
        if cmd == "up":
            self.move(-1)
        elif cmd == "down":
            self.move(1)
        elif cmd == "left":
            self.move(0, -1)
        elif cmd == "right":
            self.move(0, 1)
        elif cmd == "confirm" and self.widgets:
            self.widgets[self.focus].activate()

    def update(self, dt: float) -> None:
        for w in self.widgets:
            w.update(dt)

    def draw(self, surf: pygame.Surface) -> None:
        for i, w in enumerate(self.widgets):
            w.draw(surf, i == self.focus)


class Stick:
    """On-screen joystick for touch (also works with mouse drag)."""

    def __init__(self, center: Tuple[int, int], radius: int = 70) -> None:
        self.center = center
        self.radius = radius
        self.knob = center
        self.owner: Optional[object] = None  # finger id or "mouse"
        self.vec = (0.0, 0.0)

    def _set(self, pos: Tuple[float, float]) -> None:
        dx, dy = pos[0] - self.center[0], pos[1] - self.center[1]
        d = math.hypot(dx, dy)
        if d > self.radius:
            dx, dy = dx / d * self.radius, dy / d * self.radius
        self.knob = (self.center[0] + dx, self.center[1] + dy)
        self.vec = (dx / self.radius, dy / self.radius)

    def press(self, owner: object, pos: Tuple[float, float]) -> bool:
        if math.hypot(pos[0] - self.center[0], pos[1] - self.center[1]) <= self.radius * 1.4:
            self.owner = owner
            self._set(pos)
            return True
        return False

    def move(self, owner: object, pos: Tuple[float, float]) -> None:
        if self.owner == owner:
            self._set(pos)

    def release(self, owner: object) -> None:
        if self.owner == owner:
            self.owner = None
            self.knob = self.center
            self.vec = (0.0, 0.0)

    def draw(self, surf: pygame.Surface, active_hint: bool = True) -> None:
        base = pygame.Surface((self.radius * 2 + 8, self.radius * 2 + 8), pygame.SRCALPHA)
        c = (self.radius + 4, self.radius + 4)
        pygame.draw.circle(base, (14, 22, 42, 150), c, self.radius)
        pygame.draw.circle(base, A.LINE + (220,), c, self.radius, 2)
        for a in range(4):
            ang = a * math.pi / 2
            tip = (c[0] + math.cos(ang) * (self.radius - 14), c[1] + math.sin(ang) * (self.radius - 14))
            l = (tip[0] - math.cos(ang) * 10 + math.cos(ang + math.pi / 2) * 8, tip[1] - math.sin(ang) * 10 + math.sin(ang + math.pi / 2) * 8)
            rr = (tip[0] - math.cos(ang) * 10 - math.cos(ang + math.pi / 2) * 8, tip[1] - math.sin(ang) * 10 - math.sin(ang + math.pi / 2) * 8)
            pygame.draw.polygon(base, (130, 150, 190, 180), [tip, l, rr])
        surf.blit(base, (self.center[0] - c[0], self.center[1] - c[1]))
        pygame.draw.circle(surf, A.BLUE if self.owner else (60, 80, 120), (int(self.knob[0]), int(self.knob[1])), int(self.radius * 0.42))
        pygame.draw.circle(surf, A.BLUE_HI, (int(self.knob[0]), int(self.knob[1])), int(self.radius * 0.42), 2)
        if active_hint:
            A.text(surf, "STEER  ·  WASD / ARROWS / STICK", 12, A.MUTED, (self.center[0], self.center[1] + self.radius + 14))
