"""Presentation layer: every scene runs headless, inputs reach the battle, tournament stats."""

import json
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402
import pytest  # noqa: E402

from babyblade.game import inputs  # noqa: E402
from babyblade.game.app import App  # noqa: E402
from babyblade.game.match import MatchSetup, ai_side, human_side  # noqa: E402
from babyblade.sim.actions import Action  # noqa: E402
from babyblade.sim.blades import BladeType, StadiumType  # noqa: E402
from babyblade.tournament import Tournament, TournamentConfig  # noqa: E402


def run_scene(scene, frames=20):
    app = App(first_scene=scene)
    app.setup()
    for _ in range(frames):
        app.tick()
    return app


def key(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="", scancode=0)


@pytest.mark.parametrize("name", ["title", "setup_h", "setup_ai", "customize", "howto", "settings", "tournament"])
def test_every_scene_renders(name):
    from babyblade.game.scenes import customize, howto, settings, setup, title, tournament
    scene = {
        "title": lambda: title.TitleScene(),
        "setup_h": lambda: setup.SetupScene(human=True),
        "setup_ai": lambda: setup.SetupScene(human=False),
        "customize": lambda: customize.CustomizeScene(),
        "howto": lambda: howto.HowToScene(),
        "settings": lambda: settings.SettingsScene(),
        "tournament": lambda: tournament.TournamentScene(),
    }[name]()
    app = run_scene(scene, 15)
    assert app.scene is scene


def _human_battle():
    from babyblade.game.scenes.battle import BattleScene
    setup = MatchSetup(human_side(), ai_side("Ironclad", "Easy", BladeType.BALANCED), StadiumType.CLASSIC, 3)
    scene = BattleScene(setup)
    app = run_scene(scene, 160)  # launch countdown is 2.4 s
    return app, scene


def test_launch_then_fight_and_keys_queue_actions():
    app, scene = _human_battle()
    assert scene.phase == "fight" and scene.battle is not None
    scene.event(key(pygame.K_3))
    assert scene.human.queued is Action.GUARD
    scene.event(key(pygame.K_4))
    assert scene.human.queued is Action.SPECIAL
    scene.event(key(pygame.K_SPACE))
    assert scene.human.queued is Action.DODGE
    for _ in range(600):  # fixed 1/60 s steps: 10 s of play, minus hit-stop freezes
        scene.update(1 / 60)
        if scene.battle.over:
            break
    assert scene.battle.round >= 2 or scene.battle.over  # rounds keep advancing in real time


def test_steering_input_reaches_the_human_top():
    app, scene = _human_battle()
    scene.stick.press("mouse", (scene.stick.center[0] + 60, scene.stick.center[1]))
    app.tick()
    top = scene.battle.t1
    assert top.steer_x > 0.5


def test_pause_freezes_the_battle():
    app, scene = _human_battle()
    scene.event(key(pygame.K_p))
    assert scene.paused
    t = scene.battle.time
    for _ in range(30):
        app.tick()
    assert scene.battle.time == t
    scene.event(key(pygame.K_ESCAPE))
    assert not scene.paused


def test_ai_vs_ai_step_and_speed():
    from babyblade.game.scenes.battle import BattleScene
    setup = MatchSetup(ai_side("Ironclad", "Easy"), ai_side("Cyclone", "Easy"), StadiumType.ICE, 4)
    scene = BattleScene(setup)
    run_scene(scene, 150)
    r = scene.battle.round
    scene._step()
    assert scene.battle.round == r + 1 and not scene.playing
    scene._speed(4)
    assert scene.speed == 4


def test_input_mapping():
    assert inputs.nav(key(pygame.K_UP)) == "up"
    assert inputs.nav(key(pygame.K_RETURN)) == "confirm"
    assert inputs.battle_action(key(pygame.K_1)) is Action.CHARGE
    assert inputs.battle_action(pygame.event.Event(pygame.JOYBUTTONDOWN, button=5, instance_id=0)) is Action.SPECIAL
    assert inputs.is_pause(key(pygame.K_p))


def test_tournament_statistics_and_export(tmp_path):
    cfg = TournamentConfig("Ironclad", "Cyclone", "Easy", "Easy", matches=3, seed=5)
    s = Tournament(cfg).run()
    assert s.played == 3
    assert s.wins("A") + s.wins("B") + s.draws == 3
    assert sum(s.finishes().values()) == 3
    assert s.avg_seconds > 0 and s.avg_rounds > 0
    assert [r.a_side for r in s.records] == [1, 2, 1]  # sides alternate
    folder = s.export(str(tmp_path / "out"))
    data = json.load(open(os.path.join(folder, "summary.json"), encoding="utf-8"))
    assert data["played"] == 3 and "finishes" in data
    assert os.path.exists(os.path.join(folder, "matches.csv"))


def test_audio_initializes_or_stays_silent():
    from babyblade.game.audio import AUDIO
    pygame.init()
    AUDIO.init()
    AUDIO.finish_loading()
    AUDIO.play("clash0")
    AUDIO.hum(1, 0.8, True)
    AUDIO.stop_hums()  # must not raise with or without a device


def test_screen_guide_freezes_the_battle_and_explains_every_item():
    app, scene = _human_battle()
    scene.event(key(pygame.K_h))
    assert scene.guide
    t = scene.battle.time
    for _ in range(30):
        app.tick()
    assert scene.battle.time == t  # frozen while the guide is open
    items = scene._guide_items()
    terms = " ".join(i[1] for i in items)
    for needed in ("SPIN", "BURST GUARD", "SPECIAL", "DANGER", "NOW / NEXT", "AI DECISION", "ROUND", "STADIUM", "COACH", "CONTROLS"):
        assert needed in terms
    assert all(len(i[2]) > 20 for i in items)  # every term has a real explanation
    scene.event(key(pygame.K_3))  # any key closes it, without also queueing an action
    assert not scene.guide


def test_guide_button_opens_it_and_ai_mode_lists_the_ai_controls():
    from babyblade.game.scenes.battle import BattleScene
    setup = MatchSetup(ai_side("Ironclad", "Easy"), ai_side("Cyclone", "Easy"), StadiumType.CLASSIC, 6)
    scene = BattleScene(setup)
    run_scene(scene, 150)
    scene.event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=scene.GUIDE_BTN.center))
    assert scene.guide
    assert any(i[1] == "CONTROLS" for i in scene._guide_items())
