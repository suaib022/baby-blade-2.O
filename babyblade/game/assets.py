"""Procedural art: palette, fonts, stage, stadium bowls, Beyblade sprites and action icons.

Everything is drawn in code at start-up (no image files), supersampled 3x and smoothed down
for clean edges. Beyblade sprites are pre-rotated into a frame cache, plus a radial-blur disc
used when the top spins fast, which is what makes a real spinning top read as "fast".
"""

from __future__ import annotations

import math
import os
import random
from functools import lru_cache
from typing import Dict, List, Optional, Sequence, Tuple

import pygame

Color = Tuple[int, int, int]

W, H = 1280, 720

# ---- palette (from the deck: deep navy, neon blue for P1, neon red for P2) -------------------
BG = (5, 8, 18)
NAVY = (10, 16, 32)
PANEL = (14, 22, 42)
PANEL_HI = (24, 36, 66)
LINE = (44, 62, 104)
WHITE = (240, 244, 252)
MUTED = (130, 146, 178)
DIM = (78, 92, 122)
BLUE = (40, 140, 255)
BLUE_HI = (140, 205, 255)
RED = (255, 64, 52)
RED_HI = (255, 170, 150)
GOLD = (255, 196, 64)
GREEN = (80, 230, 150)
ORANGE = (255, 130, 40)
PURPLE = (170, 110, 255)
CYAN = (90, 230, 255)

PLAYER_COLORS = {1: (BLUE, BLUE_HI), 2: (RED, RED_HI)}

_FONT_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "fonts")
_FONT_FILES = {"bold": "Oswald-Bold.ttf", "semi": "Oswald-SemiBold.ttf", "regular": "Oswald-Regular.ttf"}
_fonts: Dict[Tuple[int, str], pygame.font.Font] = {}


def font(size: int, weight: str = "semi") -> pygame.font.Font:
    key = (size, weight)
    if not pygame.font.get_init():
        pygame.font.init()
    f = _fonts.get(key)
    if f is not None:
        try:
            f.size("A")  # a font from an earlier pygame session is no longer valid
        except Exception:
            _fonts.clear()
            _text_cache.clear()
            _glow_parts.cache_clear()
            f = None
    if f is None:
        try:
            f = pygame.font.Font(os.path.join(_FONT_DIR, _FONT_FILES[weight]), size)
        except Exception:
            f = pygame.font.Font(None, int(size * 1.3))
        _fonts[key] = f
    return f


_text_cache: Dict[Tuple, pygame.Surface] = {}


def _render(s: str, size: int, color: Color, weight: str) -> pygame.Surface:
    key = (s, size, tuple(color), weight)
    img = _text_cache.get(key)
    if img is None:
        if len(_text_cache) > 600:
            _text_cache.clear()
        img = font(size, weight).render(s, True, color)
        _text_cache[key] = img
    return img


def text(surf: pygame.Surface, s: str, size: int, color: Color, pos: Tuple[float, float],
         anchor: str = "center", weight: str = "semi", shadow: bool = False, alpha: int = 255) -> pygame.Rect:
    img = _render(s, size, color, weight)
    rect = img.get_rect(**{anchor: (int(pos[0]), int(pos[1]))})
    if shadow:
        sh = _render(s, size, (0, 0, 0), weight).copy()
        sh.set_alpha(int(150 * alpha / 255))
        surf.blit(sh, rect.move(2, 3))
    if alpha < 255:
        img = img.copy()  # never fade the cached image itself
        img.set_alpha(alpha)
    surf.blit(img, rect)
    return rect


@lru_cache(maxsize=96)
def _glow_parts(s: str, size: int, color: Color, glow_c: Color, weight: str, strength: int):
    letters = font(size, weight).render(s, True, glow_c)
    base = pygame.Surface(letters.get_size())
    base.blit(letters, (0, 0))
    g = blur(base, strength * 2)
    return g, font(size, weight).render(s, True, color)


def glow_text(surf: pygame.Surface, s: str, size: int, color: Color, glow: Color, pos, anchor="center",
              weight="bold", strength: int = 3, alpha: int = 255, scale: float = 1.0) -> pygame.Rect:
    """Text with an additive neon halo. Halo and text are cached; scale/alpha are cheap."""
    g, img = _glow_parts(s, size, tuple(color), tuple(glow), weight, strength)
    if scale != 1.0:
        g = pygame.transform.smoothscale(g, (max(1, int(g.get_width() * scale)), max(1, int(g.get_height() * scale))))
        img = pygame.transform.smoothscale(img, (max(1, int(img.get_width() * scale)), max(1, int(img.get_height() * scale))))
    rect = img.get_rect(**{anchor: (int(pos[0]), int(pos[1]))})
    if alpha < 255:
        g = g.copy()
        g.fill((alpha, alpha, alpha), special_flags=pygame.BLEND_MULT)
        img = img.copy()
        img.set_alpha(alpha)
    surf.blit(g, g.get_rect(center=rect.center), special_flags=pygame.BLEND_ADD)
    surf.blit(img, rect)
    return rect


# ---- generic helpers ------------------------------------------------------------------------------

def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def mix(c1: Sequence[int], c2: Sequence[int], t: float) -> Color:
    return (int(lerp(c1[0], c2[0], t)), int(lerp(c1[1], c2[1], t)), int(lerp(c1[2], c2[2], t)))


def shade(c: Sequence[int], k: float) -> Color:
    return (max(0, min(255, int(c[0] * k))), max(0, min(255, int(c[1] * k))), max(0, min(255, int(c[2] * k))))


def blur(surf: pygame.Surface, radius: int) -> pygame.Surface:
    """Gaussian blur with a smoothscale fallback (the fallback also works in the browser)."""
    radius = max(1, int(radius))
    pad = radius * 3
    flags = pygame.SRCALPHA if surf.get_flags() & pygame.SRCALPHA else 0
    big = pygame.Surface((surf.get_width() + pad * 2, surf.get_height() + pad * 2), flags)
    big.blit(surf, (pad, pad))
    try:
        return pygame.transform.gaussian_blur(big, radius)
    except Exception:
        w, h = big.get_size()
        k = max(2, radius)
        small = pygame.transform.smoothscale(big, (max(1, w // k), max(1, h // k)))
        return pygame.transform.smoothscale(small, (w, h))


@lru_cache(maxsize=128)
def glow(radius: int, color: Color, strength: float = 1.0) -> pygame.Surface:
    """Soft radial glow, blit with BLEND_ADD."""
    radius = max(2, radius)
    s = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    for r in range(radius, 0, -1):
        t = 1.0 - r / radius
        k = (t ** 2.2) * strength
        pygame.draw.circle(s, (min(255, int(color[0] * k)), min(255, int(color[1] * k)), min(255, int(color[2] * k)), 255), (radius, radius), r)
    return s


def supersample(draw_fn, size: Tuple[int, int], scale: int = 3) -> pygame.Surface:
    big = pygame.Surface((size[0] * scale, size[1] * scale), pygame.SRCALPHA)
    draw_fn(big, scale)
    return pygame.transform.smoothscale(big, size)


# ---- stage background -----------------------------------------------------------------------------

@lru_cache(maxsize=4)
def stage_background(w: int = W, h: int = H, seed: int = 4) -> pygame.Surface:
    """Dark arena with blurred blue/red stadium lights (the deck's key art, drawn in code).

    Lights are drawn at quarter resolution and smooth-scaled up, which blurs them cheaply
    (important for the browser build, where Python runs several times slower).
    """
    rng = random.Random(seed)
    surf = pygame.Surface((w, h))
    for y in range(0, h, 2):
        t = y / h
        surf.fill(mix((12, 18, 38), (3, 5, 12), t ** 0.8), (0, y, w, 2))
    q = 4
    lw, lh = w // q, h // q
    lights = pygame.Surface((lw, lh))
    for i in range(18):  # LED panels along the top: blue left, red right
        x = (i + 0.5) / 18 * lw
        col = BLUE if x < lw / 2 else RED
        pygame.draw.rect(lights, shade(col, 0.95), (x - 6, 6 + int(2.5 * math.sin(i)), 13, 2))
    for _ in range(170):  # crowd bokeh
        x = rng.uniform(0, lw)
        y = rng.uniform(12, lh * 0.42)
        col = BLUE if (x < lw / 2) ^ (rng.random() < 0.15) else RED
        pygame.draw.circle(lights, shade(col, rng.randint(30, 110) / 255.0), (int(x), int(y)), rng.randint(1, 2))
    for i, col in ((0, BLUE), (1, RED)):  # haze beams
        x = lw * (0.18 if i == 0 else 0.82)
        pygame.draw.polygon(lights, shade(col, 0.07), [(x - 8, 0), (x + 8, 0), (lw * 0.5 + (i * 2 - 1) * 15, lh), (lw * 0.5 + (i * 2 - 1) * 70, lh)])
    tmp = pygame.transform.smoothscale(lights, (lw // 2, lh // 2))
    big = pygame.transform.smoothscale(pygame.transform.smoothscale(tmp, (lw, lh)), (w, h))
    soft = pygame.transform.smoothscale(pygame.transform.smoothscale(lights, (lw * 2, lh * 2)), (w, h))
    surf.blit(big, (0, 0), special_flags=pygame.BLEND_ADD)
    surf.blit(big, (0, 0), special_flags=pygame.BLEND_ADD)
    soft.fill((150, 150, 150), special_flags=pygame.BLEND_MULT)
    surf.blit(soft, (0, 0), special_flags=pygame.BLEND_ADD)
    vig = pygame.Surface((w, h), pygame.SRCALPHA)
    for i in range(0, 60, 2):
        a = int(150 * (i / 60) ** 2.5)
        pygame.draw.rect(vig, (0, 0, 0, a), (59 - i, 59 - i, w - 2 * (59 - i), h - 2 * (59 - i)), width=3)
    surf.blit(vig, (0, 0))
    return surf


# ---- stadium bowl ---------------------------------------------------------------------------------

STADIUM_LOOK = {
    "CLASSIC": {"floor": (18, 26, 46), "floor_hi": (62, 84, 128), "groove": (120, 150, 210), "bezel": (40, 46, 62)},
    "ICE": {"floor": (16, 44, 70), "floor_hi": (96, 170, 210), "groove": (190, 240, 255), "bezel": (44, 60, 76)},
    "STEEP": {"floor": (40, 22, 22), "floor_hi": (130, 76, 56), "groove": (230, 150, 100), "bezel": (60, 44, 40)},
}


@lru_cache(maxsize=6)
def stadium_bowl(kind: str, radius_px: int) -> pygame.Surface:
    """Pre-rendered bowl: steel bezel with bolts, lit floor with grooves and a centre emblem."""
    look = STADIUM_LOOK[kind]
    bezel = 26
    size = (radius_px + bezel + 8) * 2
    c = size // 2

    def draw(s: pygame.Surface, k: int) -> None:
        R = radius_px * k
        cc = c * k
        bz = bezel * k
        # Bezel: dark steel ring with a bevel.
        pygame.draw.circle(s, shade(look["bezel"], 0.6), (cc, cc), R + bz)
        for i in range(bz, 0, -1):
            t = i / bz
            pygame.draw.circle(s, shade(look["bezel"], 0.7 + 0.8 * (1 - abs(t - 0.5) * 2)), (cc, cc), R + i, width=1 * k)
        for i in range(24):  # bolts
            a = 2 * math.pi * i / 24
            bx, by = cc + math.cos(a) * (R + bz * 0.55), cc + math.sin(a) * (R + bz * 0.55)
            pygame.draw.circle(s, (120, 130, 150), (int(bx), int(by)), 3 * k)
            pygame.draw.circle(s, (30, 34, 44), (int(bx), int(by)), 3 * k, width=k)
        # Floor: bowl lighting (bright upper-left, dark rim).
        for r in range(R, 0, -2 * k):
            t = r / R
            col = mix(look["floor_hi"], look["floor"], t ** 0.7)
            off = (1 - t) * R * 0.18
            pygame.draw.circle(s, col, (int(cc - off), int(cc - off)), r)
        # Clip any spill past the rim, then a dark rim shadow.
        mask = pygame.Surface(s.get_size(), pygame.SRCALPHA)
        pygame.draw.circle(mask, (255, 255, 255, 255), (cc, cc), R + bz)
        s.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        for i in range(18 * k):
            a = int(140 * (1 - i / (18 * k)) ** 2)
            pygame.draw.circle(s, (0, 0, 0, a), (cc, cc), R - i, width=1)
        # Concentric grooves and radial spokes.
        groove = look["groove"]
        for frac in (0.25, 0.5, 0.75):
            pygame.draw.circle(s, groove + (40,), (cc, cc), int(R * frac), width=k)
        for i in range(12):
            a = 2 * math.pi * i / 12
            pygame.draw.line(s, groove + (22,), (cc + math.cos(a) * R * 0.28, cc + math.sin(a) * R * 0.28),
                             (cc + math.cos(a) * R * 0.95, cc + math.sin(a) * R * 0.95), width=k)
        if kind == "ICE":
            rng = random.Random(3)
            for _ in range(40):
                a = rng.uniform(0, 2 * math.pi)
                r0 = rng.uniform(0.1, 0.9) * R
                ln = rng.uniform(0.05, 0.18) * R
                pygame.draw.line(s, (230, 250, 255, 60), (cc + math.cos(a) * r0, cc + math.sin(a) * r0),
                                 (cc + math.cos(a + 0.2) * (r0 + ln), cc + math.sin(a + 0.2) * (r0 + ln)), width=k)
        if kind == "STEEP":
            for frac in (0.15, 0.32, 0.5, 0.66, 0.82):
                pygame.draw.circle(s, (0, 0, 0, 50), (cc, cc), int(R * frac), width=3 * k)
        # Centre emblem: a split blue/red ring.
        er = int(R * 0.13)
        pygame.draw.arc(s, BLUE + (120,), (cc - er, cc - er, er * 2, er * 2), math.pi / 2, math.pi * 1.5, 3 * k)
        pygame.draw.arc(s, RED + (120,), (cc - er, cc - er, er * 2, er * 2), -math.pi / 2, math.pi / 2, 3 * k)

    return supersample(draw, (size, size), 2)


# ---- Beyblade sprites -----------------------------------------------------------------------------

BLADE_SHAPES = ("Dragon", "Storm", "Fortress", "Phantom")


def _blade_outline(shape: str, cx: float, cy: float, R: float) -> List[Tuple[float, float]]:
    """Outer contour of the attack ring for one shape (angle 0 = right)."""
    pts: List[Tuple[float, float]] = []
    n = 240
    for i in range(n):
        a = 2 * math.pi * i / n
        if shape == "Dragon":  # three hooked claws
            ph = (a * 3) % (2 * math.pi)
            r = R * (0.80 + 0.20 * max(0.0, math.sin(ph)) ** 0.6 - 0.08 * max(0.0, -math.sin(ph * 1.0)))
        elif shape == "Storm":  # six sharp spikes
            ph = (a * 6) % (2 * math.pi)
            r = R * (0.84 + 0.16 * (1 - ph / (2 * math.pi)) ** 1.5)
        elif shape == "Fortress":  # round with eight bumps
            r = R * (0.93 + 0.07 * math.cos(a * 8))
        else:  # Phantom: four crescent blades
            ph = (a * 4) % (2 * math.pi)
            r = R * (0.78 + 0.22 * (math.sin(ph / 2) ** 4))
        pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
    return pts


class TopArt:
    """Pre-rendered Beyblade: sharp rotation frames, a spin-blur disc and a fixed hub."""

    FRAMES = 60

    def __init__(self, radius_px: int, ring: Color, shape: str = "Dragon", claws: int = 3,
                 disk: Color = (150, 160, 180), bit: Color = (120, 230, 175)) -> None:
        self.radius = radius_px
        self.ring = ring
        size = radius_px * 2 + 6
        k = 3 if radius_px <= 60 else 2
        self._k = k
        R = radius_px * k
        big = pygame.Surface((size * k, size * k), pygame.SRCALPHA)
        c = size * k / 2
        ring_dark = shade(ring, 0.45)
        ring_hi = mix(ring, (255, 255, 255), 0.55)
        # Attack ring (outer contour) with metallic shading.
        outline = _blade_outline(shape, c, c, R)
        pygame.draw.polygon(big, ring_dark, outline)
        inner = _blade_outline(shape, c, c, R * 0.9)
        pygame.draw.polygon(big, ring, inner)
        pygame.draw.polygon(big, ring_hi, outline, width=2 * k)
        # Ratchet: dark metal ring with teeth.
        rr = R * 0.66
        pygame.draw.circle(big, (36, 40, 52), (c, c), rr)
        for i in range(max(2, claws) * 2):
            a = math.pi * i / max(2, claws)
            pts = [(c + math.cos(a - 0.18) * rr * 0.75, c + math.sin(a - 0.18) * rr * 0.75),
                   (c + math.cos(a) * rr * 1.08, c + math.sin(a) * rr * 1.08),
                   (c + math.cos(a + 0.18) * rr * 0.75, c + math.sin(a + 0.18) * rr * 0.75)]
            pygame.draw.polygon(big, (70, 76, 92) if i % 2 else ring_hi, pts)
        # Weight disk: metallic gradient with screws.
        dr = R * 0.5
        for r in range(int(dr), 0, -k):
            t = r / dr
            pygame.draw.circle(big, mix(mix(disk, (255, 255, 255), 0.35), shade(disk, 0.5), t), (c - (1 - t) * dr * 0.2, c - (1 - t) * dr * 0.2), r)
        for i in range(max(2, claws)):
            a = 2 * math.pi * i / max(2, claws) + 0.5
            sx, sy = c + math.cos(a) * dr * 0.66, c + math.sin(a) * dr * 0.66
            pygame.draw.circle(big, (40, 44, 56), (sx, sy), 3 * k)
            pygame.draw.circle(big, (190, 200, 215), (sx, sy), 3 * k, width=k)
        # Accent stripes in the player colour (they make the rotation readable).
        for i in range(max(2, claws)):
            a = 2 * math.pi * i / max(2, claws)
            pygame.draw.line(big, ring_hi, (c + math.cos(a) * dr * 0.2, c + math.sin(a) * dr * 0.2),
                             (c + math.cos(a + 0.35) * R * 0.86, c + math.sin(a + 0.35) * R * 0.86), width=3 * k)
        for i in range(max(2, claws)):  # bright tip markers: the turn is readable at any speed
            a = 2 * math.pi * i / max(2, claws)
            tx, ty = c + math.cos(a) * R * 0.9, c + math.sin(a) * R * 0.9
            pygame.draw.circle(big, (255, 255, 255), (tx, ty), 5 * k)
            pygame.draw.circle(big, ring, (tx, ty), 3 * k)
        # One asymmetric gold pointer on the rim: it breaks every shape's symmetry, so rotation is
        # visible on all blades, including round or 4-fold shapes that look the same each quarter turn.
        pa = 0.0
        tri_pts = [(c + math.cos(pa) * R * 1.01, c + math.sin(pa) * R * 1.01),
                   (c + math.cos(pa + 0.2) * R * 0.7, c + math.sin(pa + 0.2) * R * 0.7),
                   (c + math.cos(pa - 0.2) * R * 0.7, c + math.sin(pa - 0.2) * R * 0.7)]
        pygame.draw.polygon(big, (255, 226, 90), tri_pts)
        pygame.draw.polygon(big, (60, 40, 0), tri_pts, width=max(1, k))
        master = big
        self._master = master
        self.frames: Dict[int, pygame.Surface] = {}
        frame0 = self._frame(0)
        # Spin blur: many rotations layered; shows the colour bands a fast top really shows.
        self.blur = pygame.Surface(frame0.get_size(), pygame.SRCALPHA)
        steps = 24
        for i in range(steps):
            fr = pygame.transform.rotozoom(master, -360.0 * i / steps, 1.0 / k)
            fr.set_alpha(int(255 * 4.0 / steps) + 8)
            self.blur.blit(fr, fr.get_rect(center=self.blur.get_rect().center))
        # Hub (bit) drawn crisp on top: it barely moves while the body spins.
        hs = int(radius_px * 0.5) * 2 + 4

        def hub(s: pygame.Surface, kk: int) -> None:
            cc = s.get_width() / 2
            hr = radius_px * 0.22 * kk
            pygame.draw.circle(s, (20, 22, 30), (cc, cc), hr * 1.35)
            pygame.draw.circle(s, shade(bit, 0.6), (cc, cc), hr)
            pygame.draw.circle(s, bit, (cc - hr * 0.12, cc - hr * 0.12), hr * 0.78)
            pygame.draw.circle(s, (255, 255, 255, 220), (cc - hr * 0.35, cc - hr * 0.4), hr * 0.22)
        self.hub = supersample(hub, (hs, hs), 3)
        # Fixed specular highlight and rim light (light from the upper left).
        sp = pygame.Surface(frame0.get_size(), pygame.SRCALPHA)
        sc = sp.get_width() / 2
        pygame.draw.ellipse(sp, (255, 255, 255, 46), (sc - radius_px * 0.75, sc - radius_px * 0.85, radius_px * 0.95, radius_px * 0.6))
        pygame.draw.arc(sp, (255, 255, 255, 90), (sc - radius_px, sc - radius_px, radius_px * 2, radius_px * 2), math.pi * 0.55, math.pi * 1.05, 2)
        self.spec = sp

    def _frame(self, idx: int) -> pygame.Surface:
        f = self.frames.get(idx)
        if f is None:  # rotation frames are built lazily on first use
            f = pygame.transform.rotozoom(self._master, -360.0 * idx / self.FRAMES, 1.0 / self._k)
            self.frames[idx] = f
        return f

    def draw(self, surf: pygame.Surface, pos: Tuple[float, float], angle: float, spin01: float,
             alpha: int = 255, squash: float = 1.0, sweep: float = 0.0) -> None:
        """Draw the top. spin01 (0..1) blends from crisp detail to a fast-spin blur."""
        idx = int((angle % (2 * math.pi)) / (2 * math.pi) * self.FRAMES) % self.FRAMES
        frame = self._frame(idx)
        spin = min(1.0, max(0.0, spin01))
        layers = []
        if spin > 0.05:
            if sweep > 0.0:
                # Exposure-style motion blur: ghost copies spread across the angle swept this frame,
                # so a fast turn draws a smooth arc (pointer, tips and claws) rather than strobing.
                total = min(sweep, 2.0) / (2 * math.pi) * self.FRAMES
                n = 9
                lags = [(total * k / n, int((30 + 120 * (1 - k / n)) * spin)) for k in range(n, 0, -1)]
            else:
                lags = [(18, int(45 * spin)), (12, int(80 * spin)), (6, int(130 * spin))]
            for lag, a_ in lags:
                layers.append((self._frame(int(idx - lag) % self.FRAMES), a_))
        layers.append((frame, int(255 - 50 * spin) if sweep > 0.0 else 255))
        for img, a in layers:
            if squash != 1.0:
                img = pygame.transform.smoothscale(img, (img.get_width(), max(1, int(img.get_height() * squash))))
            img.set_alpha(int(a * alpha / 255))
            surf.blit(img, img.get_rect(center=(int(pos[0]), int(pos[1]))))
            img.set_alpha(255)
        hub = self.hub
        hub.set_alpha(alpha)
        surf.blit(hub, hub.get_rect(center=(int(pos[0]), int(pos[1]))))
        hub.set_alpha(255)
        if alpha > 200:
            surf.blit(self.spec, self.spec.get_rect(center=(int(pos[0]), int(pos[1]))))


# ---- action icons -----------------------------------------------------------------------------------

def draw_icon(surf: pygame.Surface, name: str, center: Tuple[float, float], size: float, color: Color) -> None:
    cx, cy = center
    s = size / 2

    def P(x, y):
        return (cx + x * s, cy + y * s)

    if name == "CHARGE":  # lightning bolt
        pygame.draw.polygon(surf, color, [P(0.15, -1), P(-0.55, 0.12), P(-0.05, 0.12), P(-0.25, 1), P(0.55, -0.2), P(0.05, -0.2), P(0.35, -1)])
    elif name == "ATTACK":  # double chevron
        for off in (-0.45, 0.15):
            pygame.draw.polygon(surf, color, [P(off - 0.2, -0.85), P(off + 0.45, 0), P(off - 0.2, 0.85), P(off - 0.5, 0.85), P(off + 0.12, 0), P(off - 0.5, -0.85)])
    elif name == "GUARD":  # shield
        pts = [P(0, -0.95), P(0.8, -0.6), P(0.7, 0.25), P(0, 0.98), P(-0.7, 0.25), P(-0.8, -0.6)]
        pygame.draw.polygon(surf, color, pts)
        pygame.draw.polygon(surf, (0, 0, 0), [P(0, -0.6), P(0.45, -0.38), P(0.4, 0.15), P(0, 0.62), P(-0.4, 0.15), P(-0.45, -0.38)], width=max(1, int(s * 0.12)))
    elif name == "DODGE":  # side-step arrows
        pygame.draw.polygon(surf, color, [P(-1, -0.25), P(-0.35, -0.85), P(-0.35, -0.5), P(0.4, -0.5), P(0.4, 0.0), P(-0.35, 0.0), P(-0.35, 0.35)])
        pygame.draw.polygon(surf, color, [P(1, 0.35), P(0.35, -0.25), P(0.35, 0.1), P(-0.4, 0.1), P(-0.4, 0.6), P(0.35, 0.6), P(0.35, 0.95)])
    elif name == "SPECIAL":  # star burst
        pts = []
        for i in range(16):
            a = -math.pi / 2 + math.pi * i / 8
            r = 1.0 if i % 2 == 0 else 0.45
            pts.append(P(math.cos(a) * r, math.sin(a) * r))
        pygame.draw.polygon(surf, color, pts)
    elif name == "PAUSE":
        pygame.draw.rect(surf, color, (*P(-0.6, -0.8), s * 0.45, s * 1.6), border_radius=2)
        pygame.draw.rect(surf, color, (*P(0.15, -0.8), s * 0.45, s * 1.6), border_radius=2)
    elif name == "PLAY":
        pygame.draw.polygon(surf, color, [P(-0.6, -0.85), P(0.8, 0), P(-0.6, 0.85)])
