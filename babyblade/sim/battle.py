"""Real-time battle: continuous physics driven by the proposal's round rules.

Time is game seconds. A round lasts 3 s (40 rounds = 120 s). At each round boundary both
controllers lock in one action simultaneously; that action shapes the top's movement for the
round (dash, drift to centre, heavy guard stance, sideways dodge) and decides what happens on
contact. Costs, damage, recovery and finishes use the exact numbers in config.py, the same ones
the AI's abstract model (model.py) uses.

The battle has no rendering code. It appends events (hits, clashes, dodges, shrinks, finishes)
to `self.events` for the presentation layer and the tests to read.
"""

from __future__ import annotations

import math
import random
import time as _time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Protocol, Tuple

from babyblade import config as C
from babyblade.sim.actions import ATTACKS, COST, Action, hit_effects, is_legal, legal_actions
from babyblade.sim.blades import BladeType, StadiumType, spec
from babyblade.sim.fuzzy import blade_danger, label as danger_label
from babyblade.sim import model

THINK_LEAD = 1.2  # seconds before a boundary when controllers start thinking


class Controller(Protocol):
    name: str

    def begin(self, state: model.State, player: int) -> None: ...

    def step(self, budget_s: float) -> bool: ...

    def choice(self) -> Action: ...


@dataclass
class TopStats:
    hits: int = 0
    damage_dealt: float = 0.0
    damage_taken: float = 0.0
    actions: Dict[str, int] = field(default_factory=dict)
    think_seconds: float = 0.0
    decisions: int = 0


@dataclass
class Top:
    player: int
    kind: BladeType
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0
    energy: float = C.START_ENERGY
    stability: float = 0.0
    ready_at: float = 0.0
    action: Action = Action.CHARGE
    hit_done: bool = False
    evade_until: float = -1.0
    dodge_ok: bool = False
    steer_x: float = 0.0
    steer_y: float = 0.0
    dvx: float = 0.0  # drive velocity: follows the stick almost instantly (direct control)
    dvy: float = 0.0
    auto: bool = False  # True when an AI steers this top
    steer_gain: float = 1.0
    out: Optional[str] = None
    stats: TopStats = field(default_factory=TopStats)

    @property
    def spec(self):
        return spec(self.kind)

    @property
    def mass(self) -> float:
        return C.GUARD_MASS if self.action is Action.GUARD else 1.0

    def blade(self) -> model.Blade:
        return model.Blade(self.x, self.y, self.energy, self.stability, self.ready_at, self.kind)


class Battle:
    def __init__(
        self,
        kind1: BladeType,
        kind2: BladeType,
        stadium: StadiumType = StadiumType.CLASSIC,
        controllers: Optional[Tuple[Controller, Controller]] = None,
        seed: int = 0,
        launch: Tuple[float, float] = (0.7, 0.7),
    ) -> None:
        self.stadium = stadium
        self.rng = random.Random(seed)
        self.t1 = Top(1, kind1, -5.0, 0.0, stability=spec(kind1).max_stability)
        self.t2 = Top(2, kind2, 5.0, 0.0, stability=spec(kind2).max_stability)
        self.controllers = controllers
        if controllers:
            for top, ctl in ((self.t1, controllers[0]), (self.t2, controllers[1])):
                top.auto = not getattr(ctl, "is_human", False)
                top.steer_gain = getattr(ctl, "steer_skill", 1.0)
        self.time = 0.0
        self.round = 0  # completed rounds
        self.round_t = 0.0
        self.radius = C.STADIUM_START_RADIUS
        self._radius_from = self.radius
        self._radius_to = self.radius
        self._radius_anim = 1.0
        self.winner: Optional[int] = None
        self.finish: Optional[str] = None
        self.events: List[dict] = []
        self._thinking = False
        self._acc = 0.0
        self._started = False
        self.last_info: Dict[int, dict] = {1: {}, 2: {}}
        self._launch(launch)

    # ---- setup ------------------------------------------------------------------------------

    @property
    def tops(self) -> Tuple[Top, Top]:
        return (self.t1, self.t2)

    @property
    def over(self) -> bool:
        return self.winner is not None

    def _launch(self, power: Tuple[float, float]) -> None:
        """Launch: tops enter from opposite sides, orbiting; power sets the entry speed."""
        for top, p, side in ((self.t1, power[0], -1.0), (self.t2, power[1], 1.0)):
            p = max(0.0, min(1.0, p))
            top.x = side * (5.5 - 1.5 * p)
            top.y = self.rng.uniform(-1.5, 1.5)
            speed = 3.0 + 5.0 * p
            top.vx = -side * speed * 0.35
            top.vy = side * speed * 0.9  # both orbit the same way, like right-spin tops

    def snapshot(self) -> model.State:
        return model.State(self.t1.blade(), self.t2.blade(), self._radius_to, self.round, self.time, self.stadium)

    def danger(self, player: int) -> Tuple[float, str]:
        t = self.t1 if player == 1 else self.t2
        d = blade_danger(t.x, t.y, self.radius, t.energy)
        return d, danger_label(d)

    def legal(self, player: int) -> List[Action]:
        t = self.t1 if player == 1 else self.t2
        return legal_actions(t.energy, self.time, t.ready_at)

    # ---- the clock --------------------------------------------------------------------------

    def update(self, dt: float, think_budget: float = 0.006) -> None:
        """Advance game time by dt seconds with fixed physics substeps."""
        if self.over:
            return
        if not self._started:
            self._start_round()
            self._started = True
        self._acc += dt
        step = 1.0 / C.PHYSICS_HZ
        while self._acc >= step and not self.over:
            self._acc -= step
            self._physics(step)
            self.time += step
            self.round_t += step
            if not self._thinking and self.round_t >= C.ROUND_SECONDS - THINK_LEAD:
                self._begin_thinking()
            if self.round_t >= C.ROUND_SECONDS - 1e-9:
                self._end_round()
                if not self.over:
                    self._start_round()
        if self._thinking and not self.over:
            self._think(think_budget)

    def run_to_end(self, max_seconds: float = 400.0) -> None:
        """Headless: run the whole match (AI search runs to completion each round)."""
        step = 1.0 / C.PHYSICS_HZ
        n = 0
        while not self.over and n * step < max_seconds:
            self.update(step, think_budget=10.0)
            n += 1
            if n % 600 == 0:
                self.events.clear()

    def step_round(self) -> None:
        """Advance exactly to the next round boundary (AI vs AI single-step)."""
        start = self.round
        step = 1.0 / C.PHYSICS_HZ
        guard = 0
        while self.round == start and not self.over and guard < C.PHYSICS_HZ * 5:
            self.update(step, think_budget=10.0)
            guard += 1

    # ---- rounds -------------------------------------------------------------------------------

    def _begin_thinking(self) -> None:
        self._thinking = True
        if not self.controllers:
            return
        snap = self.snapshot()
        for player, ctl in ((1, self.controllers[0]), (2, self.controllers[1])):
            t0 = _time.perf_counter()
            ctl.begin(snap, player)
            (self.t1 if player == 1 else self.t2).stats.think_seconds += _time.perf_counter() - t0

    def _think(self, budget: float) -> None:
        if not self.controllers:
            return
        for player, ctl in ((1, self.controllers[0]), (2, self.controllers[1])):
            t0 = _time.perf_counter()
            ctl.step(budget)
            (self.t1 if player == 1 else self.t2).stats.think_seconds += _time.perf_counter() - t0

    def _choose(self, player: int) -> Action:
        top = self.t1 if player == 1 else self.t2
        if not self.controllers:
            return Action.CHARGE
        ctl = self.controllers[player - 1]
        if not self._thinking:
            ctl.begin(self.snapshot(), player)
        t0 = _time.perf_counter()
        while not ctl.step(1.0):
            pass
        act = ctl.choice()
        top.stats.think_seconds += _time.perf_counter() - t0
        top.stats.decisions += 1
        info = getattr(ctl, "info", None)
        if info:
            self.last_info[player] = dict(info)
        if not is_legal(act, top.energy, self.time, top.ready_at):
            act = legal_actions(top.energy, self.time, top.ready_at)[0]
        return act

    def _start_round(self) -> None:
        a1 = self._choose(1)
        a2 = self._choose(2)
        self._thinking = False
        self.round_t = 0.0
        ice = self.stadium is StadiumType.ICE
        mult = C.ICE_MOVE_MULT if ice else 1.0
        for top, act, opp in ((self.t1, a1, self.t2), (self.t2, a2, self.t1)):
            top.action = act
            top.hit_done = False
            top.energy -= COST[act]
            top.stats.actions[act.value] = top.stats.actions.get(act.value, 0) + 1
            dx, dy = opp.x - top.x, opp.y - top.y
            d = math.hypot(dx, dy) or 1.0
            if act in ATTACKS:
                dash = (C.DASH_SPECIAL if act is Action.SPECIAL else C.DASH_ATTACK) * mult
                top.vx += dx / d * dash
                top.vy += dy / d * dash
                if act is Action.SPECIAL:
                    top.ready_at = self.time + C.SPECIAL_COOLDOWN
                    top.stability -= C.SPECIAL_SELF_RECOIL
            elif act is Action.DODGE:
                px, py = -dy / d, dx / d
                best = None
                for sgn in (1.0, -1.0):
                    nx = top.x + sgn * px * C.MOVE_DODGE * mult
                    ny = top.y + sgn * py * C.MOVE_DODGE * mult
                    margin = self._radius_to - math.hypot(nx, ny)
                    if best is None or margin > best[2]:
                        best = (sgn * px, sgn * py, margin)
                assert best is not None
                top.vx += best[0] * C.DASH_DODGE * mult
                top.vy += best[1] * C.DASH_DODGE * mult
                top.dodge_ok = best[2] >= C.DODGE_EDGE_MARGIN
                top.evade_until = self.time + C.EVADE_SECONDS if top.dodge_ok else -1.0
                self.events.append({"type": "dodge", "player": top.player, "ok": top.dodge_ok})
        self.events.append({"type": "round_start", "round": self.round + 1, "a1": a1, "a2": a2})
        if (self.round + 1) % C.SHRINK_EVERY_ROUNDS == 0 and self.radius > C.STADIUM_MIN_RADIUS + 1e-9:
            self.events.append({"type": "shrink_warning", "round": self.round + 1})
        self._check_out()

    def _end_round(self) -> None:
        self.round += 1
        self.events.append({"type": "round_end", "round": self.round})
        if self.round >= C.ROUNDS and not self.over:
            s = model.judge(self.snapshot()._replace(radius=self.radius, round=self.round))
            self._finish(s.winner if s.winner is not None else 0, "POINTS" if s.finish in ("POINTS",) else (s.finish or "POINTS"))
            return
        new_r = model.radius_after_round(self.round)
        if new_r < self._radius_to - 1e-9:
            self._radius_from = self.radius
            self._radius_to = new_r
            self._radius_anim = 0.0
            self.events.append({"type": "shrink", "radius": new_r})

    # ---- physics ------------------------------------------------------------------------------

    def _physics(self, dt: float) -> None:
        ice = self.stadium is StadiumType.ICE
        pull = C.STEEP_BOWL_PULL if self.stadium is StadiumType.STEEP else C.BOWL_PULL
        damping = C.LINEAR_DAMPING * (C.ICE_DAMPING_MULT if ice else 1.0)
        mult = C.ICE_MOVE_MULT if ice else 1.0
        frac = dt / C.ROUND_SECONDS

        if self._radius_anim < 1.0:
            self._radius_anim = min(1.0, self._radius_anim + dt / C.SHRINK_ANIM_SECONDS)
            k = self._radius_anim * self._radius_anim * (3 - 2 * self._radius_anim)
            self.radius = self._radius_from + (self._radius_to - self._radius_from) * k

        for top, opp in ((self.t1, self.t2), (self.t2, self.t1)):
            ax = -pull * top.x
            ay = -pull * top.y
            r = math.hypot(top.x, top.y)
            wall_r = C.EDGE_WALL_START * self.radius
            if r > wall_r:  # the steep rim wall pushes back harder the closer a top gets
                k = (r - wall_r) / max(1e-6, self.radius - wall_r)
                ax += -top.x / r * C.EDGE_WALL * k * k
                ay += -top.y / r * C.EDGE_WALL * k * k
            if r > 1e-6:
                spin = top.energy / C.START_ENERGY
                ax += -top.y / r * C.ORBIT_DRIFT * spin * min(1.0, r / 3.0)
                ay += top.x / r * C.ORBIT_DRIFT * spin * min(1.0, r / 3.0)
            act = top.action
            if act in ATTACKS and self.round_t < C.HOMING_SECONDS and not top.hit_done:
                dx, dy = opp.x - top.x, opp.y - top.y
                d = math.hypot(dx, dy) or 1.0
                homing = 12.0 if act is Action.SPECIAL else 9.0
                ax += dx / d * homing * mult
                ay += dy / d * homing * mult
            elif act is Action.CHARGE and r > 1e-6:
                ax += -top.x / r * C.CHARGE_PULL * mult
                ay += -top.y / r * C.CHARGE_PULL * mult
            if top.auto:
                top.steer_x, top.steer_y = self._ai_steer(top, opp)
            sx, sy = top.steer_x, top.steer_y
            sm = math.hypot(sx, sy)
            if sm > 1.0:
                sx, sy = sx / sm, sy / sm
            # Direct drive: the stick sets a target velocity that the top follows almost instantly,
            # independent of the bowl pull, orbit drift and damping that act on the physics velocity.
            tdx, tdy = sx * C.DRIVE_SPEED * mult, sy * C.DRIVE_SPEED * mult
            r_now = math.hypot(top.x, top.y)
            if r_now > 0.9 * self.radius and r_now > 1e-6:
                # You cannot steer yourself out of the stadium: drop the outward part near the rim.
                ox, oy = top.x / r_now, top.y / r_now
                outward = tdx * ox + tdy * oy
                if outward > 0:
                    tdx -= outward * ox
                    tdy -= outward * oy
            kd = 1.0 - math.exp(-C.DRIVE_RESPONSE * dt)
            top.dvx += (tdx - top.dvx) * kd
            top.dvy += (tdy - top.dvy) * kd

            top.vx += ax * dt
            top.vy += ay * dt
            damp = damping * (1.8 if act is Action.GUARD else 1.0)
            f = math.exp(-damp * dt)
            top.vx *= f
            top.vy *= f
            sp = math.hypot(top.vx, top.vy)
            if sp > C.MAX_SPEED:
                top.vx *= C.MAX_SPEED / sp
                top.vy *= C.MAX_SPEED / sp
            top.x += (top.vx + top.dvx) * dt
            top.y += (top.vy + top.dvy) * dt

            # Continuous resource flow: passive spin loss and the action's recovery.
            top.energy -= top.spec.energy_loss * frac
            if top.energy <= 0.0:
                continue  # spun out: no recovery can revive a stopped top
            if act is Action.CHARGE:
                top.energy = min(C.START_ENERGY, top.energy + top.spec.charge_recovery * frac)
            elif act is Action.GUARD:
                top.stability = min(top.spec.max_stability, top.stability + top.spec.guard_recovery * frac)

        self._collide()
        self._check_out()

    def _ai_steer(self, top: Top, opp: Top) -> Tuple[float, float]:
        """Free movement for AI tops: the same x/y steering the human uses (centre = (0, 0)).

        The chosen action decides where to go: Attack and Special chase the rival, Dodge slides
        sideways toward the side with more room, Charge heads for the centre, Guard holds. Near
        the rim every action is blended with a pull back toward the centre. `steer_gain` makes
        Easy AIs sloppier than Hard ones.
        """
        act = top.action
        r = math.hypot(top.x, top.y)
        dx, dy = opp.x - top.x, opp.y - top.y
        d = math.hypot(dx, dy) or 1.0
        ux, uy = dx / d, dy / d
        vx = vy = 0.0
        if act in ATTACKS:
            vx, vy = ux, uy
        elif act is Action.DODGE:
            px, py = -uy, ux
            # pick the perpendicular with more room to the rim
            if math.hypot(top.x + px, top.y + py) > math.hypot(top.x - px, top.y - py):
                px, py = -px, -py
            vx, vy = px, py
        elif act is Action.CHARGE and r > 0.5:
            vx, vy = -top.x / r, -top.y / r
        edge = (r - 0.78 * self.radius) / max(1e-6, 0.22 * self.radius)
        if edge > 0 and r > 1e-6:  # blend in a pull back toward the centre near the rim
            k = min(1.0, edge * top.steer_gain)  # skilled AIs retreat harder
            vx += -top.x / r * k
            vy += -top.y / r * k
        m = math.hypot(vx, vy)
        if m > 1.0:
            vx, vy = vx / m, vy / m
        return vx * top.steer_gain, vy * top.steer_gain

    def _collide(self) -> None:
        a, b = self.t1, self.t2
        dx, dy = b.x - a.x, b.y - a.y
        d = math.hypot(dx, dy)
        min_d = 2.0 * C.BLADE_RADIUS
        if d >= min_d:
            return
        nx, ny = (dx / d, dy / d) if d > 1e-9 else (1.0, 0.0)
        ma, mb = a.mass, b.mass
        # Positional correction (mass-weighted) so tops never overlap.
        overlap = min_d - d
        a.x -= nx * overlap * mb / (ma + mb)
        a.y -= ny * overlap * mb / (ma + mb)
        b.x += nx * overlap * ma / (ma + mb)
        b.y += ny * overlap * ma / (ma + mb)
        rel = ((a.vx + a.dvx) - (b.vx + b.dvx)) * nx + ((a.vy + a.dvy) - (b.vy + b.dvy)) * ny
        if rel > 0:
            j = (1 + C.RESTITUTION) * rel / (1 / ma + 1 / mb)
            a.vx -= j / ma * nx
            a.vy -= j / ma * ny
            b.vx += j / mb * nx
            b.vy += j / mb * ny
        cx, cy = (a.x + b.x) / 2, (a.y + b.y) / 2
        landed = self._hits(a, b, nx, ny)
        kind = "clash" if (rel > 2.5 or landed) else "grind"
        self.events.append({"type": kind, "x": cx, "y": cy, "speed": max(0.0, rel), "landed": landed})

    def _hits(self, a: Top, b: Top, nx: float, ny: float) -> bool:
        """Apply at most one hit per attacker per round; both can land in the same contact."""
        ice = self.stadium is StadiumType.ICE
        push_mult = C.ICE_PUSH_MULT if ice else 1.0
        damping = C.LINEAR_DAMPING * (C.ICE_DAMPING_MULT if ice else 1.0)
        landed = False
        results = []
        for att, dfn, sgn in ((a, b, 1.0), (b, a, -1.0)):
            if att.action not in ATTACKS or att.hit_done:
                continue
            if dfn.action is Action.DODGE and self.time < dfn.evade_until:
                if not att.hit_done:
                    self.events.append({"type": "evade", "player": dfn.player})
                    att.hit_done = True
                continue
            dmg, push, recoil = hit_effects(att.action, dfn.action, att.spec.power)
            results.append((att, dfn, sgn, dmg, push * push_mult, recoil))
        for att, dfn, sgn, dmg, push, recoil in results:  # simultaneous: compute first, then apply
            att.hit_done = True
            dfn.stability -= dmg
            att.stability -= recoil
            att.stats.hits += 1
            att.stats.damage_dealt += dmg
            dfn.stats.damage_taken += dmg
            dfn_damp = damping * (1.8 if dfn.action is Action.GUARD else 1.0)
            dfn.vx += sgn * nx * push * dfn_damp
            dfn.vy += sgn * ny * push * dfn_damp
            landed = True
            self.events.append({"type": "hit", "attacker": att.player, "defender": dfn.player,
                                "action": att.action, "damage": dmg, "recoil": recoil,
                                "defender_action": dfn.action})
        return landed

    # ---- finishes -----------------------------------------------------------------------------

    def _out_reason(self, t: Top) -> Optional[str]:
        if math.hypot(t.x, t.y) > self.radius:
            return "RING_OUT"
        if t.stability <= 0.0:
            return "BURST"
        if t.energy <= 0.0:
            return "SPIN_OUT"
        return None

    def _check_out(self) -> None:
        if self.over:
            return
        r1 = self._out_reason(self.t1)
        r2 = self._out_reason(self.t2)
        if r1 and r2:
            self.t1.out, self.t2.out = r1, r2
            self._finish(0, "DRAW")
        elif r1:
            self.t1.out = r1
            self._finish(2, r1)
        elif r2:
            self.t2.out = r2
            self._finish(1, r2)

    def _finish(self, winner: int, reason: str) -> None:
        self.winner = winner
        self.finish = reason
        self.t1.energy = max(0.0, self.t1.energy)
        self.t2.energy = max(0.0, self.t2.energy)
        self.t1.stability = max(0.0, self.t1.stability)
        self.t2.stability = max(0.0, self.t2.stability)
        self.events.append({"type": "finish", "winner": winner, "reason": reason})

    def points(self) -> Tuple[float, float]:
        return (model.points_score(self.t1.blade(), self.radius), model.points_score(self.t2.blade(), self.radius))
