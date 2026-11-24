"""Player profile: settings and the customized blade look (saved to disk on desktop)."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from typing import Tuple

from babyblade.game import assets as A
from babyblade.sim.blades import BladeType

IS_WEB = sys.platform == "emscripten"

RING_COLORS = [("Azure", (40, 140, 255)), ("Crimson", (255, 64, 52)), ("Emerald", (60, 220, 130)),
               ("Violet", (170, 110, 255)), ("Solar", (255, 190, 50)), ("Neon", (255, 80, 180))]
DISKS = [("Steel", (150, 160, 180)), ("Chrome", (215, 222, 235)), ("Gunmetal", (90, 96, 112)), ("Gold", (220, 180, 90))]
BITS = [("Flat", (120, 230, 175)), ("Spike", (255, 130, 40)), ("Ball", (100, 170, 255)), ("Rush", (255, 220, 80))]
SHAPE_NOTES = {"Dragon": "3 hooked claws", "Storm": "6 razor spikes", "Fortress": "round armour", "Phantom": "4 crescents"}


@dataclass
class Look:
    name: str = "Storm Pegasus"
    ring: int = 0
    shape: str = "Dragon"
    claws: int = 3
    disk: int = 0
    bit: int = 0
    archetype: str = BladeType.BALANCED.value

    def key(self) -> Tuple:
        return (self.ring, self.shape, self.claws, self.disk, self.bit)

    @property
    def kind(self) -> BladeType:
        return BladeType(self.archetype)

    @property
    def color(self):
        return RING_COLORS[self.ring % len(RING_COLORS)][1]


AI_LOOKS = {
    "Ironclad": Look("Ironclad", ring=1, shape="Fortress", claws=4, disk=2, bit=1, archetype=BladeType.DEFENDER.value),
    "Cyclone": Look("Cyclone", ring=3, shape="Storm", claws=5, disk=1, bit=2, archetype=BladeType.ATTACKER.value),
}


@dataclass
class Settings:
    master: float = 0.8
    sfx: float = 0.9
    shake: bool = True
    show_fps: bool = False
    fullscreen: bool = False
    coach: bool = True


@dataclass
class Stats:
    titles: int = 0
    championships: int = 0
    battles: int = 0
    battles_won: int = 0


@dataclass
class Profile:
    settings: Settings = field(default_factory=Settings)
    look: Look = field(default_factory=Look)
    stats: Stats = field(default_factory=Stats)

    @staticmethod
    def path() -> str:
        return os.path.join(os.path.expanduser("~"), ".babyblade2.json")

    @classmethod
    def load(cls) -> "Profile":
        if IS_WEB:
            return cls()
        try:
            with open(cls.path(), "r", encoding="utf-8") as fh:
                data = json.load(fh)
            return cls(Settings(**data.get("settings", {})), Look(**data.get("look", {})), Stats(**data.get("stats", {})))
        except Exception:
            return cls()

    def save(self) -> None:
        if IS_WEB:
            return
        try:
            with open(self.path(), "w", encoding="utf-8") as fh:
                json.dump({"settings": asdict(self.settings), "look": asdict(self.look), "stats": asdict(self.stats)}, fh, indent=2)
        except Exception:
            pass


PROFILE = Profile.load()


@lru_cache(maxsize=24)
def _art(key: Tuple, radius: int) -> A.TopArt:
    ring, shape, claws, disk, bit = key
    return A.TopArt(radius, RING_COLORS[ring % len(RING_COLORS)][1], shape, claws,
                    DISKS[disk % len(DISKS)][1], BITS[bit % len(BITS)][1])


def art_for(look: Look, radius: int) -> A.TopArt:
    return _art(look.key(), radius)
