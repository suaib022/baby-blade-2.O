"""Battle scene: launch countdown, live real-time battle, HUD, controls, pause and finish."""

from __future__ import annotations

import math
import random
import sys
from typing import List, Optional

import pygame

from babyblade import config as C
from babyblade.game import assets as A
from babyblade.game import coach, inputs, ui
from babyblade.game.app import Scene
from babyblade.game.arena_view import CX, CY, PPU, TOP_PX, ArenaView, to_screen
from babyblade.game.audio import AUDIO
from babyblade.game.match import MatchSetup
from babyblade.game.profile import PROFILE, art_for
from babyblade.sim.actions import COST, LABEL, ORDER, Action
from babyblade.sim.blades import STADIUM_NAMES, spec

IS_WEB = sys.platform == "emscripten"
ACTION_COLORS = {Action.CHARGE: A.CYAN, Action.ATTACK: A.ORANGE, Action.GUARD: (90, 200, 230),
                 Action.DODGE: A.PURPLE, Action.SPECIAL: A.GOLD}


class BattleScene(Scene):
    GUIDE_BTN = pygame.Rect(812, 16, 128, 34)

    def __init__(self, setup: MatchSetup) -> None:
        self.setup = setup
        self.human_mode = setup.human_mode
        self.phase = "launch"
        self.launch_t = 0.0
        self.meter = 0.0
        self.locked_power: Optional[float] = None
        self.battle = None
        self.human = None
        self.human_player = 1 if setup.p1.is_human else (2 if setup.p2.is_human else 0)
        self.view: Optional[ArenaView] = None
        self.world = pygame.Surface((A.W, A.H))
        self.paused = False
        self.guide = False
        self.hover_action = None
        self.speed = 1
        self.playing = True
        self.stick = ui.Stick((104, 604), 62)
        self.portraits = (art_for(setup.p1.look, 30), art_for(setup.p2.look, 30))
        self.portrait_angle = 0.0
        self.tags = (setup.p1.tag(self.human_mode, 1), setup.p2.tag(self.human_mode, 2))
        self.lock_flash = 0.0
        self.action_rects: List[pygame.Rect] = []
        self.pause_menu: Optional[ui.Menu] = None
        self.ctrl_menu: Optional[ui.Menu] = None
        self.rng = random.Random(setup.seed + 5)
        self._build_controls()

    # ---- setup -----------------------------------------------------------------------------
    def _build_controls(self) -> None:
        self.action_rects = []
        w, gap = 132, 10
        x0 = A.W // 2 - (w * 5 + gap * 4) // 2
        for i in range(5):
            self.action_rects.append(pygame.Rect(x0 + i * (w + gap), 642, w, 66))
        if not self.human_mode:
            labels = [("Pause", self._toggle_play), ("Step", self._step), ("1x", lambda: self._speed(1)),
                      ("2x", lambda: self._speed(2)), ("4x", lambda: self._speed(4)), ("Swap", self._swap),
                      ("Restart", self._restart), ("Menu", self._menu)]
            ws = [110, 90, 64, 64, 64, 90, 100, 90]
            total = sum(ws) + 8 * (len(ws) - 1)
            x = A.W // 2 - total // 2
            widgets = []
            for (lab, fn), w_ in zip(labels, ws):
                widgets.append(ui.Button((x, 652, w_, 50), lab, fn, size=18))
                x += w_ + 8
            self.ctrl_menu = ui.Menu(widgets, columns=len(widgets))
            self.ctrl_menu.focus = 0

    def _toggle_play(self) -> None:
        self.playing = not self.playing
        if self.ctrl_menu:
            self.ctrl_menu.widgets[0].label = "Play" if not self.playing else "Pause"

    def _step(self) -> None:
        if self.battle and not self.battle.over:
            self.playing = False
            if self.ctrl_menu:
                self.ctrl_menu.widgets[0].label = "Play"
            self.battle.step_round()

    def _speed(self, s: int) -> None:
        self.speed = s

    def _swap(self) -> None:
        self.app.replace(BattleScene(self.setup.swapped()))

    def _restart(self) -> None:
        self.app.replace(BattleScene(self.setup))

    def _menu(self) -> None:
        AUDIO.stop_hums()
        from babyblade.game.scenes.title import TitleScene
        self.app.reset_to(TitleScene())

    def _start_fight(self) -> None:
        human_power = self.locked_power if self.locked_power is not None else self._power_now()
        ai_p = lambda: self.rng.uniform(0.55, 0.95)
        p1 = human_power if self.setup.p1.is_human else ai_p()
        p2 = human_power if self.setup.p2.is_human else ai_p()
        self.battle, self.human = self.setup.build((p1, p2))
        if self.human is not None:
            self.human.queued = Action.ATTACK
        self.view = ArenaView(self.battle, (self.setup.p1.look, self.setup.p2.look), self.tags)
        self.view.camera.enabled_shake = PROFILE.settings.shake
        self.view.banner.show("LET IT RIP!", A.WHITE, A.BLUE, 1.1)
        self.phase = "fight"
        AUDIO.play("launch")
        AUDIO.play("go", 0.7)

    def _power_now(self) -> float:
        # Needle sweeps 0..1..0; the sweet spot is the middle of the gauge.
        return 1.0 - abs(self.meter - 0.5) * 2.0

    # ---- events -----------------------------------------------------------------------------
    def event(self, e: pygame.event.Event) -> None:
        if e.type == pygame.MOUSEMOTION:
            self.hover_action = self._action_at(e.pos) if self.human_mode else None
        if self.phase == "fight" and not self.paused:
            if self.guide:  # any key or click closes the guide
                if e.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN):
                    self.guide = False
                return
            opens = (e.type == pygame.KEYDOWN and e.key in (pygame.K_h, pygame.K_F1)) or \
                (e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and self.GUIDE_BTN.collidepoint(e.pos))
            if opens:
                self.guide = True
                AUDIO.stop_hums()
                AUDIO.play("select")
                return
        if self.paused and self.pause_menu:
            cmd = inputs.nav(e)
            if cmd == "back" or (e.type == pygame.KEYDOWN and e.key == pygame.K_p):
                self._resume()
                return
            if cmd:
                self.pause_menu.nav(cmd)
            self.pause_menu.handle(e)
            return
        if self.phase == "launch":
            if inputs.nav(e) == "confirm" or (e.type == pygame.MOUSEBUTTONDOWN and e.button == 1) or e.type == pygame.FINGERDOWN:
                if self.locked_power is None and self.human_mode:
                    self.locked_power = self._power_now()
                    AUDIO.play("select")
            if inputs.nav(e) == "back":
                self._menu()
            return
        if self.phase == "finish":
            if inputs.nav(e) in ("confirm", "back") or (e.type == pygame.MOUSEBUTTONDOWN and e.button == 1):
                if self.view and self.view.finish_t > 1.0:
                    self._to_results()
            return
        # fight
        if inputs.is_pause(e) or self._pause_click(e):
            self._pause()
            return
        if self.human_mode:
            act = inputs.battle_action(e)
            if act is None and e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                act = self._action_at(e.pos)
            if act is None and e.type == pygame.FINGERDOWN:
                pos = (e.x * A.W, e.y * A.H)
                if not self.stick.press(e.finger_id, pos):
                    act = self._action_at(pos)
            if e.type == pygame.FINGERMOTION:
                self.stick.move(e.finger_id, (e.x * A.W, e.y * A.H))
            if e.type == pygame.FINGERUP:
                self.stick.release(e.finger_id)
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and not getattr(e, "touch", False):
                self.stick.press("mouse", e.pos)
            if e.type == pygame.MOUSEMOTION and not getattr(e, "touch", False):
                self.stick.move("mouse", e.pos)
            if e.type == pygame.MOUSEBUTTONUP and e.button == 1:
                self.stick.release("mouse")
            if act is not None:
                self._queue(act)
        elif self.ctrl_menu:
            if e.type == pygame.KEYDOWN and e.key == pygame.K_SPACE:
                self._toggle_play()
                return
            if e.type == pygame.KEYDOWN and e.key == pygame.K_s:
                self._step()
                return
            cmd = inputs.nav(e)
            if cmd in ("left", "right", "confirm"):
                self.ctrl_menu.nav(cmd)
            self.ctrl_menu.handle(e)

    def _pause_click(self, e: pygame.event.Event) -> bool:
        return self.human_mode and e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and \
            math.hypot(e.pos[0] - 1218, e.pos[1] - 668) < 32

    def _action_at(self, pos) -> Optional[Action]:
        for i, r in enumerate(self.action_rects):
            if r.collidepoint(pos):
                return ORDER[i]
        return None

    def _queue(self, act: Action) -> None:
        b = self.battle
        top = b.t1 if self.human_player == 1 else b.t2
        legal = b.legal(self.human_player)
        if act not in legal:
            AUDIO.play("dodge_fail", 0.5)
            return
        if self.human.queued is not act:
            AUDIO.play("select", 0.7)
        self.human.queued = act

    def _pause(self) -> None:
        self.paused = True
        AUDIO.stop_hums()
        cx = A.W // 2
        items = [ui.Button((cx - 160, 280, 320, 56), "Resume", self._resume, icon="PLAY"),
                 ui.Button((cx - 160, 348, 320, 56), "Restart", self._restart),
                 ui.Button((cx - 160, 416, 320, 56), "Quit to menu", self._menu, accent=A.RED)]
        self.pause_menu = ui.Menu(items)

    def _resume(self) -> None:
        self.paused = False
        self.pause_menu = None

    def _to_results(self) -> None:
        from babyblade.game.scenes.results import ResultsScene
        AUDIO.stop_hums()
        self.app.replace(ResultsScene(self.setup, self.battle, self.tags))

    # ---- update -----------------------------------------------------------------------------
    def update(self, dt: float) -> None:
        self.portrait_angle += dt * 9
        if self.guide:
            return  # the battle is frozen while the guide is open
        if self.paused:
            if self.pause_menu:
                self.pause_menu.update(dt)
            return
        if self.phase == "launch":
            self._update_launch(dt)
            return
        view, b = self.view, self.battle
        assert view is not None and b is not None
        if self.ctrl_menu:
            self.ctrl_menu.update(dt)
        scale = view.camera.time_scale()
        sim_dt = dt * scale * (self.speed if not self.human_mode else 1)
        if not self.human_mode and not self.playing:
            sim_dt = 0.0
        if self.human_mode and self.human is not None and not b.over:
            sx, sy = inputs.steer()
            sx += self.stick.vec[0]
            sy += self.stick.vec[1]
            top = b.t1 if self.human_player == 1 else b.t2
            top.steer_x, top.steer_y = sx, sy
        prev_round = b.round
        if sim_dt > 0 and not b.over:
            b.update(sim_dt, think_budget=0.004 if IS_WEB else 0.006)
        if b.round != prev_round:
            self.lock_flash = 0.6
        self.lock_flash = max(0.0, self.lock_flash - dt)
        view.consume_events()
        view.update(dt, sim_dt if not b.over else dt * scale)
        if b.over and self.phase != "finish":
            self.phase = "finish"
        if self.phase == "finish" and view.finish_t > 4.5:
            self._to_results()

    def _update_launch(self, dt: float) -> None:
        prev = self.launch_t
        self.launch_t += dt
        if self.locked_power is None:
            self.meter = (self.meter + dt * 1.4) % 2.0
        for mark in (0.0, 0.8, 1.6):
            if prev < mark <= self.launch_t or (mark == 0.0 and prev == 0.0):
                AUDIO.play("beep")
        if self.launch_t >= 2.4:
            self._start_fight()

    # ---- drawing ----------------------------------------------------------------------------
    def draw(self, screen: pygame.Surface) -> None:
        if self.phase == "launch" or self.view is None:
            self._draw_launch(screen)
            return
        self.view.draw(self.world)
        self.view.camera.present(self.world, screen)
        self._draw_hud(screen)
        self._draw_guide_button(screen)
        self._draw_coach(screen)
        self.view.banner.draw(screen)
        if self.phase == "finish" and self.view.finish_t > 1.2:
            A.text(screen, "PRESS ENTER / TAP FOR RESULTS", 18, A.MUTED, (A.W / 2, A.H * 0.36 + 96))
        if self.guide:
            self._draw_guide(screen)
        if self.paused:
            self._draw_pause(screen)

    def _draw_launch(self, screen: pygame.Surface) -> None:
        screen.blit(A.stage_background(), (0, 0))
        bowl = A.stadium_bowl(self.setup.stadium.value, int(C.STADIUM_START_RADIUS * PPU))
        screen.blit(bowl, bowl.get_rect(center=(CX, CY)))
        for i, (side, x) in enumerate(((self.setup.p1, -5.0), (self.setup.p2, 5.0))):
            art = art_for(side.look, TOP_PX)
            sx, sy = to_screen(x, 0)
            hover = math.sin(self.launch_t * 3 + i) * 4
            screen.blit(A.glow(TOP_PX * 3, side.look.color, 0.8), (sx - TOP_PX * 3, sy - TOP_PX * 3 + hover), special_flags=pygame.BLEND_ADD)
            art.draw(screen, (sx, sy + hover), self.launch_t * 2, 0.0)
            A.text(screen, self.tags[i], 18, side.look.color, (sx, sy - 50), weight="bold")
        n = 3 - int(self.launch_t / 0.8)
        k = (self.launch_t % 0.8) / 0.8
        if n >= 1:
            A.glow_text(screen, str(n), 150, A.WHITE, A.BLUE, (A.W / 2, A.H * 0.42), scale=1.5 - 0.5 * k, alpha=int(255 * (1 - k * 0.6)))
        A.text(screen, f"{STADIUM_NAMES[self.setup.stadium].upper()}", 22, A.MUTED, (A.W / 2, 40), weight="bold")
        A.text(screen, f"{self.setup.p1.title()}   vs   {self.setup.p2.title()}", 30, A.WHITE, (A.W / 2, 78), weight="bold")
        if self.human_mode:
            r = pygame.Rect(A.W / 2 - 220, 640, 440, 26)
            pygame.draw.rect(screen, (10, 14, 26), r, border_radius=13)
            sweet = pygame.Rect(r.centerx - 44, r.y, 88, r.h)
            pygame.draw.rect(screen, (40, 120, 80), sweet, border_radius=13)
            pygame.draw.rect(screen, A.LINE, r, 2, border_radius=13)
            pos = self.meter if self.meter <= 1 else 2 - self.meter
            nx = r.x + r.w * pos
            pygame.draw.line(screen, A.GOLD if self.locked_power is None else A.GREEN, (nx, r.y - 8), (nx, r.bottom + 8), 4)
            msg = "PRESS SPACE / TAP IN THE GREEN ZONE FOR A POWER LAUNCH" if self.locked_power is None else f"LAUNCH POWER {int(self.locked_power * 100)}%"
            A.text(screen, msg, 16, A.WHITE, (A.W / 2, 618), weight="bold")

    def _draw_hud(self, screen: pygame.Surface) -> None:
        b = self.battle
        for player, x in ((1, 16), (2, A.W - 16 - 300)):
            self._player_card(screen, player, pygame.Rect(x, 16, 300, 360))
        # Round / clock box
        box = pygame.Rect(A.W // 2 - 150, 10, 300, 92)
        ui.panel(screen, box, alpha=210)
        remaining = max(0.0, C.ROUNDS * C.ROUND_SECONDS - b.time)
        A.text(screen, f"ROUND {min(C.ROUNDS, b.round + 1)} / {C.ROUNDS}", 18, A.MUTED, (box.centerx, box.y + 16), weight="bold")
        A.text(screen, f"{int(remaining // 60)}:{int(remaining % 60):02d}", 40, A.WHITE, (box.centerx, box.y + 50), weight="bold")
        prog = pygame.Rect(box.x + 20, box.bottom - 16, box.w - 40, 8)
        ui.bar(screen, prog, b.round_t / C.ROUND_SECONDS, A.GOLD if self.lock_flash <= 0 else A.WHITE)
        A.text(screen, f"{STADIUM_NAMES[b.stadium]}  ·  radius {b.radius:.1f}", 14, A.MUTED, (box.centerx, box.bottom + 14))
        # Event feed
        feed = self.view.feed[-4:]
        if feed:
            A.text(screen, "BATTLE LOG", 13, A.DIM, (24, 392), anchor="topleft", weight="bold")
        for i, (msg, age) in enumerate(feed):
            a = int(255 * max(0.0, min(1.0, 1.5 - age / 4)))
            A.text(screen, msg, 15, A.MUTED, (24, 412 + i * 22), anchor="topleft", alpha=a)
        if self.human_mode:
            self._action_bar(screen)
            self.stick.draw(screen)
            pc = (1218, 668)
            pygame.draw.circle(screen, A.PANEL, pc, 30)
            pygame.draw.circle(screen, A.LINE, pc, 30, 2)
            A.draw_icon(screen, "PAUSE", pc, 26, A.WHITE)
            A.text(screen, "P / ESC", 12, A.MUTED, (pc[0], pc[1] - 42))
        elif self.ctrl_menu:
            self.ctrl_menu.draw(screen)
            A.text(screen, f"SPEED {self.speed}x  ·  SPACE play/pause  ·  S step", 14, A.MUTED, (A.W / 2, 632))

    def _player_card(self, screen: pygame.Surface, player: int, rect: pygame.Rect) -> None:
        b = self.battle
        top = b.t1 if player == 1 else b.t2
        side = self.setup.p1 if player == 1 else self.setup.p2
        col = side.look.color
        ui.panel(screen, rect, accent=col, alpha=200)
        right = player == 2
        # portrait
        pc = (rect.right - 46, rect.y + 52) if right else (rect.x + 46, rect.y + 52)
        screen.blit(A.glow(46, col, 0.7), (pc[0] - 46, pc[1] - 46), special_flags=pygame.BLEND_ADD)
        e01 = max(0.0, top.energy) / C.START_ENERGY
        self.portraits[player - 1].draw(screen, pc, self.portrait_angle * (0.3 + e01), e01)
        ui.ring(screen, pc, 38, e01, A.GOLD, 4)
        tx = rect.x + 96 if not right else rect.right - 96
        anchor = "midleft" if not right else "midright"
        A.text(screen, self.tags[player - 1], 14, col, (tx, rect.y + 22), anchor=anchor, weight="bold")
        A.text(screen, side.title(), 22, A.WHITE, (tx, rect.y + 46), anchor=anchor, weight="bold")
        A.text(screen, spec(top.kind).name.upper(), 14, A.MUTED, (tx, rect.y + 72), anchor=anchor, weight="bold")
        y = rect.y + 104
        # SPIN (energy)
        A.text(screen, "SPIN  ·  energy", 14, A.MUTED, (rect.x + 16, y), anchor="midleft", weight="bold")
        A.text(screen, f"{max(0, top.energy):.0f}", 16, A.WHITE, (rect.right - 16, y), anchor="midright", weight="bold")
        ui.bar(screen, pygame.Rect(rect.x + 16, y + 12, rect.w - 32, 14), e01, A.mix(A.RED, A.GOLD, min(1, e01 * 2)))
        y += 44
        # BURST (stability)
        st01 = max(0.0, top.stability) / top.spec.max_stability
        A.text(screen, "BURST GUARD  ·  stability", 14, A.MUTED, (rect.x + 16, y), anchor="midleft", weight="bold")
        A.text(screen, f"{max(0, top.stability):.0f}/{top.spec.max_stability:.0f}", 16, A.WHITE, (rect.right - 16, y), anchor="midright", weight="bold")
        st_col = A.BLUE if st01 > 0.5 else (A.GOLD if st01 > 0.25 else A.RED)
        ui.bar(screen, pygame.Rect(rect.x + 16, y + 12, rect.w - 32, 14), st01, st_col, segments=10)
        y += 46
        # SPECIAL + DANGER
        cd = max(0.0, top.ready_at - b.time)
        ready = cd <= 0 and top.energy >= COST[Action.SPECIAL]
        sc = (rect.x + 34, y + 10)
        ui.ring(screen, sc, 16, 1.0 - cd / C.SPECIAL_COOLDOWN if cd > 0 else 1.0, A.GOLD if ready else A.DIM, 4)
        A.draw_icon(screen, "SPECIAL", sc, 14, A.GOLD if ready else A.DIM)
        A.text(screen, "SPECIAL READY" if ready else (f"COOLDOWN {cd:.1f}s" if cd > 0 else "NEED 35 SPIN"), 14,
               A.GOLD if ready else A.MUTED, (rect.x + 58, y + 10), anchor="midleft", weight="bold")
        d, lab = b.danger(player)
        dcol = {"LOW": A.GREEN, "MEDIUM": A.GOLD, "HIGH": A.RED}[lab]
        chip = pygame.Rect(rect.right - 122, y - 3, 106, 26)
        pygame.draw.rect(screen, A.shade(dcol, 0.25), chip, border_radius=13)
        pygame.draw.rect(screen, dcol, chip, 2, border_radius=13)
        A.text(screen, f"DANGER {lab[:3]} {d:.0f}", 13, dcol, chip.center, weight="bold")
        y += 40
        # Current action
        act = top.action
        A.text(screen, "NOW", 13, A.MUTED, (rect.x + 16, y), anchor="midleft", weight="bold")
        A.draw_icon(screen, act.value, (rect.x + 62, y), 18, ACTION_COLORS[act])
        A.text(screen, LABEL[act].upper(), 18, A.WHITE, (rect.x + 78, y), anchor="midleft", weight="bold")
        if side.is_human and self.human is not None:
            nxt = self.human.queued
            A.text(screen, "NEXT", 13, A.MUTED, (rect.x + 170, y), anchor="midleft", weight="bold")
            A.draw_icon(screen, nxt.value, (rect.x + 214, y), 18, ACTION_COLORS[nxt])
            A.text(screen, LABEL[nxt].upper(), 18, A.GOLD, (rect.x + 230, y), anchor="midleft", weight="bold")
        y += 26
        # AI decision panel
        info = b.last_info.get(player) or {}
        if not side.is_human and info:
            A.text(screen, "AI DECISION", 13, A.MUTED, (rect.x + 16, y), anchor="midleft", weight="bold")
            if "scores" in info:
                vals = info["scores"]
                meta = f"minimax d{info.get('depth', 0)} · {info.get('nodes', 0)} nodes · {info.get('ms', 0):.0f} ms"
            else:
                vals = info.get("visits", {})
                meta = f"MCTS {info.get('iterations', 0)} iters · {info.get('ms', 0):.0f} ms"
            nums = [vals.get(a) for a in ORDER]
            present = [v for v in nums if v is not None and math.isfinite(v)]
            lo, hi = (min(present), max(present)) if present else (0.0, 1.0)
            bw = (rect.w - 32 - 4 * 6) / 5
            for i, a in enumerate(ORDER):
                v = vals.get(a)
                bx = rect.x + 16 + i * (bw + 6)
                full = pygame.Rect(bx, y + 14, bw, 36)
                pygame.draw.rect(screen, (10, 14, 26), full, border_radius=4)
                if v is not None and math.isfinite(v):
                    f = 0.12 + 0.88 * ((v - lo) / (hi - lo) if hi > lo else 1.0)
                    h = int(full.h * f)
                    chosen = a is info.get("action")
                    pygame.draw.rect(screen, A.GOLD if chosen else A.shade(ACTION_COLORS[a], 0.7), (bx, full.bottom - h, bw, h), border_radius=4)
                A.draw_icon(screen, a.value, (bx + bw / 2, y + 62), 12, A.MUTED)
            A.text(screen, meta, 12, A.DIM, (rect.x + 16, y + 80), anchor="midleft")
        elif side.is_human:
            A.text(screen, "Pick your next move any time;", 13, A.MUTED, (rect.x + 16, y + 8), anchor="midleft")
            A.text(screen, "it locks in when the gold bar fills.", 13, A.MUTED, (rect.x + 16, y + 26), anchor="midleft")

    def _action_bar(self, screen: pygame.Surface) -> None:
        b = self.battle
        legal = b.legal(self.human_player)
        top = b.t1 if self.human_player == 1 else b.t2
        keys = ["1", "2", "3", "SPACE", "4"]  # order: Charge, Attack, Guard, Dodge, Special
        for i, (act, r) in enumerate(zip(ORDER, self.action_rects)):
            ok = act in legal
            queued = self.human is not None and self.human.queued is act
            col = ACTION_COLORS[act]
            base = A.mix(A.PANEL, col, 0.22 if queued else 0.06) if ok else (10, 14, 24)
            pygame.draw.rect(screen, base, r, border_radius=14)
            pygame.draw.rect(screen, (col if queued else A.LINE) if ok else (30, 36, 50), r, 3 if queued else 2, border_radius=14)
            if queued:
                g = A.glow(70, col, 0.4)
                screen.blit(g, (r.centerx - 70, r.centery - 70), special_flags=pygame.BLEND_ADD)
            A.draw_icon(screen, act.value, (r.x + 30, r.centery - 2), 30, col if ok else A.DIM)
            A.text(screen, LABEL[act].upper(), 19, A.WHITE if ok else A.DIM, (r.x + 54, r.y + 22), anchor="midleft", weight="bold")
            cost = COST[act]
            sub = ("+SPIN" if act is Action.CHARGE else f"{cost:.0f} SPIN")
            if act is Action.SPECIAL and top.ready_at > b.time:
                sub = f"CD {top.ready_at - b.time:.1f}s"
            A.text(screen, sub, 13, A.MUTED if ok else A.DIM, (r.x + 54, r.y + 46), anchor="midleft", weight="bold")
            A.text(screen, keys[i], 14, A.GOLD if ok else A.DIM, (r.right - 12, r.bottom - 10), anchor="bottomright", weight="bold")
            if queued:
                A.text(screen, "NEXT", 12, col, (r.centerx, r.y - 10), weight="bold")

    # ---- Screen guide: numbered markers on the HUD and a plain-language glossary ---------------
    def _guide_items(self):
        """(number, term, explanation, [marker positions]) for every element on screen."""
        human = self.human_mode
        ai_left = not self.setup.p1.is_human  # the card that shows the AI decision panel
        x_l, x_r = 16, A.W - 16 - 300
        x_ai = x_l if ai_left else x_r
        items = [
            ("PORTRAIT RING", "The blade's picture. The gold ring is its spin energy; when it empties the blade stops.", [(x_l + 46, 68)]),
            ("SPIN", "Spin energy, 0 to 100. Actions cost spin and it drains every round. At 0: SPIN FINISH, you lose.", [(x_l + 134, 132)]),
            ("BURST GUARD", "Stability: damage the blade can take. Hits lower it, Guard restores it. At 0 it BURSTS and loses.", [(x_l + 134, 176)]),
            ("SPECIAL", "Special Spin: 35 spin, 3 s cooldown, 10 damage to yourself. READY means it can be used.", [(x_l + 34, 220)]),
            ("DANGER", "Fuzzy-logic risk, 0 to 100: LOW, MED or HIGH. High = near the rim and low on spin.", [(x_l + 231, 220)]),
            ("NOW / NEXT", "NOW: the action being played this round. NEXT: your queued action, locked in when the bar fills.", [(x_l + 62, 250)]),
            ("AI DECISION", "How much the AI likes each action; gold is its pick. Below: search depth and positions checked "
                            "(minimax) or simulations (MCTS), and thinking time in ms.", [(x_ai + 134, 306)]),
            ("ROUND · TIMER", "40 rounds of 3 s = a 2 minute match. The gold bar fills once per round, then both blades lock in actions.", [(500, 56)]),
            ("STADIUM · RADIUS", "Arena type and size. It shrinks by 1 every 6 rounds (10 to 6). Past the ring = RING OUT.", [(640, 116)]),
            ("COACH · COUNTERS", "The Coach panel explains what is happening and what to do; hover an action button for its details. "
                                 "Counters: Attack beats Charge, Guard beats Attack, Special breaks Guard, Dodge avoids both.", [(A.W - 166, 400), (A.W - 166, 556)]),
            ("BATTLE LOG · TAGS", "The log lists the actions played and the damage dealt. Tags: YOU is your blade, AI is the rival.", [(52, 404)]),
        ]
        if human:
            items.append(("CONTROLS", "1 Charge, 2 Attack (8), 3 Guard (4), SPACE Dodge (8), 4 Special (35): spin costs. "
                                      "Move freely with WASD, arrows, a stick or this touch pad.", [(640, 676), (104, 604)]))
        else:
            items.append(("CONTROLS", "Pause or play (Space), step one round (S), speed 1x 2x 4x, swap sides, restart, menu.", [(640, 677)]))
        return [(i + 1, t, d, m) for i, (t, d, m) in enumerate(items)]

    @staticmethod
    def _wrap(s: str, size: int, width: int):
        f = A.font(size, "regular")
        lines, cur = [], ""
        for w in s.split():
            t = (cur + " " + w).strip()
            if f.size(t)[0] <= width:
                cur = t
            else:
                lines.append(cur)
                cur = w
        lines.append(cur)
        return lines

    def _draw_coach(self, screen: pygame.Surface) -> None:
        """Coach tips (or the hovered action's details) and the counter chart, right column."""
        if not PROFILE.settings.coach:
            return
        x = A.W - 316
        r = pygame.Rect(x, 392, 300, 148)
        ui.panel(screen, r, accent=A.CYAN, alpha=210, title="Coach")
        hv = coach.hover_help(self.hover_action)
        y = r.y + 38
        if hv is not None:
            title, text = hv
            A.text(screen, title, 16, A.GOLD, (r.x + 16, y), anchor="topleft", weight="bold")
            for j, line in enumerate(self._wrap(text, 14, 268)[:5]):
                A.text(screen, line, 14, A.WHITE, (r.x + 16, y + 24 + j * 17), anchor="topleft", weight="regular")
        else:
            human = self.human_player
            tips = coach.tips(self.battle, human, limit=4) if human else coach.spectator_tips(self.battle, limit=4)
            sev_col = {0: A.MUTED, 1: A.GOLD, 2: A.RED_HI}
            for icon, msg, sev in tips:
                lines = self._wrap(msg, 14, 212)[:2]
                if y + len(lines) * 17 > r.bottom - 8:
                    break  # keep every tip fully inside the panel
                if icon:
                    A.draw_icon(screen, icon, (r.x + 28, y + 9 + (len(lines) - 1) * 8), 20, sev_col[sev] if sev else ACTION_COLORS[Action(icon)])
                else:
                    pygame.draw.circle(screen, A.DIM, (r.x + 28, y + 9), 3)
                for j, line in enumerate(lines):
                    A.text(screen, line, 14, A.WHITE if sev else A.MUTED, (r.x + 48, y + j * 17), anchor="topleft", weight="semi" if sev else "regular")
                y += len(lines) * 17 + 9
        c = pygame.Rect(x, 548, 300, 88)
        ui.panel(screen, c, accent=A.LINE, alpha=200, title="Counters")
        cells = [("ATTACK", "beats", ["CHARGE"]), ("GUARD", "beats", ["ATTACK"]), ("SPECIAL", "breaks", ["GUARD"]), ("DODGE", "avoids", ["ATTACK", "SPECIAL"])]
        for i, (a_, verb, bs) in enumerate(cells):
            cx, cy = c.x + 22 + (i % 2) * 146, c.y + 46 + (i // 2) * 28
            A.draw_icon(screen, a_, (cx, cy), 20, ACTION_COLORS[Action(a_)])
            A.text(screen, verb, 13, A.MUTED, (cx + 16, cy), anchor="midleft")
            for k, b_ in enumerate(bs):
                A.draw_icon(screen, b_, (cx + 64 + k * 24, cy), 20, ACTION_COLORS[Action(b_)])

    def _draw_guide_button(self, screen: pygame.Surface) -> None:
        r = self.GUIDE_BTN
        pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 400.0)
        pygame.draw.rect(screen, A.mix(A.PANEL, A.GOLD, 0.10 + 0.12 * pulse), r, border_radius=17)
        pygame.draw.rect(screen, A.GOLD, r, 2, border_radius=17)
        A.text(screen, "?  GUIDE  [H]", 15, A.GOLD, r.center, weight="bold")

    def _draw_guide(self, screen: pygame.Surface) -> None:
        dim = pygame.Surface((A.W, A.H), pygame.SRCALPHA)
        dim.fill((2, 4, 12, 205))
        screen.blit(dim, (0, 0))
        panel = pygame.Rect(330, 124, 620, 524)
        ui.panel(screen, panel, accent=A.GOLD, alpha=238)
        A.glow_text(screen, "SCREEN GUIDE", 34, A.WHITE, A.GOLD, (panel.centerx, panel.y + 28), strength=2)
        A.text(screen, "Numbers on the screen match this list.  Press H, Esc or click to close.", 14, A.MUTED, (panel.centerx, panel.y + 56))
        items = self._guide_items()
        top, bottom = panel.y + 76, panel.bottom - 10
        for size in (15, 14, 13, 12):
            lines = [self._wrap(d, size, 430) for _, _, d, _ in items]
            total = sum(len(ln) * (size + 3) + 9 for ln in lines)
            if total <= bottom - top:
                break
        gap = max(9, (bottom - top - sum(len(ln) * (size + 3) for ln in lines)) // len(items))
        y = top
        for (num, term, _d, _m), ln in zip(items, lines):
            h = len(ln) * (size + 3)
            pygame.draw.circle(screen, A.GOLD, (panel.x + 26, y + 10), 11)
            A.text(screen, str(num), 14, (20, 14, 0), (panel.x + 26, y + 10), weight="bold")
            A.text(screen, term, size + 1, A.WHITE, (panel.x + 46, y + 2), anchor="topleft", weight="bold")
            for j, t in enumerate(ln):
                A.text(screen, t, size, A.MUTED, (panel.x + 176, y + 2 + j * (size + 3)), anchor="topleft", weight="regular")
            y += h + gap
        for num, _t, _d, markers in items:
            for marker in markers:
                g = A.glow(30, A.GOLD, 0.8)
                screen.blit(g, (marker[0] - 30, marker[1] - 30), special_flags=pygame.BLEND_ADD)
                pygame.draw.circle(screen, A.GOLD, marker, 13)
                pygame.draw.circle(screen, (20, 14, 0), marker, 13, 2)
                A.text(screen, str(num), 15, (20, 14, 0), marker, weight="bold")

    def _draw_pause(self, screen: pygame.Surface) -> None:
        dim = pygame.Surface((A.W, A.H), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 170))
        screen.blit(dim, (0, 0))
        A.glow_text(screen, "PAUSED", 70, A.WHITE, A.BLUE, (A.W / 2, 200))
        if self.pause_menu:
            self.pause_menu.draw(screen)
