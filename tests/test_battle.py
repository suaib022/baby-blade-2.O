"""Real-time battle: physics, rounds, finishes, determinism."""

import math

import pytest

from babyblade import config as C
from babyblade.ai.agents import Cyclone, Human, Ironclad
from babyblade.sim.actions import Action
from babyblade.sim.battle import Battle
from babyblade.sim.blades import BladeType, StadiumType


def _ai_battle(seed=1, stadium=StadiumType.CLASSIC, kinds=(BladeType.BALANCED, BladeType.ATTACKER)):
    return Battle(kinds[0], kinds[1], stadium, controllers=(Ironclad("Easy", seed=seed), Cyclone("Easy", seed=seed)), seed=seed)


def test_match_runs_to_a_valid_finish_within_120_seconds():
    b = _ai_battle()
    b.run_to_end()
    assert b.over
    assert b.finish in ("RING_OUT", "BURST", "SPIN_OUT", "DRAW", "POINTS")
    assert b.time <= C.ROUNDS * C.ROUND_SECONDS + 1e-6
    assert b.round <= C.ROUNDS


def test_battle_is_deterministic_for_a_seed():
    a, b = _ai_battle(seed=4), _ai_battle(seed=4)
    a.run_to_end()
    b.run_to_end()
    assert (a.winner, a.finish, a.round) == (b.winner, b.finish, b.round)


def test_tops_never_overlap_during_play():
    b = _ai_battle(seed=2)
    step = 1.0 / C.PHYSICS_HZ
    worst = 99.0
    for _ in range(C.PHYSICS_HZ * 30):
        b.update(step, think_budget=1.0)
        if b.over:
            break
        worst = min(worst, math.hypot(b.t1.x - b.t2.x, b.t1.y - b.t2.y))
    assert worst >= 2 * C.BLADE_RADIUS - 1e-6


def test_costs_are_paid_at_round_start_and_special_sets_cooldown():
    h1, h2 = Human(), Human()
    h1.queued = Action.SPECIAL
    h2.queued = Action.GUARD
    b = Battle(BladeType.BALANCED, BladeType.BALANCED, controllers=(h1, h2), seed=3)
    b.update(1.0 / C.PHYSICS_HZ)
    assert b.t1.action is Action.SPECIAL and b.t2.action is Action.GUARD
    assert b.t1.energy == pytest.approx(100 - 35, abs=0.1)
    assert b.t1.stability == pytest.approx(100 - 10, abs=0.5) or b.t1.stability < 90  # self-recoil
    assert b.t1.ready_at == pytest.approx(3.0, abs=0.02)


def test_shrink_happens_after_round_six():
    h1, h2 = Human(), Human()
    b = Battle(BladeType.STAMINA, BladeType.STAMINA, controllers=(h1, h2), seed=5)
    for _ in range(6):
        b.step_round()
    b.update(C.SHRINK_ANIM_SECONDS + 0.1)
    assert not b.over
    assert b.radius == pytest.approx(9.0, abs=1e-6)
    assert any(e["type"] == "shrink" for e in b.events)


def test_ring_out_is_detected():
    h1, h2 = Human(), Human()
    b = Battle(BladeType.BALANCED, BladeType.BALANCED, controllers=(h1, h2), seed=6)
    b.update(0.01)
    b.t1.x, b.t1.y, b.t1.vx, b.t1.vy = 9.9, 0.0, 20.0, 0.0
    b.update(0.05)
    assert b.over and b.finish == "RING_OUT" and b.winner == 2


def test_burst_and_draw():
    h1, h2 = Human(), Human()
    b = Battle(BladeType.BALANCED, BladeType.BALANCED, controllers=(h1, h2), seed=7)
    b.update(0.01)
    b.t2.stability = 0.0
    b.update(0.02)
    assert b.finish == "BURST" and b.winner == 1
    d = Battle(BladeType.BALANCED, BladeType.BALANCED, controllers=(Human(), Human()), seed=7)
    d.update(0.01)
    d.t1.energy = 0.0
    d.t2.stability = 0.0
    d.update(0.02)
    assert d.winner == 0 and d.finish == "DRAW"


def test_steering_moves_the_top():
    h1, h2 = Human(), Human()
    b = Battle(BladeType.BALANCED, BladeType.BALANCED, controllers=(h1, h2), seed=8)
    b.update(0.01)
    x0 = b.t1.x
    b.t1.steer_x = 1.0
    b.update(0.5)
    free = Battle(BladeType.BALANCED, BladeType.BALANCED, controllers=(Human(), Human()), seed=8)
    free.update(0.51)
    assert b.t1.x - x0 > free.t1.x - x0


def test_ai_think_time_is_recorded():
    b = _ai_battle(seed=9)
    b.run_to_end()
    assert b.t1.stats.decisions > 0 and b.t1.stats.think_seconds > 0


def test_ai_tops_steer_and_humans_do_not():
    b = Battle(BladeType.BALANCED, BladeType.BALANCED, controllers=(Ironclad("Easy", seed=1), Human()), seed=2)
    assert b.t1.auto and not b.t2.auto
    assert b.t1.steer_gain == pytest.approx(0.6)  # Easy steers worse than Hard


def test_ai_steering_follows_the_chosen_action():
    b = Battle(BladeType.BALANCED, BladeType.BALANCED, controllers=(Ironclad("Hard", seed=1), Human()), seed=3)
    b.t1.x, b.t1.y, b.t2.x, b.t2.y = -3.0, 0.0, 3.0, 0.0
    b.t1.action = Action.ATTACK
    sx, sy = b._ai_steer(b.t1, b.t2)
    assert sx > 0.9 and abs(sy) < 0.1  # chases the rival along +x
    b.t1.action = Action.CHARGE
    sx, sy = b._ai_steer(b.t1, b.t2)
    assert sx > 0.9  # heads for the centre (0, 0)
    b.t1.action = Action.DODGE
    sx, sy = b._ai_steer(b.t1, b.t2)
    assert abs(sy) > 0.9 and abs(sx) < 0.1  # slides sideways
    b.t1.x, b.t1.y = -9.0, 0.0  # near the rim: pulled back toward the centre
    b.t1.action = Action.GUARD
    assert b._ai_steer(b.t1, b.t2)[0] > 0.5


def test_steering_moves_a_top_in_all_four_directions():
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        b = Battle(BladeType.BALANCED, BladeType.BALANCED, controllers=(Human(), Human()), seed=4)
        b.update(0.01)
        b.t1.vx = b.t1.vy = 0.0
        x0, y0 = b.t1.x, b.t1.y
        b.t1.steer_x, b.t1.steer_y = float(dx), float(dy)
        b.update(0.4)
        assert (b.t1.x - x0) * dx + (b.t1.y - y0) * dy > 0.4


def test_ai_vs_ai_with_free_movement_still_finishes_validly():
    b = Battle(BladeType.BALANCED, BladeType.ATTACKER, controllers=(Ironclad("Medium", 1), Cyclone("Medium", 2)), seed=5)
    b.run_to_end()
    assert b.over and b.finish in ("RING_OUT", "BURST", "SPIN_OUT", "DRAW", "POINTS")


def test_direct_drive_is_instant_and_stops_when_released():
    b = Battle(BladeType.BALANCED, BladeType.BALANCED, controllers=(Human(), Human()), seed=11)
    b.update(0.01)
    b.t1.vx = b.t1.vy = 0.0
    b.t1.steer_x, b.t1.steer_y = 1.0, 0.0
    b.update(0.12)  # ~120 ms: the top is already moving near full drive speed
    assert b.t1.dvx > 0.85 * C.DRIVE_SPEED
    b.t1.steer_x = 0.0
    b.update(0.25)  # released: the drive dies out quickly
    assert abs(b.t1.dvx) < 0.15 * C.DRIVE_SPEED


def test_cannot_steer_out_of_the_stadium():
    b = Battle(BladeType.STAMINA, BladeType.STAMINA, controllers=(Human(), Human()), seed=12)
    b.update(0.01)
    b.t1.x, b.t1.y, b.t1.vx, b.t1.vy = 9.4, 0.0, 0.0, 0.0
    b.t1.steer_x, b.t1.steer_y = 1.0, 0.0  # hold the stick toward the rim
    b.update(1.5)
    assert not (b.over and b.finish == "RING_OUT")
