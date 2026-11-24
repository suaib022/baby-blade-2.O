"""Abstract round model: the formal game the AI agents search over.

The real-time battle plays rounds out with physics. The agents cannot run physics inside a
search tree, so they reason over this deterministic model, built from the same rule numbers
(config.py): ACTIONS, RESULT, TERMINAL and UTILITY, as taught in the AI Lab.

State is immutable (NamedTuples), which keeps search branches independent and cheap.
"""

from __future__ import annotations

import math
from typing import List, NamedTuple, Optional, Tuple

from babyblade import config as C
from babyblade.sim.actions import ATTACKS, Action, hit_effects, legal_actions, COST
from babyblade.sim.blades import BladeType, StadiumType, spec
from babyblade.sim.fuzzy import blade_danger


class Blade(NamedTuple):
    x: float
    y: float
    energy: float
    stability: float
    ready_at: float  # game time when Special is usable again
    kind: BladeType


class State(NamedTuple):
    b1: Blade
    b2: Blade
    radius: float
    round: int  # completed rounds
    time: float  # game seconds elapsed
    stadium: StadiumType
    winner: Optional[int] = None  # 1, 2, 0 = draw, None = running
    finish: Optional[str] = None  # RING_OUT, BURST, SPIN_OUT, DRAW, POINTS


# ---- helpers ------------------------------------------------------------------------------------

def radius_after_round(completed_round: int) -> float:
    """Spec shrink: -1 after rounds 6, 12, 18, 24; never below 6."""
    shrinks = completed_round // C.SHRINK_EVERY_ROUNDS
    return max(C.STADIUM_MIN_RADIUS, C.STADIUM_START_RADIUS - shrinks * C.SHRINK_STEP)


def separate(x1: float, y1: float, x2: float, y2: float, min_d: float) -> Tuple[float, float, float, float]:
    """Push two centres apart until they are at least min_d apart (equal share each)."""
    dx, dy = x2 - x1, y2 - y1
    d = math.hypot(dx, dy)
    if d >= min_d:
        return x1, y1, x2, y2
    if d < 1e-9:
        ux, uy = 1.0, 0.0
    else:
        ux, uy = dx / d, dy / d
    h = (min_d - d) / 2.0
    return x1 - ux * h, y1 - uy * h, x2 + ux * h, y2 + uy * h


def points_score(b: Blade, radius: float) -> float:
    s = spec(b.kind)
    dist = math.hypot(b.x, b.y)
    centrality = max(0.0, 1.0 - dist / radius) if radius > 0 else 0.0
    return (C.POINTS_W_ENERGY * (b.energy / C.START_ENERGY)
            + C.POINTS_W_STABILITY * (b.stability / s.max_stability)
            + C.POINTS_W_POSITION * centrality)


def eliminated(b: Blade, radius: float) -> Optional[str]:
    """Priority: ring-out > burst > spin-out."""
    if math.hypot(b.x, b.y) > radius + 1e-9:
        return "RING_OUT"
    if b.stability <= 0.0:
        return "BURST"
    if b.energy <= 0.0:
        return "SPIN_OUT"
    return None


def judge(s: State) -> State:
    """Apply win conditions to a state at a round boundary."""
    e1 = eliminated(s.b1, s.radius)
    e2 = eliminated(s.b2, s.radius)
    if e1 and e2:
        return s._replace(winner=0, finish="DRAW")
    if e1:
        return s._replace(winner=2, finish=e1)
    if e2:
        return s._replace(winner=1, finish=e2)
    if s.round >= C.ROUNDS:
        p1, p2 = points_score(s.b1, s.radius), points_score(s.b2, s.radius)
        if abs(p1 - p2) <= C.POINTS_EPSILON:
            return s._replace(winner=0, finish="POINTS")
        return s._replace(winner=1 if p1 > p2 else 2, finish="POINTS")
    return s


def initial_state(kind1: BladeType, kind2: BladeType, stadium: StadiumType = StadiumType.CLASSIC) -> State:
    return State(
        b1=Blade(-4.0, 0.0, C.START_ENERGY, spec(kind1).max_stability, 0.0, kind1),
        b2=Blade(4.0, 0.0, C.START_ENERGY, spec(kind2).max_stability, 0.0, kind2),
        radius=C.STADIUM_START_RADIUS,
        round=0,
        time=0.0,
        stadium=stadium,
    )


# ---- ACTIONS / RESULT / TERMINAL / UTILITY ---------------------------------------------------------

def actions(s: State, player: int) -> List[Action]:
    b = s.b1 if player == 1 else s.b2
    return legal_actions(b.energy, s.time, b.ready_at)


def terminal(s: State) -> bool:
    return s.winner is not None


def _move(b: Blade, opp: Blade, act: Action, radius: float, mult: float) -> Tuple[float, float, bool]:
    """Planned end position for one action, plus whether a dodge succeeds."""
    x, y = b.x, b.y
    if act in ATTACKS:
        dist = C.MOVE_SPECIAL if act is Action.SPECIAL else C.MOVE_ATTACK
        dx, dy = opp.x - x, opp.y - y
        d = math.hypot(dx, dy)
        step = min(dist * mult, max(0.0, d))
        if d > 1e-9:
            x, y = x + dx / d * step, y + dy / d * step
        return x, y, False
    if act is Action.CHARGE:
        d = math.hypot(x, y)
        step = min(C.MOVE_CHARGE * mult, d)
        if d > 1e-9:
            x, y = x - x / d * step, y - y / d * step
        return x, y, False
    if act is Action.DODGE:
        dx, dy = opp.x - x, opp.y - y
        d = math.hypot(dx, dy) or 1.0
        px, py = -dy / d, dx / d  # perpendicular to the line to the opponent
        best = None
        for sgn in (1.0, -1.0):  # dodge toward whichever side keeps more room
            nx, ny = x + sgn * px * C.MOVE_DODGE * mult, y + sgn * py * C.MOVE_DODGE * mult
            margin = radius - math.hypot(nx, ny)
            if best is None or margin > best[2]:
                best = (nx, ny, margin)
        assert best is not None
        return best[0], best[1], best[2] >= C.DODGE_EDGE_MARGIN
    return x, y, False  # GUARD holds its ground


def result(s: State, a1: Action, a2: Action) -> State:
    """Resolve one simultaneous round in the abstract model."""
    if terminal(s):
        return s
    ice = s.stadium is StadiumType.ICE
    mult = C.ICE_MOVE_MULT if ice else 1.0
    push_mult = C.ICE_PUSH_MULT if ice else 1.0
    b1, b2 = s.b1, s.b2
    sp1, sp2 = spec(b1.kind), spec(b2.kind)

    e1 = b1.energy - COST[a1]
    e2 = b2.energy - COST[a2]
    st1, st2 = b1.stability, b2.stability
    r1, r2 = b1.ready_at, b2.ready_at

    x1, y1, dodge1 = _move(b1, b2, a1, s.radius, mult)
    x2, y2, dodge2 = _move(b2, b1, a2, s.radius, mult)
    if s.stadium is StadiumType.STEEP:  # slope drifts both blades inward
        x1, y1, x2, y2 = x1 * 0.93, y1 * 0.93, x2 * 0.93, y2 * 0.93
    min_d = 2.0 * C.BLADE_RADIUS
    x1, y1, x2, y2 = separate(x1, y1, x2, y2, min_d)
    dist = math.hypot(x2 - x1, y2 - y1)

    push1 = push2 = 0.0  # push received by blade 1 / blade 2
    if a1 in ATTACKS and dist <= C.HIT_RANGE and not (a2 is Action.DODGE and dodge2):
        dmg, push, recoil = hit_effects(a1, a2, sp1.power)
        st2 -= dmg
        push2 = push * push_mult
        st1 -= recoil
    if a2 in ATTACKS and dist <= C.HIT_RANGE and not (a1 is Action.DODGE and dodge1):
        dmg, push, recoil = hit_effects(a2, a1, sp2.power)
        st1 -= dmg
        push1 = push * push_mult
        st2 -= recoil
    if a1 is Action.SPECIAL:
        st1 -= C.SPECIAL_SELF_RECOIL
        r1 = s.time + C.SPECIAL_COOLDOWN
    if a2 is Action.SPECIAL:
        st2 -= C.SPECIAL_SELF_RECOIL
        r2 = s.time + C.SPECIAL_COOLDOWN

    if push1 or push2:
        dx, dy = x2 - x1, y2 - y1
        d = math.hypot(dx, dy) or 1.0
        ux, uy = dx / d, dy / d  # from blade 1 toward blade 2
        x1, y1 = x1 - ux * push1, y1 - uy * push1
        x2, y2 = x2 + ux * push2, y2 + uy * push2
        x1, y1, x2, y2 = separate(x1, y1, x2, y2, min_d)

    if a1 is Action.CHARGE:
        e1 += sp1.charge_recovery
    if a2 is Action.CHARGE:
        e2 += sp2.charge_recovery
    if a1 is Action.GUARD:
        st1 += sp1.guard_recovery
    if a2 is Action.GUARD:
        st2 += sp2.guard_recovery

    e1 = min(C.START_ENERGY, e1 - sp1.energy_loss)
    e2 = min(C.START_ENERGY, e2 - sp2.energy_loss)
    st1 = min(sp1.max_stability, st1)
    st2 = min(sp2.max_stability, st2)

    rnd = s.round + 1
    nxt = State(
        b1=Blade(x1, y1, max(0.0, e1), max(0.0, st1), r1, b1.kind),
        b2=Blade(x2, y2, max(0.0, e2), max(0.0, st2), r2, b2.kind),
        radius=s.radius,  # ring-out is judged against the radius the round was played in
        round=rnd,
        time=s.time + C.ROUND_SECONDS,
        stadium=s.stadium,
    )
    nxt = judge(nxt)
    if nxt.winner is None:
        nxt = nxt._replace(radius=radius_after_round(rnd))
    return nxt


# ---- Heuristic and utility ------------------------------------------------------------------------

def heuristic(s: State, player: int) -> float:
    """Score in roughly [-1, 1] from `player`'s view: energy, stability, position, special, danger."""
    me, op = (s.b1, s.b2) if player == 1 else (s.b2, s.b1)
    sm, so = spec(me.kind), spec(op.kind)
    energy = (me.energy - op.energy) / C.START_ENERGY
    stab = me.stability / sm.max_stability - op.stability / so.max_stability
    pos = (math.hypot(op.x, op.y) - math.hypot(me.x, me.y)) / s.radius
    special = (1.0 if s.time >= me.ready_at and me.energy >= COST[Action.SPECIAL] else 0.0) - \
              (1.0 if s.time >= op.ready_at and op.energy >= COST[Action.SPECIAL] else 0.0)
    danger = (blade_danger(op.x, op.y, s.radius, op.energy) - blade_danger(me.x, me.y, s.radius, me.energy)) / 100.0
    return 0.30 * energy + 0.30 * stab + 0.15 * pos + 0.05 * special + 0.20 * danger


def utility(s: State, player: int) -> float:
    """Terminal payoff: win +1, loss -1, draw 0; non-terminal falls back to the heuristic."""
    if s.winner is None:
        return heuristic(s, player)
    if s.winner == 0:
        return 0.0
    return 1.0 if s.winner == player else -1.0
