"""Championship bracket logic, coach tips, and the championship / coach screens."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402
import pytest  # noqa: E402

from babyblade.ai.agents import Human  # noqa: E402
from babyblade.championship import Championship, default_field  # noqa: E402
from babyblade.game import coach  # noqa: E402
from babyblade.sim.actions import Action  # noqa: E402
from babyblade.sim.battle import Battle  # noqa: E402
from babyblade.sim.blades import BladeType  # noqa: E402


class FakeBattle:
    """Minimal stand-in for a finished player battle."""

    def __init__(self, winner, finish="BURST"):
        self.winner, self.finish = winner, finish


def test_bracket_has_eight_entrants_and_one_player():
    c = Championship(BladeType.BALANCED, seed=1)
    assert len(c.entrants) == 8 and sum(e.is_player for e in c.entrants) == 1
    assert [len(r) for r in c.rounds] == [4, 2, 1]
    assert [m.best_of for r in c.rounds for m in r] == [1, 1, 1, 1, 1, 1, 3]
    assert c.rounds[0][0].a.is_player  # the player is in the first quarter-final


def test_ai_matches_are_simulated_and_winners_advance():
    c = Championship(BladeType.BALANCED, seed=2)
    played = c.simulate_ai_matches()
    assert len(played) >= 3 and all(m.winner is not None for m in played)  # incl. an AI-only semi-final
    for m in played:
        if m.round == 0:
            nxt = c.rounds[1][m.index // 2]
            assert m.winner in (nxt.a, nxt.b)


def test_player_wins_the_cup_and_series_scoring():
    c = Championship(BladeType.BALANCED, seed=3)
    for _ in range(12):
        c.simulate_ai_matches()
        m = c.next_player_match()
        if m is None:
            break
        c.record_player_battle(m, FakeBattle(1))  # the player is side 1 and always wins
    assert c.over and c.champion.is_player and c.player_result() == "Champion"
    final = c.rounds[2][0]
    assert (final.wins_a + final.wins_b) == 2 and final.needed == 2  # best of three, won 2-0


def test_player_eliminated_then_champion_is_still_decided():
    c = Championship(BladeType.BALANCED, seed=4)
    c.simulate_ai_matches()
    c.record_player_battle(c.next_player_match(), FakeBattle(2))  # the player loses the quarter-final
    assert c.player_eliminated and c.player_out_round == 0
    c.finish_without_player()
    assert c.over and not c.champion.is_player
    assert c.player_result().startswith("Eliminated in the quarter-final")


def test_draws_are_replayed_not_counted():
    c = Championship(BladeType.BALANCED, seed=5)
    m = c.rounds[0][0]
    m.record(None)
    assert m.winner is None and m.wins_a == m.wins_b == 0


def test_coach_warns_about_low_spin_and_danger():
    b = Battle(BladeType.BALANCED, BladeType.BALANCED, controllers=(Human(), Human()), seed=1)
    b.update(0.01)
    b.t1.energy = 8.0
    msgs = " ".join(t[1] for t in coach.tips(b, 1, limit=5))
    assert "SPIN" in msgs and "Charge" in msgs
    b.t1.x, b.t1.y = 9.0, 0.0
    msgs = " ".join(t[1] for t in coach.tips(b, 1, limit=5))
    assert "DANGER HIGH" in msgs
    assert coach.tips(b, 1)[0][2] == 2  # urgent tips come first


def test_coach_reads_the_rivals_action_and_hover_help_exists():
    b = Battle(BladeType.BALANCED, BladeType.BALANCED, controllers=(Human(), Human()), seed=2)
    b.update(0.01)
    b.t2.action = Action.CHARGE
    assert any("charging" in t[1] for t in coach.tips(b, 1, limit=6))
    for act in Action:
        title, text = coach.hover_help(act)
        assert len(text) > 40
    assert len(coach.spectator_tips(b)) >= 2


def test_championship_scene_runs_and_builds_a_play_button():
    from babyblade.game.app import App
    from babyblade.game.scenes.championship import ChampionshipScene
    app = App(first_scene=ChampionshipScene())
    app.setup()
    for _ in range(10):
        app.tick()
    scene = app.scene
    assert scene.champ.next_player_match() is not None
    assert any("Play" in getattr(w, "label", "") for w in scene.menu.widgets)
    scene._play_match()  # starts a real battle scene
    assert type(app.scene).__name__ == "BattleScene" and app.scene.setup.on_finish is not None


def test_no_axes_or_coordinates_are_drawn():
    import inspect
    from babyblade.game import arena_view
    src = inspect.getsource(arena_view)
    assert "_axes" not in src and "X / Y" not in src
