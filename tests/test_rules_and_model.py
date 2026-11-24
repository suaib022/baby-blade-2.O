"""Spec rules: actions, costs, counters, shrink schedule, finishes, points, no overlap."""

import math

import pytest

from babyblade import config as C
from babyblade.sim import model
from babyblade.sim.actions import COST, Action, hit_effects, is_legal, legal_actions
from babyblade.sim.blades import SPECS, BladeType, StadiumType
from babyblade.sim.model import Blade, State, initial_state, result


def test_blade_table_matches_the_proposal():
    assert (SPECS[BladeType.BALANCED].max_stability, SPECS[BladeType.BALANCED].energy_loss, SPECS[BladeType.BALANCED].power) == (100, 3, 1.0)
    assert (SPECS[BladeType.ATTACKER].max_stability, SPECS[BladeType.ATTACKER].energy_loss, SPECS[BladeType.ATTACKER].power) == (90, 4, 1.25)
    assert (SPECS[BladeType.DEFENDER].max_stability, SPECS[BladeType.DEFENDER].guard_recovery, SPECS[BladeType.DEFENDER].power) == (120, 10, 0.85)
    assert (SPECS[BladeType.STAMINA].energy_loss, SPECS[BladeType.STAMINA].charge_recovery) == (2, 25)


def test_action_costs_and_special_cooldown():
    assert COST == {Action.CHARGE: 0, Action.ATTACK: 8, Action.GUARD: 4, Action.DODGE: 8, Action.SPECIAL: 35}
    assert is_legal(Action.SPECIAL, 35, 3.0, 3.0)
    assert not is_legal(Action.SPECIAL, 35, 2.9, 3.0)
    assert not is_legal(Action.SPECIAL, 34.9, 9.0, 0.0)
    assert legal_actions(0.0, 0.0, 0.0) == [Action.CHARGE]  # Charge is always possible


def test_counter_table():
    dmg_charge, push_charge, _ = hit_effects(Action.ATTACK, Action.CHARGE, 1.0)
    dmg_guard, push_guard, recoil = hit_effects(Action.ATTACK, Action.GUARD, 1.0)
    sp_guard, _, sp_recoil = hit_effects(Action.SPECIAL, Action.GUARD, 1.0)
    sp_charge, sp_push, _ = hit_effects(Action.SPECIAL, Action.CHARGE, 1.0)
    assert dmg_charge == pytest.approx(12 * 1.25)  # attack is effective against charge
    assert dmg_guard == pytest.approx(6.0) and recoil == C.GUARD_ATTACKER_RECOIL  # guard beats attack
    assert sp_guard == pytest.approx(25 * 0.7) and sp_recoil == 0.0  # special partially breaks guard
    assert sp_charge > dmg_charge and sp_push > push_charge  # special is stronger
    assert hit_effects(Action.ATTACK, Action.CHARGE, 1.25)[0] == pytest.approx(15 * 1.25)  # attacker power


def test_shrink_schedule():
    assert [model.radius_after_round(r) for r in (0, 5, 6, 11, 12, 18, 24, 30, 40)] == [10, 10, 9, 9, 8, 7, 6, 6, 6]


def test_round_costs_recovery_and_passive_loss():
    s = initial_state(BladeType.STAMINA, BladeType.DEFENDER)
    s = s._replace(b1=s.b1._replace(energy=50.0), b2=s.b2._replace(stability=100.0))
    n = result(s, Action.CHARGE, Action.GUARD)
    assert n.b1.energy == pytest.approx(50 + 25 - 2)  # stamina charge +25, passive -2
    assert n.b2.energy == pytest.approx(100 - 4 - 3)  # guard costs 4, passive -3
    assert n.b2.stability == pytest.approx(110.0)  # defender guard +10
    assert n.round == 1 and n.time == pytest.approx(3.0)


def test_both_attacks_land_simultaneously():
    s = State(Blade(-1.3, 0, 100, 100, 0, BladeType.BALANCED), Blade(1.3, 0, 100, 100, 0, BladeType.BALANCED),
              10.0, 0, 0.0, StadiumType.CLASSIC)
    n = result(s, Action.ATTACK, Action.ATTACK)
    assert n.b1.stability == pytest.approx(88.0) and n.b2.stability == pytest.approx(88.0)


def test_dodge_avoids_attacks_but_fails_near_edge():
    s = State(Blade(-1.3, 0, 100, 100, 0, BladeType.BALANCED), Blade(1.3, 0, 100, 100, 0, BladeType.BALANCED),
              10.0, 0, 0.0, StadiumType.CLASSIC)
    n = result(s, Action.ATTACK, Action.DODGE)
    assert n.b2.stability == pytest.approx(100.0)  # evaded
    edge = State(Blade(7.6, 0, 100, 100, 0, BladeType.BALANCED), Blade(9.2, 0, 100, 100, 0, BladeType.BALANCED),
                 9.6, 0, 0.0, StadiumType.CLASSIC)
    x, y, ok = model._move(edge.b2, edge.b1, Action.DODGE, edge.radius, 1.0)
    assert not ok  # landing within 0.5 of the boundary: dodge fails


def test_tops_never_overlap_in_the_model():
    s = State(Blade(0.0, 0, 100, 100, 0, BladeType.BALANCED), Blade(0.1, 0, 100, 100, 0, BladeType.BALANCED),
              10.0, 0, 0.0, StadiumType.CLASSIC)
    for a1 in Action:
        for a2 in Action:
            n = result(s, a1, a2)
            assert math.hypot(n.b2.x - n.b1.x, n.b2.y - n.b1.y) >= 2 * C.BLADE_RADIUS - 1e-9


def test_finishes_and_priority():
    base = initial_state(BladeType.BALANCED, BladeType.BALANCED)
    ring = base._replace(b1=base.b1._replace(x=10.5))
    assert model.judge(ring).finish == "RING_OUT" and model.judge(ring).winner == 2
    burst = base._replace(b2=base.b2._replace(stability=0.0))
    assert model.judge(burst).finish == "BURST" and model.judge(burst).winner == 1
    spin = base._replace(b1=base.b1._replace(energy=0.0))
    assert model.judge(spin).finish == "SPIN_OUT"
    both = base._replace(b1=base.b1._replace(energy=0.0), b2=base.b2._replace(stability=0.0))
    assert model.judge(both).winner == 0 and model.judge(both).finish == "DRAW"
    ring_and_burst = base._replace(b1=base.b1._replace(x=11.0, stability=0.0))
    assert model.judge(ring_and_burst).finish == "RING_OUT"  # ring-out has priority


def test_points_decision_after_round_40():
    s = initial_state(BladeType.BALANCED, BladeType.BALANCED)._replace(round=40)
    s = s._replace(b2=s.b2._replace(energy=60.0))
    j = model.judge(s)
    assert j.finish == "POINTS" and j.winner == 1
    tie = initial_state(BladeType.BALANCED, BladeType.BALANCED)._replace(round=40)
    assert model.judge(tie).winner == 0  # equal scores: draw


def test_ice_rink_scales_push():
    s = State(Blade(-1.3, 0, 100, 100, 0, BladeType.BALANCED), Blade(1.3, 0, 100, 100, 0, BladeType.BALANCED),
              10.0, 0, 0.0, StadiumType.CLASSIC)
    classic = result(s, Action.ATTACK, Action.GUARD)
    ice = result(s._replace(stadium=StadiumType.ICE), Action.ATTACK, Action.GUARD)
    assert ice.b2.x > classic.b2.x  # pushed further on ice
