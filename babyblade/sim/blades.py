"""Blade archetypes (spec table) and stadium types."""

from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Dict


class BladeType(str, enum.Enum):
    BALANCED = "BALANCED"
    ATTACKER = "ATTACKER"
    DEFENDER = "DEFENDER"
    STAMINA = "STAMINA"


class StadiumType(str, enum.Enum):
    CLASSIC = "CLASSIC"
    ICE = "ICE"
    STEEP = "STEEP"


@dataclass(frozen=True)
class BladeSpec:
    blade_type: BladeType
    name: str
    max_stability: float
    energy_loss: float  # per round
    power: float
    guard_recovery: float
    charge_recovery: float
    blurb: str


SPECS: Dict[BladeType, BladeSpec] = {
    BladeType.BALANCED: BladeSpec(BladeType.BALANCED, "Balanced", 100.0, 3.0, 1.00, 5.0, 20.0,
                                  "No weak spot, no special edge."),
    BladeType.ATTACKER: BladeSpec(BladeType.ATTACKER, "Attacker", 90.0, 4.0, 1.25, 5.0, 20.0,
                                  "Hits 25% harder, burns spin faster."),
    BladeType.DEFENDER: BladeSpec(BladeType.DEFENDER, "Defender", 120.0, 3.0, 0.85, 10.0, 20.0,
                                  "Toughest shell; Guard heals 10."),
    BladeType.STAMINA: BladeSpec(BladeType.STAMINA, "Stamina", 100.0, 2.0, 1.00, 5.0, 25.0,
                                 "Slowest spin loss; Charge gives 25."),
}

STADIUM_NAMES: Dict[StadiumType, str] = {
    StadiumType.CLASSIC: "Classic Dish",
    StadiumType.ICE: "Ice Rink",
    StadiumType.STEEP: "Steep Bowl",
}

STADIUM_BLURBS: Dict[StadiumType, str] = {
    StadiumType.CLASSIC: "Standard battle environment.",
    StadiumType.ICE: "Faster movement, 25% bigger pushes.",
    StadiumType.STEEP: "Steep slope pulls blades to the centre.",
}


def spec(blade_type: BladeType) -> BladeSpec:
    return SPECS[blade_type]
