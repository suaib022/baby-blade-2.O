"""Draws a Battle and turns its events into effects and sound.

Rendering: stage → stadium bowl → (light pass 1: LED rim, under-glows, trails) → tops →
(light pass 2: auras, sparks, shockwaves) → floating text. Light passes are drawn on an opaque
black layer covering only the stadium and added on top, which is both correct additive light
and cheap enough for the browser build.
"""

from __future__ import annotations

import math
from typing import Dict, Optional, Tuple

import pygame

from babyblade import config as C
from babyblade.game import assets as A
from babyblade.game.audio import AUDIO
from babyblade.game.fx import Banner, Camera, FloatTexts, Particles, Shockwaves, Trails
from babyblade.game.profile import Look, art_for
from babyblade.sim.actions import Action, LABEL
from babyblade.sim.battle import Battle
from babyblade.sim.blades import StadiumType

CX, CY = 640, 372
PPU = 23.0
BOWL_PX = int(C.STADIUM_START_RADIUS * PPU)
TOP_PX = int(round(C.BLADE_RADIUS * PPU))
LAYER_HALF = BOWL_PX + 44

FINISH_TEXT = {
    "RING_OUT": ("RING OUT!", A.GOLD),
    "BURST": ("BURST FINISH!", A.RED),
    "SPIN_OUT": ("SPIN FINISH!", A.CYAN),
    "DRAW": ("DRAW!", A.WHITE),
    "POINTS": ("TIME UP!", A.GOLD),
}


class _Silent:
    """Audio stand-in for background demos."""

    def __getattr__(self, name):
        return lambda *a, **k: None


def to_screen(x: float, y: float) -> Tuple[float, float]:
    return (CX + x * PPU, CY + y * PPU)


class ArenaView:
    def __init__(self, battle: Battle, looks: Tuple[Look, Look], tags: Tuple[str, str], silent: bool = False) -> None:
        self.audio = _Silent() if silent else AUDIO
        self.battle = battle
        self.looks = looks
        self.tags = tags
        self.arts = (art_for(looks[0], TOP_PX), art_for(looks[1], TOP_PX))
        self.colors = (looks[0].color, looks[1].color)
        self.bowl = A.stadium_bowl(battle.stadium.value, BOWL_PX)
        self.light = pygame.Surface((LAYER_HALF * 2, LAYER_HALF * 2))
        self.particles = Particles()
        self.waves = Shockwaves()
        self.trails = Trails()
        self.floats = FloatTexts()
        self.banner = Banner()
        self.camera = Camera()
        self.angles = [0.0, 0.0]
        self.sweeps = [0.0, 0.0]
        self.time = 0.0
        self.ghosts: Dict[int, list] = {1: [], 2: []}
        self.shrink_warn = 0.0
        self.finish_t = -1.0
        self.loser_motion: Optional[list] = None
        self._grind_cd = 0.0
        self._danger_cache: Dict[int, pygame.Surface] = {}
        self.feed: list = []

    # ---- events → effects ------------------------------------------------------------------------
    def consume_events(self) -> None:
        b = self.battle
        for e in b.events:
            t = e["type"]
            if t == "round_start":
                for player, act in ((1, e["a1"]), (2, e["a2"])):
                    top = b.t1 if player == 1 else b.t2
                    x, y = to_screen(top.x, top.y)
                    col = self.colors[player - 1]
                    if act is Action.SPECIAL:
                        self.particles.embers(x, y, 30, A.GOLD, 160)
                        self.waves.add(x, y, 70, A.GOLD, 0.45, 5)
                        self.audio.play("special")
                        self.floats.add("SPECIAL SPIN!", x, y - 46, A.GOLD, 24)
                    elif act is Action.ATTACK:
                        self.audio.play("whoosh", 0.7)
                    elif act is Action.CHARGE:
                        self.audio.play("charge", 0.6)
                    elif act is Action.GUARD:
                        self.audio.play("guard", 0.5)
                        self.waves.add(x, y, 40, A.CYAN, 0.3, 3)
                self.feed_add(f"Round {e['round']}: {LABEL[e['a1']]} vs {LABEL[e['a2']]}")
            elif t == "dodge":
                top = b.t1 if e["player"] == 1 else b.t2
                x, y = to_screen(top.x, top.y)
                if e["ok"]:
                    self.audio.play("whoosh", 0.9)
                else:
                    self.floats.add("DODGE FAILED", x, y - 44, A.RED_HI, 20)
                    self.audio.play("dodge_fail", 0.6)
            elif t == "evade":
                top = b.t1 if e["player"] == 1 else b.t2
                x, y = to_screen(top.x, top.y)
                self.floats.add("MISS!", x, y - 44, A.CYAN, 26)
            elif t == "hit":
                self._hit_fx(e)
            elif t == "clash":
                if not e.get("landed"):
                    x, y = to_screen(e["x"], e["y"])
                    p = min(1.0, e["speed"] / 10.0)
                    self.particles.sparks(x, y, int(10 + 30 * p), 0.6 + p)
                    self.waves.add(x, y, 30 + 30 * p, (255, 220, 160), 0.25, 3)
                    self.audio.clash(p)
                    self.camera.kick(2 + 4 * p)
            elif t == "grind":
                x, y = to_screen(e["x"], e["y"])
                self.particles.sparks(x, y, 3, 0.5, (255, 190, 90))
                if self._grind_cd <= 0:
                    self.audio.play("grind", 0.6)
                    self._grind_cd = 0.14
            elif t == "shrink_warning":
                self.shrink_warn = C.ROUND_SECONDS
                self.audio.play("alarm")
                self.banner.show("ARENA SHRINKS!", A.WHITE, A.RED, 1.2, "stay away from the edge")
            elif t == "shrink":
                self.shrink_warn = 0.0
                self.camera.kick(5)
                self.feed_add(f"Stadium shrinks to radius {e['radius']:.0f}")
            elif t == "finish":
                self._finish_fx(e)
        b.events.clear()

    def _hit_fx(self, e: dict) -> None:
        b = self.battle
        att = b.t1 if e["attacker"] == 1 else b.t2
        dfn = b.t1 if e["defender"] == 1 else b.t2
        ax, ay = to_screen(att.x, att.y)
        dx, dy = to_screen(dfn.x, dfn.y)
        mx, my = (ax + dx) / 2, (ay + dy) / 2
        special = e["action"] is Action.SPECIAL
        dmg = e["damage"]
        power = min(1.6, 0.6 + dmg / 18)
        ang = math.atan2(dy - ay, dx - ax)
        self.particles.sparks(mx, my, int(26 + dmg * 2.2), power, (255, 225, 150), direction=ang, spread=1.2)
        self.particles.sparks(mx, my, 14, 0.7, self.colors[e["attacker"] - 1])
        self.waves.add(mx, my, 60 + dmg * 2.5, (255, 235, 200), 0.32, 5)
        if special:
            self.waves.add(mx, my, 140, A.GOLD, 0.5, 7)
            self.particles.embers(mx, my, 40, A.ORANGE, 220)
        self.camera.freeze(0.10 if special else 0.055)
        self.camera.kick(10 if special else 5)
        self.audio.clash(1.0 if special else 0.75)
        col = A.GOLD if special else A.WHITE
        self.floats.add(f"-{dmg:.0f}", dx, dy - 40, col, 34 if special else 28)
        if e["defender_action"] is Action.GUARD:
            self.floats.add("GUARD BREAK!" if special else "BLOCKED", dx, dy - 72, A.CYAN, 20)
        if e["defender_action"] is Action.CHARGE:
            self.floats.add("COUNTER!", dx, dy - 72, A.ORANGE, 20)
        if e["recoil"] > 0:
            self.floats.add(f"RECOIL -{e['recoil']:.0f}", ax, ay - 40, A.RED_HI, 18)
        who = self.tags[e["attacker"] - 1]
        self.feed_add(f"{who} {LABEL[e['action']].upper()} lands: -{dmg:.0f}")

    def _finish_fx(self, e: dict) -> None:
        b = self.battle
        reason = e["reason"]
        text, col = FINISH_TEXT.get(reason, ("FINISH!", A.WHITE))
        loser = None
        if e["winner"] in (1, 2):
            loser = b.t2 if e["winner"] == 1 else b.t1
        glow = col
        sub = ""
        if e["winner"] == 0:
            sub = "both blades fell together" if reason == "DRAW" else "scores tied"
        else:
            tag = self.tags[e['winner'] - 1]
            sub = 'you win' if tag == 'YOU' else f'{tag} wins'
        self.banner.show(text, A.WHITE, glow, 3.2, sub)
        self.camera.slow(1.6, 0.25)
        self.camera.kick(12)
        self.audio.stop_hums()
        self.audio.play("crowd", 0.8)
        self.finish_t = 0.0
        if loser is not None:
            x, y = to_screen(loser.x, loser.y)
            self.camera.focus_target = (x, y)
            self.camera.zoom_target = 1.25
            if reason == "BURST":
                self.audio.play("burst")
                self.particles.shards(x, y, 26, self.colors[loser.player - 1])
                self.particles.sparks(x, y, 80, 1.5)
                self.waves.add(x, y, 180, A.RED, 0.6, 8)
            elif reason == "RING_OUT":
                self.audio.play("ringout")
            else:
                self.audio.play("spinout")
            self.loser_motion = [loser.player, reason, x, y, loser.vx * PPU, loser.vy * PPU, 0.0]
        else:
            self.audio.play("go", 0.6)

    def feed_add(self, msg: str) -> None:
        self.feed.append([msg, 0.0])
        self.feed = self.feed[-4:]

    # ---- per-frame --------------------------------------------------------------------------------
    def update(self, real_dt: float, sim_dt: float) -> None:
        self.time += real_dt
        self._grind_cd -= real_dt
        self.shrink_warn = max(0.0, self.shrink_warn - sim_dt)
        b = self.battle
        for i, top in enumerate(b.tops):
            e01 = max(0.0, top.energy) / C.START_ENERGY
            # Real fast rotation (up to ~9 turns/s). Fast turns alias at 60 fps, so the draw adds an
            # exposure-style blur across the angle swept each frame (see TopArt.draw `sweep`).
            spin = 0.0 if (top.out == "SPIN_OUT") else (6.0 + 52.0 * e01)
            self.angles[i] += spin * sim_dt
            self.sweeps[i] = spin / 60.0
            pos = to_screen(top.x, top.y)
            self.trails.push(top.player, pos)
            if top.action is Action.DODGE and b.round_t < 0.5:
                self.ghosts[top.player].append([pos[0], pos[1], 0.35])
            if top.action is Action.CHARGE and not b.over and int(self.time * 30) % 3 == 0:
                self.particles.inward(pos[0], pos[1], TOP_PX, 1, A.CYAN)
            if top.action is Action.SPECIAL and b.round_t < 1.0 and not b.over:
                self.particles.embers(pos[0], pos[1], 2, A.GOLD, 90, 0.45)
            if not b.over:
                self.audio.hum(top.player, e01, top.out is None)
        for g in self.ghosts.values():
            for it in g:
                it[2] -= real_dt
            g[:] = [it for it in g if it[2] > 0][-6:]
        self.particles.update(sim_dt if sim_dt > 0 else 0.0)
        self.waves.update(real_dt)
        self.floats.update(real_dt)
        self.banner.update(real_dt)
        self.camera.update(real_dt)
        for f in self.feed:
            f[1] += real_dt
        self.feed = [f for f in self.feed if f[1] < 6.0]
        if self.finish_t >= 0:
            self.finish_t += real_dt
        if self.loser_motion is not None:
            lm = self.loser_motion
            lm[6] += sim_dt
            if lm[1] == "RING_OUT":
                lm[2] += lm[4] * sim_dt
                lm[3] += lm[5] * sim_dt
                lm[4] *= 0.99
                lm[5] *= 0.99

    # ---- drawing ---------------------------------------------------------------------------------
    def draw(self, world: pygame.Surface) -> None:
        b = self.battle
        world.blit(A.stage_background(), (0, 0))
        world.blit(self.bowl, self.bowl.get_rect(center=(CX, CY)))
        ox, oy = CX - LAYER_HALF, CY - LAYER_HALF
        light = self.light

        # Danger zone outside the live boundary.
        live_px = int(b.radius * PPU)
        if live_px < BOWL_PX - 1:
            world.blit(self._danger(live_px), (CX - BOWL_PX - 4, CY - BOWL_PX - 4))

        # ---- light pass 1: LED rim, live rim, under-glows, trails, ghosts ----
        light.fill((0, 0, 0))
        lc = (LAYER_HALF, LAYER_HALF)
        led_r = BOWL_PX + 13
        for i in range(84):
            a = 2 * math.pi * i / 84
            k = 0.25 + 0.75 * max(0.0, math.cos(a * 3 - self.time * 3.2)) ** 3
            base = A.BLUE if math.cos(a) < 0 else A.RED
            px, py = lc[0] + math.cos(a) * led_r, lc[1] + math.sin(a) * led_r
            pygame.draw.circle(light, A.shade(base, 0.35 + 0.65 * k), (int(px), int(py)), 3)
        rim_col = A.RED if self.shrink_warn > 0 and int(self.time * 6) % 2 == 0 else (90, 150, 255)
        pygame.draw.circle(light, A.shade(rim_col, 0.55), lc, live_px, 5)
        pygame.draw.circle(light, rim_col, lc, live_px, 2)
        if self.shrink_warn > 0:
            fut = int(max(C.STADIUM_MIN_RADIUS, b.radius - C.SHRINK_STEP) * PPU)
            for i in range(48):
                if i % 2 == 0:
                    a0 = 2 * math.pi * i / 48 + self.time
                    pygame.draw.arc(light, A.RED, (lc[0] - fut, lc[1] - fut, fut * 2, fut * 2), a0, a0 + 0.1, 2)
        for i, top in enumerate(b.tops):
            if top.out == "RING_OUT" and self.loser_motion and self.loser_motion[0] == top.player:
                continue
            sx, sy = to_screen(top.x, top.y)
            col = self.colors[i]
            g = A.glow(int(TOP_PX * 2.4), col, 0.9)
            light.blit(g, (sx - ox - g.get_width() / 2, sy - oy - g.get_height() / 2), special_flags=pygame.BLEND_ADD)
            pts = [(px - ox, py - oy) for px, py in self.trails.pts[top.player]]
            n = len(pts)
            for j in range(1, n):
                k = j / n
                pygame.draw.line(light, A.shade(col, 0.65 * k), pts[j - 1], pts[j], max(1, int(TOP_PX * 0.9 * k)))
            for gx, gy, life in self.ghosts[top.player]:
                pygame.draw.circle(light, A.shade(col, life * 1.2), (int(gx - ox), int(gy - oy)), TOP_PX, 2)
            # danger ring under a top in HIGH danger
            d, lab = b.danger(top.player)
            if lab == "HIGH" and not b.over:
                pulse = 0.5 + 0.5 * math.sin(self.time * 10)
                pygame.draw.circle(light, A.shade(A.RED, 0.4 + 0.5 * pulse), (int(sx - ox), int(sy - oy)), TOP_PX + 10, 3)
        world.blit(light, (ox, oy), special_flags=pygame.BLEND_ADD)

        # ---- the tops ----
        for i, top in enumerate(b.tops):
            self._draw_top(world, i, top)

        # ---- light pass 2: auras, sparks, shockwaves ----
        light.fill((0, 0, 0))
        for i, top in enumerate(b.tops):
            if top.out is not None:
                continue
            sx, sy = to_screen(top.x, top.y)
            lx, ly = sx - ox, sy - oy
            act = top.action
            if act is Action.GUARD:
                for h in range(6):
                    a0 = h * math.pi / 3 + self.time * 1.5
                    p0 = (lx + math.cos(a0) * (TOP_PX + 9), ly + math.sin(a0) * (TOP_PX + 9))
                    p1 = (lx + math.cos(a0 + math.pi / 3) * (TOP_PX + 9), ly + math.sin(a0 + math.pi / 3) * (TOP_PX + 9))
                    pygame.draw.line(light, (60, 200, 230), p0, p1, 3)
            elif act is Action.CHARGE:
                r = TOP_PX + 6 + 4 * math.sin(self.time * 8)
                pygame.draw.circle(light, (40, 120, 200), (int(lx), int(ly)), int(r), 2)
            elif act in (Action.ATTACK, Action.SPECIAL) and b.round_t < C.HOMING_SECONDS:
                sp = math.hypot(top.vx, top.vy)
                if sp > 1.0:
                    ux, uy = top.vx / sp, top.vy / sp
                    col = (255, 170, 60) if act is Action.SPECIAL else (255, 230, 200)
                    for k in range(-2, 3):
                        px, py = -uy * k * 9, ux * k * 9
                        ln = (40 + 16 * (2 - abs(k))) * (1.4 if act is Action.SPECIAL else 1.0)
                        pygame.draw.line(light, A.shade(col, 0.55), (lx + px - ux * TOP_PX, ly + py - uy * TOP_PX),
                                         (lx + px - ux * (TOP_PX + ln), ly + py - uy * (TOP_PX + ln)), 2)
                if act is Action.SPECIAL:
                    g = A.glow(int(TOP_PX * 3.2), (255, 150, 40), 0.7)
                    light.blit(g, (lx - g.get_width() / 2, ly - g.get_height() / 2), special_flags=pygame.BLEND_ADD)
        # particles & waves are in screen space; shift into the layer
        self._draw_particles_into(light, ox, oy)
        world.blit(light, (ox, oy), special_flags=pygame.BLEND_ADD)

        # Name tags and floating text.
        for i, top in enumerate(b.tops):
            if top.out == "RING_OUT":
                continue
            sx, sy = to_screen(top.x, top.y)
            self._tag(world, self.tags[i], self.colors[i], (sx, sy - TOP_PX - 18))
        self.floats.draw(world)

    def _draw_particles_into(self, light: pygame.Surface, ox: int, oy: int) -> None:
        for p in self.particles.items:
            k = p.life / p.max_life
            c = (int(p.color[0] * k), int(p.color[1] * k), int(p.color[2] * k))
            x, y = p.x - ox, p.y - oy
            if p.kind == "spark":
                ln = 0.022 * k
                pygame.draw.line(light, c, (x, y), (x - p.vx * ln, y - p.vy * ln), max(1, int(p.size * k + 0.5)))
            elif p.kind == "shard":
                s = p.size * (0.5 + 0.5 * k)
                a = p.life * 9
                pygame.draw.polygon(light, c, [(x + math.cos(a + i * 2.1) * s, y + math.sin(a + i * 2.1) * s) for i in range(3)])
            else:
                pygame.draw.circle(light, c, (int(x), int(y)), max(1, int(p.size * (0.4 + 0.6 * k))))
        for x, y, t, dur, max_r, color, width in self.waves.items:
            k = t / dur
            r = int(6 + max_r * (1 - (1 - k) ** 3))
            fade = 1 - k
            pygame.draw.circle(light, A.shade(color, fade), (int(x - ox), int(y - oy)), r, max(1, int(width * fade + 1)))

    def _draw_top(self, world: pygame.Surface, i: int, top) -> None:
        art = self.arts[i]
        sx, sy = to_screen(top.x, top.y)
        e01 = max(0.0, top.energy) / C.START_ENERGY
        stab01 = top.stability / top.spec.max_stability
        alpha = 255
        squash = 1.0
        lm = self.loser_motion
        if lm is not None and lm[0] == top.player:
            reason, t = lm[1], lm[6]
            if reason == "RING_OUT":
                sx, sy = lm[2], lm[3]
                alpha = int(max(0, 255 - t * 260))
                squash = max(0.4, 1 - t * 0.5)
            elif reason == "BURST":
                alpha = int(max(0, 255 - t * 700))
            else:  # spin-out: wobble to a stop and tip over
                squash = max(0.55, 1 - t * 0.6)
                sx += math.sin(t * 9) * 6 * max(0.0, 1 - t)
            if alpha <= 0:
                return
        elif stab01 < 0.4 and top.out is None:  # low stability: precession wobble
            amp = (0.4 - stab01) * 16
            sx += math.cos(self.time * 14) * amp
            sy += math.sin(self.time * 14) * amp * 0.6
            squash = 1 - (0.4 - stab01) * 0.25
        art.draw(world, (sx, sy), self.angles[i], e01 if top.out != "SPIN_OUT" else 0.0, alpha, squash,
                 sweep=self.sweeps[i])

    def _tag(self, world: pygame.Surface, s: str, col, pos) -> None:
        img = A.font(15, "bold").render(s, True, (8, 12, 22))
        r = img.get_rect(center=(int(pos[0]), int(pos[1])))
        bg = r.inflate(16, 6)
        pygame.draw.rect(world, A.shade(col, 0.35), bg.move(0, 2), border_radius=9)
        pygame.draw.rect(world, col, bg, border_radius=9)
        world.blit(img, r)

    def _danger(self, live_px: int) -> pygame.Surface:
        s = self._danger_cache.get(live_px)
        if s is None:
            size = BOWL_PX * 2 + 8
            s = pygame.Surface((size, size), pygame.SRCALPHA)
            c = size // 2
            pygame.draw.circle(s, (40, 0, 6, 150), (c, c), BOWL_PX + 2)
            for k in range(-size, size, 14):  # hazard hatch
                pygame.draw.line(s, (255, 60, 40, 40), (k, 0), (k + size, size), 3)
            pygame.draw.circle(s, (0, 0, 0, 0), (c, c), live_px)
            mask = pygame.Surface((size, size), pygame.SRCALPHA)
            pygame.draw.circle(mask, (255, 255, 255, 255), (c, c), BOWL_PX + 2)
            s.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            if len(self._danger_cache) > 40:
                self._danger_cache.clear()
            self._danger_cache[live_px] = s
        return s
