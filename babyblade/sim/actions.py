"""The five actions, their costs and legality (spec)."""

from __future__ import annotations

import enum
from typing import Dict, List, Tuple

from babyblade import config as C


class Action(str, enum.Enum):
    CHARGE = "CHARGE"
    ATTACK = "ATTACK"
    GUARD = "GUARD"
    DODGE = "DODGE"
    SPECIAL = "SPECIAL"


ORDER: Tuple[Action, ...] = (Action.CHARGE, Action.ATTACK, Action.GUARD, Action.DODGE, Action.SPECIAL)

COST: Dict[Action, float] = {
    Action.CHARGE: C.COST_CHARGE,
    Action.ATTACK: C.COST_ATTACK,
    Action.GUARD: C.COST_GUARD,
    Action.DODGE: C.COST_DODGE,
    Action.SPECIAL: C.COST_SPECIAL,
}

LABEL: Dict[Action, str] = {
    Action.CHARGE: "Charge",
    Action.ATTACK: "Attack",
    Action.GUARD: "Guard",
    Action.DODGE: "Dodge",
    Action.SPECIAL: "Special",
}

ATTACKS = (Action.ATTACK, Action.SPECIAL)


def is_legal(action: Action, energy: float, now: float, special_ready_at: float) -> bool:
    """Energy must cover the cost; Special also needs its cooldown to have expired."""
    if energy + 1e-9 < COST[action]:
        return False
    if action is Action.SPECIAL and now + 1e-9 < special_ready_at:
        return False
    return True


def legal_actions(energy: float, now: float, special_ready_at: float) -> List[Action]:
    acts = [a for a in ORDER if is_legal(a, energy, now, special_ready_at)]
    return acts or [Action.CHARGE]  # Charge costs 0, so it is always available


def hit_effects(attack: Action, defender: Action, power: float) -> Tuple[float, float, float]:
    """(stability damage to defender, push distance, recoil to attacker) for a landed hit."""
    if attack is Action.SPECIAL:
        dmg, push = C.SPECIAL_DAMAGE, C.SPECIAL_PUSH
    else:
        dmg, push = C.ATTACK_DAMAGE, C.ATTACK_PUSH
    recoil = 0.0
    if defender is Action.CHARGE:
        dmg *= C.CHARGING_DAMAGE_MULT
        push *= C.CHARGING_PUSH_MULT
    elif defender is Action.GUARD:
        mult = C.GUARD_SPECIAL_MULT if attack is Action.SPECIAL else C.GUARD_NORMAL_MULT
        dmg *= mult
        push *= mult
        if attack is Action.ATTACK:
            recoil = C.GUARD_ATTACKER_RECOIL
    return dmg * power, push, recoil
