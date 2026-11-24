"""Coach: plain-language tips that explain what is happening and what to do next.

Pure functions over a Battle, so they are easy to test. The battle scene shows them in a
panel while you play; hovering an action button replaces them with that action's details.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from babyblade import config as C
from babyblade.sim.actions import COST, Action
from babyblade.sim.battle import Battle, Top

# (icon name or "", message, severity)  severity: 0 info, 1 caution, 2 urgent
Tip = Tuple[str, str, int]

ACTION_HELP = {
    Action.CHARGE: ("CHARGE · 0 spin", "Recover +20 spin (Stamina +25) and drift to the centre. Safe when the rival is far, but it takes 25% extra damage. Attack beats it."),
    Action.ATTACK: ("ATTACK · 8 spin", "Dash at the rival and hit for 12 damage (x blade power). Beats Charge. Guard halves it and hurts you 3. Dodge makes it miss."),
    Action.GUARD: ("GUARD · 4 spin", "Brace: +5 stability (Defender +10) and half damage from Attack. Special still breaks through for 70%. You are heavy, so hard to push."),
    Action.DODGE: ("DODGE · 8 spin", "Side-step so Attack and Special miss. It fails if it ends within 0.5 of the rim. Good against a rival that is about to strike."),
    Action.SPECIAL: ("SPECIAL · 35 spin", "Big dash: 25 damage and a strong push, breaks Guard (70%). Costs 35 spin, hurts you 10 and needs a 3 second cooldown."),
}

COUNTERS = [
    ("ATTACK", "CHARGE", "Attack beats Charge"),
    ("GUARD", "ATTACK", "Guard beats Attack"),
    ("SPECIAL", "GUARD", "Special breaks Guard"),
    ("DODGE", "SPECIAL", "Dodge dodges Attack and Special"),
]


def _me_tips(b: Battle, me: Top, op: Top) -> List[Tip]:
    tips: List[Tip] = []
    d, label = b.danger(me.player)
    e01 = me.energy / C.START_ENERGY
    s01 = me.stability / me.spec.max_stability
    if label == "HIGH":
        tips.append(("DODGE", "DANGER HIGH: you are close to the rim. Steer toward the centre.", 2))
    if b.round % C.SHRINK_EVERY_ROUNDS == C.SHRINK_EVERY_ROUNDS - 1 and b.radius > C.STADIUM_MIN_RADIUS + 1e-9:
        tips.append(("", "The arena shrinks after this round. Move inward.", 1))
    if me.energy < COST[Action.ATTACK] + 4:
        tips.append(("CHARGE", f"SPIN is very low ({me.energy:.0f}). Charge to recover +20, or you may spin out.", 2))
    elif e01 < 0.3:
        tips.append(("CHARGE", f"SPIN is low ({me.energy:.0f}). Charge soon to avoid spinning out.", 1))
    if s01 < 0.3:
        tips.append(("GUARD", f"BURST GUARD is low ({me.stability:.0f}). Guard heals, Dodge avoids hits.", 2))
    if op.action is Action.CHARGE:
        tips.append(("ATTACK", "The rival is charging: Attack hits it for extra damage.", 0))
    elif op.action is Action.GUARD:
        tips.append(("SPECIAL", "The rival is guarding: Special breaks through; Attack only does half.", 0))
    elif op.action is Action.DODGE:
        tips.append(("GUARD", "The rival is dodging: an Attack would miss. Guard or Charge instead.", 0))
    elif op.action in (Action.ATTACK, Action.SPECIAL):
        tips.append(("DODGE", "The rival is attacking: Dodge makes it miss, Guard softens the hit.", 1))
    if me.energy >= COST[Action.SPECIAL] and b.time >= me.ready_at:
        tips.append(("SPECIAL", "Special is ready: 25 damage and a big push, but it hurts you 10.", 0))
    tips.append(("", "Blades that touch while attacking land hits. Steer to chase or to run.", 0))
    return tips


def tips(b: Battle, player: int, limit: int = 3) -> List[Tip]:
    """Most useful tips for the human `player` (1 or 2); urgent ones first."""
    me, op = (b.t1, b.t2) if player == 1 else (b.t2, b.t1)
    ranked = sorted(_me_tips(b, me, op), key=lambda t: -t[2])
    return ranked[:limit]


def spectator_tips(b: Battle, limit: int = 3) -> List[Tip]:
    """What is going on, for AI-vs-AI viewers."""
    out: List[Tip] = []
    for top, name in ((b.t1, "P1"), (b.t2, "P2")):
        d, label = b.danger(top.player)
        act = top.action
        verb = {Action.CHARGE: "is recovering spin", Action.ATTACK: "is attacking", Action.GUARD: "is guarding",
                Action.DODGE: "is side-stepping", Action.SPECIAL: "is using Special Spin"}[act]
        sev = 2 if label == "HIGH" else 0
        extra = " (DANGER HIGH: near the rim)" if label == "HIGH" else ""
        out.append((act.value, f"{name} {verb}{extra}.", sev))
    nxt = (b.pending.get(1), b.pending.get(2))
    if nxt[0] is not None and nxt[1] is not None:
        names = {Action.CHARGE: "charges", Action.ATTACK: "attacks", Action.GUARD: "guards", Action.DODGE: "dodges", Action.SPECIAL: "uses Special"}
        out.append(("", f"Next round: P1 {names[nxt[0]]}, P2 {names[nxt[1]]}.", 0))
    out.append(("", "Each AI picks one action every 3 seconds and then steers its blade freely.", 0))
    return sorted(out, key=lambda t: -t[2])[:limit]


def hover_help(action: Optional[Action]) -> Optional[Tuple[str, str]]:
    return ACTION_HELP.get(action) if action is not None else None
