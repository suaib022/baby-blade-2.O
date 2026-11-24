"""Evaluation experiments for the report: headless AI-vs-AI matches on identical rules.

Runs in parallel chunks and writes report/data/results.json.
    python report/run_experiments.py
"""

import json
import multiprocessing as mp
import os
import sys
import time
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from babyblade.tournament import Tournament, TournamentConfig  # noqa: E402
from babyblade.sim.blades import BladeType, StadiumType  # noqa: E402

CHUNK = 6  # matches per task (even, so sides alternate evenly)


def configs():
    out = {}
    for d in ("Easy", "Medium", "Hard"):
        out[f"head2head_{d}"] = dict(agent_a="Ironclad", agent_b="Cyclone", diff_a=d, diff_b=d, matches=24)
    for st in StadiumType:
        out[f"stadium_{st.value}"] = dict(agent_a="Ironclad", agent_b="Cyclone", diff_a="Medium", diff_b="Medium", stadium=st.value, matches=18)
    out["scaling_Ironclad"] = dict(agent_a="Ironclad", agent_b="Ironclad", diff_a="Easy", diff_b="Hard", matches=18)
    out["scaling_Cyclone"] = dict(agent_a="Cyclone", agent_b="Cyclone", diff_a="Easy", diff_b="Hard", matches=18)
    kinds = list(BladeType)
    for i in range(4):
        for j in range(i + 1, 4):
            out[f"blade_{kinds[i].value}_{kinds[j].value}"] = dict(agent_a="Ironclad", agent_b="Ironclad", diff_a="Medium", diff_b="Medium",
                                                                   blade_a=kinds[i].value, blade_b=kinds[j].value, matches=12)
    return out


def task(args):
    key, cfg, chunk = args
    c = dict(cfg)
    n = c.pop("matches")
    c["matches"] = min(CHUNK, n - chunk * CHUNK)
    c["seed"] = 5000 + chunk * 131
    s = Tournament(TournamentConfig(**c)).run()
    return key, chunk, [r.__dict__ for r in s.records]


def main():
    cfgs = configs()
    tasks = []
    for key, cfg in cfgs.items():
        for chunk in range((cfg["matches"] + CHUNK - 1) // CHUNK):
            tasks.append((key, cfg, chunk))
    t0 = time.time()
    print(len(tasks), "tasks on", os.cpu_count(), "cpus", flush=True)
    results = {}
    with mp.Pool(max(2, (os.cpu_count() or 4) - 1)) as pool:
        for i, (key, chunk, recs) in enumerate(pool.imap_unordered(task, tasks), 1):
            results.setdefault(key, []).extend(recs)
            if i % 10 == 0:
                print(i, "/", len(tasks), round(time.time() - t0), "s", flush=True)
    out = {}
    for key, recs in results.items():
        n = len(recs)
        out[key] = dict(
            config=cfgs[key], matches=n,
            wins_a=sum(r["winner"] == "A" for r in recs), wins_b=sum(r["winner"] == "B" for r in recs),
            draws=sum(r["winner"] == "DRAW" for r in recs),
            finishes=dict(Counter(r["finish"] for r in recs)),
            avg_seconds=sum(r["seconds"] for r in recs) / n, avg_rounds=sum(r["rounds"] for r in recs) / n,
            think_a_ms=sum(r["a_think_ms"] for r in recs) / n, think_b_ms=sum(r["b_think_ms"] for r in recs) / n,
        )
    with open(os.path.join(os.path.dirname(__file__), "data", "results.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
    print("done in", round(time.time() - t0), "s", flush=True)


if __name__ == "__main__":
    mp.freeze_support()
    main()
