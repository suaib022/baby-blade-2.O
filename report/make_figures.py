"""Plain black-and-white charts for the report.

    python report/make_figures.py        (needs matplotlib and numpy)
"""

import json
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from babyblade.sim import fuzzy  # noqa: E402

FIG = os.path.join(HERE, "figures")
os.makedirs(FIG, exist_ok=True)
D = json.load(open(os.path.join(HERE, "data", "results.json"), encoding="utf-8"))
plt.rcParams.update({"font.family": "serif", "font.size": 9, "axes.spines.top": False, "axes.spines.right": False})


def save(name):
    plt.tight_layout()
    plt.savefig(os.path.join(FIG, name), dpi=200)
    plt.close()


# Win share of each AI at equal difficulty
fig, ax = plt.subplots(figsize=(5.2, 2.5))
x = np.arange(3)
names = ("Easy", "Medium", "Hard")
iron = [100 * D[f"head2head_{d}"]["wins_a"] / D[f"head2head_{d}"]["matches"] for d in names]
cyc = [100 * D[f"head2head_{d}"]["wins_b"] / D[f"head2head_{d}"]["matches"] for d in names]
drw = [100 * D[f"head2head_{d}"]["draws"] / D[f"head2head_{d}"]["matches"] for d in names]
ax.bar(x - 0.27, iron, 0.27, color="#2a6fdb", label="Ironclad wins")
ax.bar(x, cyc, 0.27, color="#d6382c", label="Cyclone wins")
ax.bar(x + 0.27, drw, 0.27, color="#c8ccd4", edgecolor="#555555", hatch="///", label="Draws")
for i in range(3):
    for dx, v in ((-0.27, iron[i]), (0, cyc[i]), (0.27, drw[i])):
        ax.text(i + dx, v + 1.5, f"{v:.0f}", ha="center", fontsize=8)
ax.set_xticks(x, names)
ax.set_ylabel("Matches (%)")
ax.set_ylim(0, 100)
ax.legend(frameon=False, fontsize=8, loc="upper left")
save("plain_h2h.png")

# Fuzzy sets
mm = np.linspace(0, 1, 300)
ee = np.linspace(0, 100, 300)
xs = np.linspace(0, 100, 300)
fig, axs = plt.subplots(1, 3, figsize=(7.2, 2.1))
styles = ["-", "--", ":"]
for name, ls in zip(("near", "mid", "far"), styles):
    axs[0].plot(mm, [fuzzy.margin_sets(m)[name] for m in mm], "k", ls=ls, label=name)
for name, ls in zip(("low", "mid", "high"), styles):
    axs[1].plot(ee, [fuzzy.energy_sets(e)[name] for e in ee], "k", ls=ls, label=name)
for name, ls in zip(("low", "medium", "high"), styles):
    axs[2].plot(xs, [fuzzy.danger_set(name, x_) for x_ in xs], "k", ls=ls, label=name)
for a, t, xl in zip(axs, ("Edge margin", "Spin energy", "Danger"), ("margin", "energy", "danger")):
    a.set_title(t, fontsize=9)
    a.set_xlabel(xl)
    a.legend(frameon=False, fontsize=7)
axs[0].set_ylabel("membership")
save("plain_fuzzy.png")
print("figures saved")
