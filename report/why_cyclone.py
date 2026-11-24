import json
import multiprocessing as mp
import os
import sys
from collections import Counter

sys.path.insert(0, r"D:\baby-blade-2.0")
from babyblade.tournament import Tournament, TournamentConfig  # noqa: E402

CASES = {
    "A  Ironclad+Defender  vs  Cyclone+Attacker   (your setup)": ("Ironclad", "Cyclone", "DEFENDER", "ATTACKER"),
    "B  Ironclad+Attacker  vs  Cyclone+Defender   (blades swapped)": ("Ironclad", "Cyclone", "ATTACKER", "DEFENDER"),
    "C  Ironclad+Attacker  vs  Cyclone+Attacker   (same blade)": ("Ironclad", "Cyclone", "ATTACKER", "ATTACKER"),
    "D  Ironclad+Defender  vs  Cyclone+Defender   (same blade)": ("Ironclad", "Cyclone", "DEFENDER", "DEFENDER"),
}


def task(a):
    name, (ag_a, ag_b, ba, bb), chunk = a
    cfg = TournamentConfig(ag_a, ag_b, "Medium", "Medium", ba, bb, "CLASSIC", 6, seed=900 + chunk * 77)
    s = Tournament(cfg).run()
    return name, [(r.winner, r.finish, r.rounds) for r in s.records]


if __name__ == "__main__":
    mp.freeze_support()
    tasks = [(n, c, k) for n, c in CASES.items() for k in range(5)]  # 30 matches per case
    res = {}
    with mp.Pool(10) as pool:
        for name, recs in pool.imap_unordered(task, tasks):
            res.setdefault(name, []).extend(recs)
    out = {}
    for name in CASES:
        r = res[name]
        out[name] = {"n": len(r), "ironclad": sum(x[0] == "A" for x in r), "cyclone": sum(x[0] == "B" for x in r),
                     "draws": sum(x[0] == "DRAW" for x in r), "finishes": dict(Counter(x[1] for x in r))}
    json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "why_cyclone.json"), "w"), indent=2)
    for name in CASES:
        r = res[name]
        n = len(r)
        w = Counter(x[0] for x in r)
        f = Counter(x[1] for x in r)
        print(f"{name}\n   n={n}  Ironclad wins {w['A']} ({100*w['A']//n}%)  Cyclone wins {w['B']} ({100*w['B']//n}%)  draws {w['DRAW']}  "
              f"avg rounds {sum(x[2] for x in r)/n:.1f}  finishes {dict(f)}")
