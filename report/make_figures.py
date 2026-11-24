"""Generate report figures from report/data/results.json and the game's own fuzzy system.

    python report/make_figures.py        (needs matplotlib and numpy)
"""

import json
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, ".."))
from babyblade.sim import fuzzy  # noqa: E402

FIG = os.path.join(HERE, "figures")
os.makedirs(FIG, exist_ok=True)
D = json.load(open(os.path.join(HERE, "data", "results.json"), encoding="utf-8"))
BLUE, RED, GREY, GOLD, GREEN = "#2a6fdb", "#d6382c", "#8a93a6", "#e0a800", "#2e9e6b"
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 100})


def save(name):
    plt.tight_layout()
    plt.savefig(os.path.join(FIG, name), dpi=200)
    plt.close()


# 1. Head to head by difficulty -------------------------------------------------------------
fig, ax = plt.subplots(figsize=(6.4, 3.2))
labels, a, b, d = [], [], [], []
for diff in ("Easy", "Medium", "Hard"):
    r = D[f"head2head_{diff}"]
    n = r["matches"]
    labels.append(f"{diff}\n(n={n})")
    a.append(100 * r["wins_a"] / n)
    b.append(100 * r["wins_b"] / n)
    d.append(100 * r["draws"] / n)
x = np.arange(3)
ax.bar(x, a, color=BLUE, label="Ironclad (Minimax) wins")
ax.bar(x, d, bottom=a, color=GREY, label="Draws")
ax.bar(x, b, bottom=np.array(a) + np.array(d), color=RED, label="Cyclone (MCTS) wins")
for i in range(3):
    ax.text(i, a[i] / 2, f"{a[i]:.0f}%", ha="center", va="center", color="white", fontweight="bold")
    ax.text(i, a[i] + d[i] + b[i] / 2, f"{b[i]:.0f}%", ha="center", va="center", color="white", fontweight="bold")
ax.set_xticks(x, labels)
ax.set_ylabel("Share of matches (%)")
ax.set_title("Ironclad vs Cyclone at equal difficulty (Classic Dish, Balanced blades)")
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=3, frameon=False, fontsize=8)
save("fig_h2h.png")

# 2. Difficulty scaling -----------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(5.2, 3.0))
for i, (key, name) in enumerate((("scaling_Ironclad", "Ironclad"), ("scaling_Cyclone", "Cyclone"))):
    r = D[key]
    n = r["matches"]
    ax.bar(i - 0.18, 100 * r["wins_a"] / n, 0.36, color=GREY, label="Easy" if i == 0 else None)
    ax.bar(i + 0.18, 100 * r["wins_b"] / n, 0.36, color=GREEN, label="Hard" if i == 0 else None)
    ax.text(i - 0.18, 100 * r["wins_a"] / n + 2, f"{100 * r['wins_a'] / n:.0f}%", ha="center")
    ax.text(i + 0.18, 100 * r["wins_b"] / n + 2, f"{100 * r['wins_b'] / n:.0f}%", ha="center")
ax.set_xticks([0, 1], ["Ironclad Easy vs Hard", "Cyclone Easy vs Hard"])
ax.set_ylim(0, 110)
ax.set_ylabel("Win rate (%)")
ax.set_title("Difficulty levels are ordered (18 matches each)")
ax.legend(frameon=False)
save("fig_scaling.png")

# 3. Finish types per experiment --------------------------------------------------------------
fin_names = ["RING_OUT", "BURST", "SPIN_OUT", "POINTS", "DRAW"]
fin_cols = [GOLD, RED, "#1fa2c9", GREEN, GREY]
rows = [("head2head_Easy", "Easy"), ("head2head_Medium", "Medium"), ("head2head_Hard", "Hard"),
        ("stadium_CLASSIC", "Classic Dish"), ("stadium_ICE", "Ice Rink"), ("stadium_STEEP", "Steep Bowl")]
fig, ax = plt.subplots(figsize=(6.4, 3.2))
left = np.zeros(len(rows))
for fn, fc in zip(fin_names, fin_cols):
    vals = np.array([100 * D[k]["finishes"].get(fn, 0) / D[k]["matches"] for k, _ in rows])
    ax.barh(range(len(rows)), vals, left=left, color=fc, label=fn.replace("_", "-").title())
    left += vals
ax.set_yticks(range(len(rows)), [r[1] for r in rows])
ax.invert_yaxis()
ax.set_xlabel("Share of matches (%)")
ax.set_title("How matches finish")
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=5, frameon=False, fontsize=8)
save("fig_finish.png")

# 4. Stadium comparison -------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(5.2, 3.0))
names = [("stadium_CLASSIC", "Classic Dish"), ("stadium_ICE", "Ice Rink"), ("stadium_STEEP", "Steep Bowl")]
ro = [100 * D[k]["finishes"].get("RING_OUT", 0) / D[k]["matches"] for k, _ in names]
sec = [D[k]["avg_seconds"] for k, _ in names]
ax.bar(range(3), ro, color=GOLD)
for i, v in enumerate(ro):
    ax.text(i, v + 1, f"{v:.0f}%", ha="center")
ax.set_xticks(range(3), [n for _, n in names])
ax.set_ylabel("Ring-out finishes (%)")
ax2 = ax.twinx()
ax2.plot(range(3), sec, "o--", color=BLUE)
ax2.set_ylabel("Average duration (s)", color=BLUE)
ax2.set_ylim(0, 120)
ax2.spines["right"].set_visible(True)
ax.set_title("Stadium effect (Ironclad vs Cyclone, Medium)")
save("fig_stadium.png")

# 5. Decision time -------------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(5.2, 3.0))
ia = [D[f"head2head_{d}"]["think_a_ms"] for d in ("Easy", "Medium", "Hard")]
cb = [D[f"head2head_{d}"]["think_b_ms"] for d in ("Easy", "Medium", "Hard")]
x = np.arange(3)
ax.bar(x - 0.18, ia, 0.36, color=BLUE, label="Ironclad (Minimax)")
ax.bar(x + 0.18, cb, 0.36, color=RED, label="Cyclone (MCTS)")
for i in range(3):
    ax.text(i - 0.18, ia[i] + 2, f"{ia[i]:.1f}", ha="center", fontsize=8)
    ax.text(i + 0.18, cb[i] + 2, f"{cb[i]:.0f}", ha="center", fontsize=8)
ax.set_xticks(x, ["Easy", "Medium", "Hard"])
ax.set_ylabel("Mean decision time (ms)")
ax.set_title("Search cost per decision")
ax.legend(frameon=False)
save("fig_think.png")

# 6. Blade archetype matrix ------------------------------------------------------------------------
kinds = ["BALANCED", "ATTACKER", "DEFENDER", "STAMINA"]
M = np.full((4, 4), np.nan)
for i in range(4):
    for j in range(i + 1, 4):
        r = D[f"blade_{kinds[i]}_{kinds[j]}"]
        n = r["matches"]
        M[i, j] = (r["wins_a"] + 0.5 * r["draws"]) / n
        M[j, i] = 1 - M[i, j]
fig, ax = plt.subplots(figsize=(4.6, 3.9))
im = ax.imshow(M, cmap="RdYlBu", vmin=0, vmax=1)
for i in range(4):
    for j in range(4):
        ax.text(j, i, "-" if i == j else f"{100 * M[i, j]:.0f}%", ha="center", va="center", fontsize=10)
ax.set_xticks(range(4), [k.title() for k in kinds], rotation=30)
ax.set_yticks(range(4), [k.title() for k in kinds])
ax.set_xlabel("Opponent")
ax.set_ylabel("Blade")
ax.set_title("Archetype matchups (win rate, draw = 1/2)")
plt.colorbar(im, fraction=0.046)
save("fig_blades.png")

# 7. Fuzzy sets and control surface -----------------------------------------------------------------
mm = np.linspace(0, 1, 300)
ee = np.linspace(0, 100, 300)
fig, axs = plt.subplots(1, 3, figsize=(10, 2.8))
for name, col in (("near", RED), ("mid", GOLD), ("far", GREEN)):
    axs[0].plot(mm, [fuzzy.margin_sets(m)[name] for m in mm], color=col, label=name)
axs[0].set_title("Input 1: edge margin")
axs[0].set_xlabel("margin = (R - distance) / R")
for name, col in (("low", RED), ("mid", GOLD), ("high", GREEN)):
    axs[1].plot(ee, [fuzzy.energy_sets(e)[name] for e in ee], color=col, label=name)
axs[1].set_title("Input 2: spin energy")
axs[1].set_xlabel("energy")
xs = np.linspace(0, 100, 300)
for name, col in (("low", GREEN), ("medium", GOLD), ("high", RED)):
    axs[2].plot(xs, [fuzzy.danger_set(name, x) for x in xs], color=col, label=name)
axs[2].set_title("Output: danger")
axs[2].set_xlabel("danger")
for a_ in axs:
    a_.legend(frameon=False, fontsize=8)
    a_.set_ylabel("membership")
save("fig_fuzzy_sets.png")

gm, ge = np.meshgrid(np.linspace(0, 1, 60), np.linspace(0, 100, 60))
Z = np.array([[fuzzy.infer(m, e)[0] for m in np.linspace(0, 1, 60)] for e in np.linspace(0, 100, 60)])
fig = plt.figure(figsize=(5.2, 3.8))
ax = fig.add_subplot(111, projection="3d")
ax.plot_surface(gm, ge, Z, cmap="RdYlGn_r", linewidth=0, antialiased=True)
ax.set_xlabel("edge margin")
ax.set_ylabel("spin energy")
ax.set_zlabel("danger")
ax.set_title("Mamdani control surface (centroid defuzzification)")
ax.view_init(24, -58)
save("fig_fuzzy_surface.png")

# 8. Architecture diagram -----------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8, 4.6))
ax.set_xlim(0, 100)
ax.set_ylim(0, 60)
ax.axis("off")


def box(x, y, w, h, text, fc, ec="#222", fs=9):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4,rounding_size=1.2", fc=fc, ec=ec, lw=1.2))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs)


def arrow(x1, y1, x2, y2):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1), arrowprops=dict(arrowstyle="->", lw=1.2, color="#333"))


box(2, 46, 96, 11, "Presentation layer (babyblade/game): scenes, HUD, coach, effects, audio, input, UI kit", "#dce8ff")
box(2, 31, 30, 11, "ArenaView\nsparks, shockwaves, camera,\nhit-stop, banners", "#eef3ff", fs=8)
box(35, 31, 30, 11, "Scenes\ntitle, setup, battle, results,\nchampionship, benchmark", "#eef3ff", fs=8)
box(68, 31, 30, 11, "Coach + Screen Guide\nplain-language hints", "#eef3ff", fs=8)
box(2, 14, 30, 12, "AI agents (babyblade/ai)\nIronclad: Minimax\nCyclone: MCTS", "#ffe3df", fs=8)
box(35, 14, 30, 12, "Real-time Battle (sim/battle.py)\n120 Hz physics, 3 s rounds,\nrules, finishes, events", "#e1f5e9", fs=8)
box(68, 14, 30, 12, "Abstract round model (sim/model.py)\nACTIONS, RESULT, TERMINAL,\nUTILITY, heuristic", "#fff4cf", fs=8)
box(2, 1, 30, 8, "Championship + Tournament\nbracket, benchmark, stats", "#f0e6ff", fs=8)
box(35, 1, 30, 8, "Mamdani fuzzy danger\n(sim/fuzzy.py)", "#fff4cf", fs=8)
box(68, 1, 30, 8, "Rules data: blades, actions,\nconfig.py (all constants)", "#e8e8e8", fs=8)
arrow(50, 45.5, 50, 42.5)
arrow(17, 30.5, 17, 26.5)
arrow(50, 30.5, 50, 26.5)
arrow(83, 30.5, 83, 26.5)
arrow(33, 20, 34.5, 20)
arrow(66, 20, 67.5, 20)
arrow(50, 13.5, 50, 9.5)
arrow(17, 13.5, 17, 9.5)
arrow(83, 13.5, 83, 9.5)
ax.set_title("System architecture: rules never import graphics", fontsize=11)
save("fig_architecture.png")

# 9. Round timeline ------------------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8, 2.6))
ax.set_xlim(0, 7)
ax.set_ylim(0, 4)
ax.axis("off")
for i, (x0, x1, c, t) in enumerate([(0, 1.8, "#cfe3ff", "continuous physics (human may queue an action)"),
                                    (1.8, 3.0, "#ffe9a8", "AIs search\n(1.2 s lead)"),
                                    (3.0, 3.1, GREEN, ""), (3.1, 6.1, "#cfe3ff", "round 2: dashes, drift, hits, recovery"),
                                    (6.1, 7, "#ffe9a8", "search")]):
    ax.add_patch(plt.Rectangle((x0, 1.6), x1 - x0, 1.0, fc=c, ec="#333"))
    ax.text((x0 + x1) / 2, 2.1, t, ha="center", va="center", fontsize=7)
ax.annotate("round boundary:\nboth actions lock in\nat the same instant", xy=(3.05, 1.6), xytext=(3.05, 0.2), ha="center", fontsize=8,
            arrowprops=dict(arrowstyle="->"))
ax.text(0, 3.2, "t = 0", fontsize=8)
ax.text(3.0, 3.2, "t = 3 s", fontsize=8)
ax.text(6.1, 3.2, "t = 6 s", fontsize=8)
ax.set_title("Round timeline: 40 rounds x 3 s = 120 s match limit", fontsize=10)
save("fig_timeline.png")
print("figures saved")
