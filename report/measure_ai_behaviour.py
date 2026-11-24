"""Measure each AI's action mix and results by agent, difficulty and blade (for the strategy guide).

    python report/measure_ai_behaviour.py   -> report/data/ai_behaviour.json
"""

import json
import multiprocessing as mp
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from babyblade.ai.agents import make_agent  # noqa: E402
from babyblade.sim.battle import Battle  # noqa: E402
from babyblade.sim.blades import BladeType, StadiumType  # noqa: E402

KINDS = [k.value for k in BladeType]


def work(args):
    agent, diff, blade, stadium, seed = args
    other = "Cyclone" if agent == "Ironclad" else "Ironclad"
    # The AI under test plays a Medium AI of the other kind that uses a Balanced blade.
    ctls = (make_agent(agent, diff, seed), make_agent(other, "Medium", seed + 1))
    b = Battle(BladeType(blade), BladeType.BALANCED, StadiumType(stadium), controllers=ctls, seed=seed)
    b.run_to_end()
    me = b.t1
    return (agent, diff, blade, stadium, dict(me.stats.actions), me.stats.hits, b.winner == 1, b.finish, b.round)


def main():
    tasks = []
    for agent in ("Ironclad", "Cyclone"):
        for diff in ("Easy", "Medium", "Hard"):
            for blade in KINDS:
                for s in range(6):
                    tasks.append((agent, diff, blade, "CLASSIC", 100 + s * 17))
    for agent in ("Ironclad", "Cyclone"):
        for st in ("ICE", "STEEP"):
            for s in range(6):
                tasks.append((agent, "Medium", "BALANCED", st, 300 + s * 17))
    with mp.Pool(max(2, (os.cpu_count() or 4) - 1)) as pool:
        res = pool.map(work, tasks)
    agg = {}
    for agent, diff, blade, st, acts, hits, won, finish, rounds in res:
        k = f"{agent}|{diff}|{blade}|{st}"
        a = agg.setdefault(k, dict(actions=Counter(), hits=0, wins=0, n=0, finishes=Counter(), rounds=0))
        a["actions"].update(acts)
        a["hits"] += hits
        a["wins"] += int(won)
        a["n"] += 1
        a["finishes"][finish] += 1
        a["rounds"] += rounds
    out = {k: dict(actions=dict(v["actions"]), hits=v["hits"] / v["n"], win_rate=v["wins"] / v["n"], n=v["n"],
                   finishes=dict(v["finishes"]), rounds=v["rounds"] / v["n"]) for k, v in agg.items()}
    with open(os.path.join(os.path.dirname(__file__), "data", "ai_behaviour.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
    print("done", len(res), "matches")


if __name__ == "__main__":
    mp.freeze_support()
    main()
