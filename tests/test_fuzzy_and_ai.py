"""Mamdani danger, heuristic and the two AI agents."""

import pytest

from babyblade.ai.agents import Cyclone, Human, Ironclad, make_agent
from babyblade.sim import fuzzy, model
from babyblade.sim.actions import Action
from babyblade.sim.blades import BladeType, StadiumType
from babyblade.sim.model import Blade, State, initial_state


def test_membership_functions():
    assert fuzzy.tri(5, 0, 5, 10) == 1.0
    assert fuzzy.tri(2.5, 0, 5, 10) == pytest.approx(0.5)
    assert fuzzy.trap(0.5, 0, 0.2, 0.8, 1) == 1.0
    assert fuzzy.trap(1.5, 0, 0.2, 0.8, 1) == 0.0


def test_danger_rises_near_edge_and_low_energy():
    safe, _ = fuzzy.infer(margin=0.9, energy=95)
    risky, _ = fuzzy.infer(margin=0.05, energy=15)
    assert safe < 34 and fuzzy.label(safe) == "LOW"
    assert risky > 67 and fuzzy.label(risky) == "HIGH"


def test_or_max_aggregation_and_centroid_bounds():
    crisp, strength = fuzzy.infer(margin=0.3, energy=50)
    assert set(strength) == {"low", "medium", "high"}
    assert 0 <= crisp <= 100
    assert max(strength.values()) > 0


def test_fast_grid_tracks_full_inference():
    for m in (0.0, 0.33, 0.71, 1.0):
        for e in (0, 37, 64, 100):
            assert abs(fuzzy.danger_fast(m, e) - fuzzy.infer(m, e)[0]) < 3.0


def test_heuristic_prefers_the_stronger_blade():
    s = initial_state(BladeType.BALANCED, BladeType.BALANCED)
    weak2 = s._replace(b2=s.b2._replace(stability=30.0, energy=40.0))
    assert model.heuristic(weak2, 1) > 0 > model.heuristic(weak2, 2)


@pytest.mark.parametrize("agent_cls", [Ironclad, Cyclone])
@pytest.mark.parametrize("difficulty", ["Easy", "Medium"])
def test_agents_return_legal_actions(agent_cls, difficulty):
    s = initial_state(BladeType.BALANCED, BladeType.ATTACKER)._replace(b1=initial_state(BladeType.BALANCED, BladeType.ATTACKER).b1._replace(energy=20.0))
    act = agent_cls(difficulty, seed=3).decide(s, 1)
    assert act in model.actions(s, 1)
    assert Action.SPECIAL not in model.actions(s, 1)


def test_agents_take_a_winning_hit():
    # Opponent is one hit from bursting and is charging-prone: attacking ends the match.
    s = State(Blade(-1.3, 0, 100, 100, 0, BladeType.ATTACKER), Blade(1.3, 0, 100, 8.0, 0, BladeType.BALANCED),
              10.0, 10, 30.0, StadiumType.CLASSIC)
    for agent in (Ironclad("Hard", seed=1), Cyclone("Hard", seed=1)):
        act = agent.decide(s, 1)
        assert act in (Action.ATTACK, Action.SPECIAL)


def test_ironclad_is_deterministic_and_reports_info():
    s = initial_state(BladeType.BALANCED, BladeType.BALANCED)
    a = Ironclad("Medium", seed=5)
    b = Ironclad("Medium", seed=5)
    assert a.decide(s, 1) == b.decide(s, 1)
    assert a.info["depth"] == 2 and a.info["nodes"] > 0


def test_cyclone_is_deterministic_with_a_seed():
    s = initial_state(BladeType.BALANCED, BladeType.STAMINA)
    a = Cyclone("Medium", seed=7)
    b = Cyclone("Medium", seed=7)
    assert a.decide(s, 2) == b.decide(s, 2)
    assert a.info["iterations"] > 0 and sum(a.info["visits"].values()) > 0


def test_human_choice_falls_back_when_illegal():
    h = Human()
    s = initial_state(BladeType.BALANCED, BladeType.BALANCED)
    s = s._replace(b1=s.b1._replace(energy=5.0))
    h.queued = Action.SPECIAL
    h.begin(s, 1)
    assert h.choice() == Action.CHARGE


def test_make_agent():
    assert isinstance(make_agent("ironclad", "Easy"), Ironclad)
    assert isinstance(make_agent("cyclone", "Hard"), Cyclone)
