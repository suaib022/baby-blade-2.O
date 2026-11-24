"""Capture the game screens used in the report (headless). Output: report/figures/shots/*.png"""

import os
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT)
import pygame  # noqa: E402

from babyblade.game.app import App  # noqa: E402
from babyblade.game.match import MatchSetup, ai_side, human_side  # noqa: E402
from babyblade.game.scenes.battle import BattleScene  # noqa: E402
from babyblade.game.scenes.championship import ChampionshipScene  # noqa: E402
from babyblade.game.scenes.customize import CustomizeScene  # noqa: E402
from babyblade.game.scenes.howto import HowToScene  # noqa: E402
from babyblade.game.scenes.results import ResultsScene  # noqa: E402
from babyblade.game.scenes.setup import SetupScene  # noqa: E402
from babyblade.game.scenes.title import TitleScene  # noqa: E402
from babyblade.game.scenes.tournament import TournamentScene  # noqa: E402
from babyblade.sim.actions import Action  # noqa: E402
from babyblade.sim.blades import BladeType, StadiumType  # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), "figures", "shots")
os.makedirs(OUT, exist_ok=True)


def snap(name, scene, frames, hook=None):
    app = App(first_scene=scene)
    app.setup()
    for i in range(frames):
        app.tick()
        if hook:
            hook(app, scene, i)
    pygame.image.save(app.screen, os.path.join(OUT, name + ".png"))
    app.stack.clear()
    pygame.quit()
    return app


def human_match():
    return MatchSetup(human_side(), ai_side("Cyclone", "Hard", BladeType.ATTACKER), StadiumType.ICE, 7)


def hook_attack(app, scene, i):
    if scene.human is not None and i == 380:
        scene.human.queued = Action.ATTACK


snap("01_title", TitleScene(), 90)
snap("02_setup", SetupScene(True), 20)
snap("03_customize", CustomizeScene(), 20)
snap("04_howto", HowToScene(), 10)
s = BattleScene(human_match())
snap("05_battle_human", s, 560, hook_attack)
s = BattleScene(human_match())


def hook_guide(app, scene, i):
    if i == 520:
        scene.guide = True


snap("06_screen_guide", s, 530, hook_guide)
ai = MatchSetup(ai_side("Ironclad", "Hard", BladeType.DEFENDER), ai_side("Cyclone", "Hard", BladeType.ATTACKER), StadiumType.STEEP, 11)
snap("07_battle_ai", BattleScene(ai), 900, lambda app, sc, i: None)


def finish_hook(app, scene, i):
    if i == 360 and scene.battle is not None:
        scene.battle.t2.stability = 0.5
        scene.battle.t1.x, scene.battle.t1.y = scene.battle.t2.x - 2.5, scene.battle.t2.y
        scene.battle.t1.action = Action.ATTACK
        scene.battle.t1.hit_done = False
        scene.battle.t1.vx, scene.battle.t1.vy = 12, 0


snap("08_finish_banner", BattleScene(human_match()), 400, finish_hook)
_setup = human_match()
_battle, _human = _setup.build((0.8, 0.8))
_human.queued = Action.ATTACK
_battle.run_to_end()
snap("09_results", ResultsScene(_setup, _battle, ("YOU", "AI")), 30)
snap("10_championship", ChampionshipScene(), 20)


def bench_hook(app, scene, i):
    if i == 2:
        scene.n.index = 0
        scene._run()


snap("11_benchmark", TournamentScene(), 400, bench_hook)
print("screenshots saved to", OUT)
