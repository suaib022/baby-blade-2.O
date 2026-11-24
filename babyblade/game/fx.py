"""Game-feel effects: sparks, shockwaves, trails, floating text, camera shake, hit-stop and
slow motion. Purely visual; the simulation never reads any of it."""

from __future__ import annotations

import math
import random
from typing import List, Optional, Tuple

import pygame

from babyblade.game import assets as A

Color = Tuple[int, int, int]


class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "color", "size", "drag", "kind")

    def __init__(self, x, y, vx, vy, life, color, size, drag=3.0, kind="spark"):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.life = self.max_life = life
        self.color, self.size, self.drag, self.kind = color, size, drag, kind


class Particles:
    """Additive particles: 'spark' streaks, 'ember' dots, 'shard' fragments."""

    def __init__(self, cap: int = 700) -> None:
        self.items: List[Particle] = []
        self.cap = cap
        self.rng = random.Random(7)

    def sparks(self, x: float, y: float, count: int, power: float = 1.0, color: Color = (255, 210, 120),
               direction: Optional[float] = None, spread: float = math.pi) -> None:
        for _ in range(count):
            a = (direction if direction is not None else 0.0) + self.rng.uniform(-spread, spread)
            sp = self.rng.uniform(160, 620) * power
            life = self.rng.uniform(0.18, 0.55)
            tint = self.rng.uniform(0.75, 1.0)
            c = (int(color[0] * tint), int(color[1] * tint), int(color[2] * tint))
            self.items.append(Particle(x, y, math.cos(a) * sp, math.sin(a) * sp, life, c, self.rng.uniform(1.5, 3.0), 4.5))
        self._trim()

    def embers(self, x: float, y: float, count: int, color: Color, speed: float = 60.0, life: float = 0.7) -> None:
        for _ in range(count):
            a = self.rng.uniform(0, 2 * math.pi)
            sp = self.rng.uniform(0.2, 1.0) * speed
            self.items.append(Particle(x, y, math.cos(a) * sp, math.sin(a) * sp, self.rng.uniform(0.4, 1.0) * life,
                                       color, self.rng.uniform(1.5, 3.5), 1.5, "ember"))
        self._trim()

    def inward(self, x: float, y: float, radius: float, count: int, color: Color) -> None:
        """Energy flowing into a charging top."""
        for _ in range(count):
            a = self.rng.uniform(0, 2 * math.pi)
            r = radius * self.rng.uniform(1.6, 2.4)
            px, py = x + math.cos(a) * r, y + math.sin(a) * r
            self.items.append(Particle(px, py, (x - px) * 2.6, (y - py) * 2.6, 0.38, color, 2.2, 0.5, "ember"))
        self._trim()

    def shards(self, x: float, y: float, count: int, color: Color) -> None:
        for _ in range(count):
            a = self.rng.uniform(0, 2 * math.pi)
            sp = self.rng.uniform(120, 420)
            self.items.append(Particle(x, y, math.cos(a) * sp, math.sin(a) * sp, self.rng.uniform(0.6, 1.3),
                                       color, self.rng.uniform(4, 9), 1.8, "shard"))
        self._trim()

    def _trim(self) -> None:
        if len(self.items) > self.cap:
            self.items = self.items[-self.cap:]

    def update(self, dt: float) -> None:
        keep = []
        for p in self.items:
            p.life -= dt
            if p.life <= 0:
                continue
            f = math.exp(-p.drag * dt)
            p.vx *= f
            p.vy *= f
            p.x += p.vx * dt
            p.y += p.vy * dt
            keep.append(p)
        self.items = keep

    def draw(self, surf: pygame.Surface, layer: pygame.Surface) -> None:
        """Draw onto an opaque black `layer` and add it to `surf` (true additive light)."""
        if not self.items:
            return
        layer.fill((0, 0, 0))
        for p in self.items:
            k = p.life / p.max_life
            c = (int(p.color[0] * k), int(p.color[1] * k), int(p.color[2] * k))
            if p.kind == "spark":
                ln = 0.022 * k
                pygame.draw.line(layer, c, (p.x, p.y), (p.x - p.vx * ln, p.y - p.vy * ln), max(1, int(p.size * k + 0.5)))
            elif p.kind == "shard":
                s = p.size * (0.5 + 0.5 * k)
                a = p.life * 9
                pts = [(p.x + math.cos(a + i * 2.1) * s, p.y + math.sin(a + i * 2.1) * s) for i in range(3)]
                pygame.draw.polygon(layer, c, pts)
            else:
                pygame.draw.circle(layer, c, (int(p.x), int(p.y)), max(1, int(p.size * (0.4 + 0.6 * k))))
        surf.blit(layer, (0, 0), special_flags=pygame.BLEND_ADD)


class Shockwaves:
    def __init__(self) -> None:
        self.items: List[list] = []  # [x, y, t, dur, max_r, color, width]

    def add(self, x: float, y: float, max_r: float, color: Color, dur: float = 0.35, width: int = 4) -> None:
        self.items.append([x, y, 0.0, dur, max_r, color, width])

    def update(self, dt: float) -> None:
        for it in self.items:
            it[2] += dt
        self.items = [it for it in self.items if it[2] < it[3]]

    def draw(self, layer: pygame.Surface) -> None:
        for x, y, t, dur, max_r, color, width in self.items:
            k = t / dur
            r = int(6 + max_r * (1 - (1 - k) ** 3))
            fade = 1 - k
            c = (int(color[0] * fade), int(color[1] * fade), int(color[2] * fade))
            pygame.draw.circle(layer, c, (int(x), int(y)), r, max(1, int(width * fade + 1)))


class Trails:
    """Glowing ribbon behind each top."""

    def __init__(self, length: int = 22) -> None:
        self.pts = {1: [], 2: []}
        self.length = length

    def push(self, player: int, pos: Tuple[float, float]) -> None:
        pts = self.pts[player]
        pts.append(pos)
        if len(pts) > self.length:
            del pts[0]

    def clear(self) -> None:
        self.pts = {1: [], 2: []}

    def draw(self, layer: pygame.Surface, player: int, color: Color, width: float) -> None:
        pts = self.pts[player]
        n = len(pts)
        for i in range(1, n):
            k = i / n
            c = (int(color[0] * k * 0.8), int(color[1] * k * 0.8), int(color[2] * k * 0.8))
            pygame.draw.line(layer, c, pts[i - 1], pts[i], max(1, int(width * k)))


class FloatTexts:
    def __init__(self) -> None:
        self.items: List[list] = []  # [text, x, y, t, dur, color, size]

    def add(self, s: str, x: float, y: float, color: Color, size: int = 26, dur: float = 0.9) -> None:
        self.items.append([s, x, y, 0.0, dur, color, size])

    def update(self, dt: float) -> None:
        for it in self.items:
            it[3] += dt
            it[2] -= 42 * dt
        self.items = [it for it in self.items if it[3] < it[4]]

    def draw(self, surf: pygame.Surface) -> None:
        for s, x, y, t, dur, color, size in self.items:
            k = t / dur
            pop = 1.0 + 0.5 * max(0.0, 1 - t / 0.12)
            alpha = int(255 * (1 - max(0.0, k - 0.6) / 0.4))
            A.text(surf, s, int(size * pop), color, (x, y), weight="bold", shadow=True, alpha=alpha)


class Camera:
    """Screen shake, hit-stop (freeze), slow motion and zoom."""

    def __init__(self) -> None:
        self.shake = 0.0
        self.hitstop = 0.0
        self.slowmo = 0.0
        self.slowmo_scale = 0.25
        self.zoom = 1.0
        self.zoom_target = 1.0
        self.focus = (A.W / 2, A.H / 2)
        self.focus_target = (A.W / 2, A.H / 2)
        self.enabled_shake = True
        self.rng = random.Random(11)

    def kick(self, amount: float) -> None:
        if self.enabled_shake:
            self.shake = min(22.0, self.shake + amount)

    def freeze(self, seconds: float) -> None:
        self.hitstop = max(self.hitstop, seconds)

    def slow(self, seconds: float, scale: float = 0.25) -> None:
        self.slowmo = max(self.slowmo, seconds)
        self.slowmo_scale = scale

    def time_scale(self) -> float:
        if self.hitstop > 0:
            return 0.0
        if self.slowmo > 0:
            return self.slowmo_scale
        return 1.0

    def update(self, real_dt: float) -> None:
        self.hitstop = max(0.0, self.hitstop - real_dt)
        self.slowmo = max(0.0, self.slowmo - real_dt)
        self.shake *= math.exp(-10.0 * real_dt)
        if self.shake < 0.1:
            self.shake = 0.0
        k = 1 - math.exp(-5.0 * real_dt)
        self.zoom += (self.zoom_target - self.zoom) * k
        fx, fy = self.focus
        tx, ty = self.focus_target
        self.focus = (fx + (tx - fx) * k, fy + (ty - fy) * k)

    def offset(self) -> Tuple[int, int]:
        if self.shake <= 0:
            return (0, 0)
        return (int(self.rng.uniform(-1, 1) * self.shake), int(self.rng.uniform(-1, 1) * self.shake))

    def present(self, world: pygame.Surface, screen: pygame.Surface) -> None:
        ox, oy = self.offset()
        if self.zoom > 1.01:
            w, h = world.get_size()
            cw, ch = int(w / self.zoom), int(h / self.zoom)
            fx, fy = self.focus
            x = int(min(max(0, fx - cw / 2), w - cw))
            y = int(min(max(0, fy - ch / 2), h - ch))
            sub = world.subsurface((x, y, cw, ch))
            screen.blit(pygame.transform.smoothscale(sub, (w, h)), (ox, oy))
        else:
            screen.blit(world, (ox, oy))


class Banner:
    """Big animated announcement (round start, finish)."""

    def __init__(self) -> None:
        self.text = ""
        self.sub = ""
        self.color = A.WHITE
        self.glow = A.BLUE
        self.t = 0.0
        self.dur = 0.0

    def show(self, text: str, color=A.WHITE, glow=A.BLUE, dur: float = 1.4, sub: str = "") -> None:
        self.text, self.sub, self.color, self.glow, self.t, self.dur = text, sub, color, glow, 0.0, dur

    @property
    def active(self) -> bool:
        return self.t < self.dur and bool(self.text)

    def update(self, dt: float) -> None:
        self.t += dt

    def draw(self, surf: pygame.Surface, y: float = A.H * 0.36) -> None:
        if not self.active:
            return
        k_in = min(1.0, self.t / 0.18)
        k_out = min(1.0, max(0.0, (self.dur - self.t) / 0.25))
        alpha = int(255 * min(k_in, k_out))
        scale = 1.6 - 0.6 * (1 - (1 - k_in) ** 3)
        band = pygame.Surface((A.W, 130), pygame.SRCALPHA)
        band.fill((0, 0, 0, int(120 * min(k_in, k_out))))
        surf.blit(band, (0, int(y - 70)))
        A.glow_text(surf, self.text, 84, self.color, self.glow, (A.W / 2, y), alpha=alpha, strength=3, scale=scale)
        if self.sub:
            A.text(surf, self.sub, 24, A.MUTED, (A.W / 2, y + 52), alpha=alpha)
