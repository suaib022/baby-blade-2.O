"""Match setup shared by the setup, battle and results scenes."""

from __future__ import annotations

import random
from dataclasses import dataclass, field, replace
from typing import Callable, Optional, Tuple

from babyblade.ai.agents import Human, make_agent
from babyblade.game.profile import AI_LOOKS, PROFILE, Look
from babyblade.sim.battle import Battle
from babyblade.sim.blades import BladeType, StadiumType


@dataclass
class Side:
    controller: str = "human"  # "human", "Ironclad" or "Cyclone"
    difficulty: str = "Medium"
    look: Look = field(default_factory=Look)

    @property
    def is_human(self) -> bool:
        return self.controller == "human"

    def tag(self, mode_human: bool, player: int) -> str:
        if self.is_human:
            return "YOU"
        return "AI" if mode_human else f"P{player}"

    def title(self) -> str:
        if self.is_human:
            return self.look.name
        return f"{self.controller} · {self.difficulty}"


@dataclass
class MatchSetup:
    p1: Side
    p2: Side
    stadium: StadiumType = StadiumType.CLASSIC
    seed: int = 0
    on_finish: Optional[Callable] = None  # championship matches report their result here

    @property
    def human_mode(self) -> bool:
        return self.p1.is_human or self.p2.is_human

    def swapped(self) -> "MatchSetup":
        return replace(self, p1=self.p2, p2=self.p1)

    def build(self, launch: Tuple[float, float]):
        """Create (battle, human controller or None)."""
        human: Optional[Human] = None
        ctls = []
        for i, side in enumerate((self.p1, self.p2)):
            if side.is_human:
                human = Human()
                ctls.append(human)
            else:
                ctls.append(make_agent(side.controller, side.difficulty, self.seed + i * 101))
        battle = Battle(self.p1.look.kind, self.p2.look.kind, self.stadium, controllers=(ctls[0], ctls[1]),
                        seed=self.seed, launch=launch)
        return battle, human


def ai_side(kind: str, difficulty: str, archetype: Optional[BladeType] = None) -> Side:
    look = replace(AI_LOOKS[kind])
    if archetype is not None:
        look = replace(look, archetype=archetype.value)
    return Side(kind, difficulty, look)


def human_side() -> Side:
    return Side("human", "", replace(PROFILE.look))


def quick_setup(seed: Optional[int] = None) -> MatchSetup:
    return MatchSetup(human_side(), ai_side("Ironclad", "Medium"), StadiumType.CLASSIC,
                      seed if seed is not None else random.randint(0, 99999))
