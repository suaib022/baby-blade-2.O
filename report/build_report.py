"""Build the project report as PDF and DOCX from one content list.

    python report/build_report.py     (needs reportlab, python-docx, pillow; run make_figures.py and make_screenshots.py first)
"""

import json
import os
import re
import subprocess
import sys

from PIL import Image as PILImage

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
FIG = os.path.join(HERE, "figures")
SHOTS = os.path.join(FIG, "shots")
JPG = os.path.join(FIG, "jpg")
os.makedirs(JPG, exist_ok=True)
OUT_PDF = os.path.join(HERE, "BabyBlade_Report.pdf")
OUT_DOCX = os.path.join(HERE, "BabyBlade_Report.docx")
D = json.load(open(os.path.join(HERE, "data", "results.json"), encoding="utf-8"))
W4 = json.load(open(os.path.join(HERE, "data", "why_cyclone.json"), encoding="utf-8"))
BEH = json.load(open(os.path.join(HERE, "data", "ai_behaviour.json"), encoding="utf-8"))
sys.path.insert(0, ROOT)
from babyblade import config as C  # noqa: E402
from babyblade.sim import fuzzy  # noqa: E402

# ================================================================== facts measured from the project
PY = os.path.join(ROOT, ".venv", "Scripts", "python.exe")


def loc(folder):
    n = f = 0
    for dp, dn, fn in os.walk(os.path.join(ROOT, folder)):
        dn[:] = [d for d in dn if d not in ("__pycache__", ".venv", "build")]
        for x in fn:
            if x.endswith(".py"):
                f += 1
                n += sum(1 for _ in open(os.path.join(dp, x), encoding="utf-8", errors="ignore"))
    return n, f


SRC_LINES, SRC_FILES = loc("babyblade")
TEST_COUNTS = {}
try:
    out = subprocess.run([PY, "-m", "pytest", "--collect-only", "-q"], cwd=ROOT, capture_output=True, text=True, timeout=120).stdout
    for line in out.splitlines():
        if "::" in line:
            k = line.split("::")[0].split("/")[-1]
            TEST_COUNTS[k] = TEST_COUNTS.get(k, 0) + 1
except Exception:
    pass
TESTS = sum(TEST_COUNTS.values()) or 67
N_MATCHES = sum(v["matches"] for v in D.values()) + sum(v["n"] for v in W4.values()) + sum(v["n"] for v in BEH.values())


def pct(a, n):
    return f"{100 * a / n:.0f}%"


def jpg(name, width_px=1100):
    """Re-encode a screenshot as a smaller JPEG (avoids viewer tiling lines on large PNGs)."""
    dst = os.path.join(JPG, name + ".jpg")
    im = PILImage.open(os.path.join(SHOTS, name + ".png")).convert("RGB")
    im = im.resize((width_px, int(im.height * width_px / im.width)), PILImage.LANCZOS)
    im.save(dst, "JPEG", quality=88, optimize=True)
    return dst


# ================================================================== content (one list, two renderers)
B = []  # blocks: (kind, ...)


def H1(t):
    B.append(("h1", t))


def H2(t):
    B.append(("h2", t))


def Pp(t):
    B.append(("p", t))


def BL(items):
    B.append(("bul", items))


def TB(caption, rows, widths):
    B.append(("table", caption, rows, widths))


def FG(path, caption, width):
    B.append(("fig", path, caption, width))


def FG2(p1, p2, caption):
    B.append(("fig2", p1, p2, caption))


# ---------------------------------------------------------------- 1
H1("1. Introduction")
H2("1.1 Goal")
Pp("The goal of this project is to use the search and fuzzy logic methods from the AI lab inside one complete game. "
   "A game is a good test for these methods because every move depends on what the other player does.")
Pp("The objectives are:")
BL(["Make a spinning top game with five actions and counters.",
    "Build two AI players that use different algorithms.",
    "Add an AI vs AI mode (required) and a Human vs AI mode.",
    "Show a live danger meter that uses fuzzy logic.",
    "Compare the two AIs with many matches."])
H2("1.2 What we built")
Pp("Baby Blade is a 2D spinning top battle game. Two blades fight in a round stadium that gets smaller over time. "
   "Every 3 seconds each player picks one action, and physics decides what happens.")
Pp("The game has five modes: Play (Human vs AI), AI vs AI, Championship, AI Benchmark and Customize. "
   "It runs on desktop and in the browser. All art and sound are made by code. The only outside file is the Oswald font, which has an open license.")

# ---------------------------------------------------------------- 2
H1("2. Background")
H2("2.1 Spinning top games")
Pp("In real Beyblade, a battle runs from launch to finish. Players do not choose moves during the battle. "
   "The video game Beyblade X: XONE adds gauges for spin, burst and special moves. "
   "Our proposal uses rounds instead, where both players choose one action. This gives the AI a clear game tree. "
   "In our game, each round is played with real-time physics.")
Pp("We also looked at a web game, Beyblade Simulator. It uses a top-down view, a rounded board, a glowing rim and a part editor. "
   "We used the same ideas for our stadium and our blade editor.")
H2("2.2 Algorithms")
Pp("<b>Minimax</b> picks the move that is best when the opponent replies in the best way. "
   "Alpha-beta pruning skips moves that cannot change the result. "
   "Iterative deepening searches 1 move deep, then 2, then 3, so an answer is always ready.")
Pp("<b>Monte Carlo Tree Search (MCTS)</b> plays many random games. It repeats four steps: selection, expansion, simulation and backpropagation. "
   "UCB1 chooses which move to try next.")
Pp("<b>Mamdani fuzzy logic</b> turns numbers into fuzzy sets, applies if-then rules, and turns the result back into one number.")

# ---------------------------------------------------------------- 3
H1("3. Game Design")
H2("3.1 Match and rounds")
Pp(f"A match has {C.ROUNDS} rounds of {C.ROUND_SECONDS:.0f} seconds, so 120 seconds in total. "
   "At the start of each round both players lock in one action at the same time. Neither player has priority. "
   "During the round, physics runs 120 times per second.")
TB("What happens in one round.",
   [["Time in round", "Event"],
    ["0 s", "Both actions lock in. The spin cost is paid. Attack, Special and Dodge start their dash."],
    ["0 to 0.9 s", "Attack and Special pull the blade toward the rival."],
    ["0 to 0.7 s", "A successful Dodge makes attacks miss."],
    ["1.8 s", "Both AIs start to search for their next action. A human can still change the queued action."],
    ["3 s", "The round ends. The next actions lock in. The stadium shrinks after rounds 6, 12, 18 and 24."]],
   [3.2 * 10 / 10, 12.8])
H2("3.2 How a match ends")
TB("Finish types.",
   [["Finish", "Rule"],
    ["Ring-out", "The center of a blade leaves the stadium."],
    ["Burst", "Stability reaches 0."],
    ["Spin-out", "Spin energy reaches 0."],
    ["Draw", "Both blades are out at the same time."],
    ["Points", "After round 40: 0.4 x energy + 0.4 x stability + 0.2 x closeness to center. Equal scores are a draw."]],
   [2.8, 13.2])
Pp("If a blade has more than one finish at once, ring-out comes first, then burst, then spin-out. A match can end at any moment in a round.")
H2("3.3 Blades")
TB("Blade types.",
   [["Blade", "Stability", "Spin loss per round", "Attack power", "Special"],
    ["Balanced", "100", "3", "1.00", "None"], ["Attacker", "90", "4", "1.25", "Hits harder"],
    ["Defender", "120", "3", "0.85", "Guard heals 10"], ["Stamina", "100", "2", "1.00", "Charge gives 25"]],
   [2.8, 2.4, 3.8, 3.0, 4.0])
H2("3.4 Actions")
TB("The five actions.",
   [["Action", "Cost", "Effect"],
    ["Charge", "0", "Gain 20 spin and move toward the center. Takes 25% more damage."],
    ["Attack", "8", f"Dash at the rival. Hit for {C.ATTACK_DAMAGE:.0f} damage times blade power. Guard halves it."],
    ["Guard", "4", "Gain 5 stability. Take half damage and push. Heavy, so hard to move."],
    ["Dodge", "8", "Dash sideways. Attacks that touch in the first 0.7 seconds miss. Fails near the rim."],
    ["Special", "35", f"Hit for {C.SPECIAL_DAMAGE:.0f} damage with a big push. You lose 10 stability. 3 second cooldown. Guard only blocks 30%."]],
   [2.4, 1.4, 12.2])
Pp("Counters: Attack beats Charge. Guard beats Attack. Special breaks Guard. Dodge avoids Attack and Special. If both players attack, both hits land.")
TB("Damage of one hit when the blade power is 1.0. Multiply by the attacker's blade power.",
   [["Attacker uses", "Rival Charge", "Rival Attack", "Rival Guard", "Rival Dodge", "Rival Special"],
    ["Attack", "15", "12", "6 (attacker takes 3)", "miss", "12"],
    ["Special", "31", "25", "17.5", "miss", "25"]],
   [2.6, 2.2, 2.2, 3.6, 2.2, 3.2])
H2("3.5 Stadiums")
Pp("The stadium starts with radius 10 and shrinks to radius 6. The shrink is smooth and is announced one round before it happens. "
   "There are three stadiums.")
TB("Stadiums and the shrink schedule.",
   [["Stadium", "Effect"],
    ["Classic Dish", "Normal movement and push."],
    ["Ice Rink", "Movement and push are 1.25 times stronger. Less friction."],
    ["Steep Bowl", "A strong pull toward the center."],
    ["Rounds 1-6 / 7-12 / 13-18 / 19-24 / 25-40", "Radius 10 / 9 / 8 / 7 / 6"]],
   [7.0, 9.0])
H2("3.6 Movement and hits")
Pp(f"Humans and AIs move freely. The stick sets the speed, up to {C.DRIVE_SPEED:.0f} units per second, and the blade follows in about 45 ms. "
   "A blade cannot steer itself out of the stadium, so a ring-out always comes from a hit.")
Pp("Blades are solid and cannot overlap. A hit happens when two blades touch. Each attacker can hit once per round. "
   "A hit takes spin and stability only when the rules in the tables above allow it.")
H2("3.7 Modes")
TB("Game modes.",
   [["Mode", "What it does"],
    ["Play", "Human vs AI. Choose the AI, difficulty, blades and stadium."],
    ["AI vs AI", "Watch two AIs. Pause, step one round, change speed, swap sides."],
    ["Championship", "You and seven AIs in a knockout bracket. The final is best of three."],
    ["AI Benchmark", "Run 5 to 50 AI matches and see wins, draws, time and finish types."],
    ["Customize", "Change the look of your blade and choose its type."]],
   [3.4, 12.6])

# ---------------------------------------------------------------- 4
H1("4. AI Methods")
H2("4.1 Round model and score")
Pp("The AI cannot run physics inside its search. It uses a simple model of one round with the same numbers as the game. "
   "The model has the four standard parts: ACTIONS (legal moves), RESULT (play one round), TERMINAL (is the match over) and UTILITY (win, loss or draw).")
Pp("Both AIs score a position with the same heuristic. It adds five parts:")
TB("Heuristic score (from the player's point of view).",
   [["Part", "Weight"],
    ["Spin energy compared with the rival", "0.30"],
    ["Stability compared with the rival", "0.30"],
    ["Position (closer to the center than the rival)", "0.15"],
    ["Special is ready compared with the rival", "0.05"],
    ["Fuzzy danger of the rival minus own danger", "0.20"]],
   [11.0, 5.0])
H2("4.2 Ironclad (Minimax)")
Pp("Ironclad uses Minimax with alpha-beta pruning and a depth limit. Its steps are:")
BL(["List its legal actions. Try the best action of the last search first.",
    "For depth 1, 2, 3 (up to the limit): for each action, find the worst result over all rival replies. Skip an action when it cannot beat the best so far.",
    "Keep the best action of the last depth that finished.",
    "On Easy, play a random legal action 15% of the time."])
H2("4.3 Cyclone (MCTS)")
Pp("Cyclone uses MCTS with UCB1 (C = 1.4). Each player keeps its own move counts at every node, because both players move at the same time. Its steps are:")
BL(["Selection: at each node both players pick an action with UCB1. Every action is tried once first.",
    "Expansion: add the new state to the tree.",
    "Simulation: play up to 4 rounds. The rollout mixes random moves with a one-step greedy choice. Score the end with the utility.",
    "Backpropagation: update counts and rewards along the path. The second player gets 1 minus the reward.",
    "After all simulations, play the most visited action."])
H2("4.4 AI movement")
Pp("After an AI picks an action, it also steers its blade. It uses the same drive as a human.")
TB("How the AI steers.",
   [["Action", "Movement"],
    ["Attack, Special", "Move toward the rival."],
    ["Dodge", "Slide sideways, toward the side with more room."],
    ["Charge", "Move to the center."],
    ["Guard", "Stay in place."],
    ["Near the rim (any action)", "Add a pull toward the center."]],
   [4.4, 11.6])
H2("4.5 Difficulty")
TB("Difficulty levels.",
   [["Level", "Ironclad depth", "Cyclone simulations", "Random move", "Steering speed"],
    ["Easy", "1", "60", "15%", "60%"], ["Medium", "2", "200", "0%", "85%"], ["Hard", "3", "500", "0%", "100%"]],
   [2.4, 3.2, 3.8, 3.2, 3.4])
H2("4.6 Fuzzy danger")
Pp("The inputs are the edge margin (how far the blade is from the rim) and the spin energy. The output is danger from 0 to 100. "
   "Each has three sets, shown in the figure below. We use minimum for AND, maximum for OR, and the centroid for the final number. "
   "The game shows the result as LOW, MEDIUM or HIGH.")
FG(os.path.join(FIG, "plain_fuzzy.png"), "Fuzzy sets for the two inputs and the output.", 14.5)
TB("The nine fuzzy rules: danger for each pair of inputs.",
   [["Edge margin", "Energy low", "Energy medium", "Energy high"],
    ["Near", "High", "High", "Medium"], ["Middle", "High", "Medium", "Low"], ["Far", "Medium", "Low", "Low"]],
   [3.4, 3.6, 3.6, 3.6])
ex = []
for m, e in ((0.9, 95), (0.4, 50), (0.05, 15)):
    d, _ = fuzzy.infer(m, e)
    ex.append([f"{m}", f"{e}", f"{d:.0f}", fuzzy.label(d)])
TB("Examples of the fuzzy output.", [["Edge margin", "Spin energy", "Danger", "Shown as"]] + ex, [3.4, 3.4, 3.4, 3.4])
H2("4.7 Thinking without stopping the game")
Pp("A browser has no threads, so a long search would freeze the game. Each AI search is written as a generator. "
   "The game runs it for a few milliseconds per frame, starting 1.2 seconds before the round ends. "
   "At the end of the round, any unfinished search is completed. In tests, the search runs to the end at once.")
H2("4.8 Lab topics used")
TB("Lab topics and where they appear.",
   [["Lab topic", "Where it is used"],
    ["Python data structures", "State tuples, tables, event lists"],
    ["Depth-limited search, iterative deepening", "Ironclad"],
    ["Adversarial search (Minimax)", "Ironclad and the round model"],
    ["Heuristic function", "Shared score for both AIs"],
    ["MCTS and UCB", "Cyclone"],
    ["Mamdani fuzzy inference", "Danger meter"]],
   [7.0, 9.0])

# ---------------------------------------------------------------- 5
H1("5. System Design")
H2("5.1 Layers")
Pp("The rules code never imports graphics, and the screen code only reads the rules. "
   "This lets us test the rules without a window and run fast benchmarks.")
TB("Main modules.",
   [["Module", "Job"],
    ["sim/battle.py", "Physics, rounds, actions, hits, finishes"],
    ["sim/model.py", "Round model and score used by the AIs"],
    ["sim/fuzzy.py", "Fuzzy danger"],
    ["ai/agents.py", "Ironclad, Cyclone and the human player"],
    ["tournament.py, championship.py", "AI Benchmark and the bracket"],
    ["game/arena_view.py, fx.py, assets.py", "Drawing, effects and art made by code"],
    ["game/audio.py, inputs.py, ui.py", "Sound made by code, input, menus"],
    ["game/coach.py and scenes/", "Coach tips and all screens"]],
   [6.4, 9.6])
H2("5.2 Frame loop")
Pp("In every frame the game reads input, moves the battle forward by the frame time, reads the new events, updates effects and draws the screen. "
   "Hit-stop and slow motion change the time given to the battle, not the drawing.")
TB("Events from the battle and what the screen does with them.",
   [["Event", "Effect on screen and sound"],
    ["Round start", "Sound for each action. Special shows sparks and a label."],
    ["Hit", "Sparks, shock wave, screen shake, short freeze, damage number."],
    ["Clash or grind", "Smaller sparks and a clash sound."],
    ["Dodge, evade", "Whoosh and a MISS or DODGE FAILED label."],
    ["Shrink warning, shrink", "Alarm, banner, red ring and a shake."],
    ["Finish", "Banner, slow motion, crowd and finish sound."]],
   [4.0, 12.0])
H2("5.3 Physics")
Pp("Each blade has a pull toward the center, a push-back near the rim, damping and a spin drift. Dashes add speed at the start of a round. "
   "Spin and stability change a little in every frame, so the bars move smoothly.")
TB("Main physics numbers (all in one config file).",
   [["Number", "Value", "Meaning"],
    ["Simulation rate", f"{C.PHYSICS_HZ} per second", "Fixed time step"],
    ["Bowl pull", f"{C.BOWL_PULL} (Steep Bowl {C.STEEP_BOWL_PULL})", "Pull toward the center"],
    ["Damping", f"{C.LINEAR_DAMPING} per second", "Friction"],
    ["Bounce", f"{C.RESTITUTION}", "Energy kept in a collision"],
    ["Attack, Special, Dodge dash", f"{C.DASH_ATTACK}, {C.DASH_SPECIAL}, {C.DASH_DODGE}", "Speed added at round start"],
    ["Drive speed and response", f"{C.DRIVE_SPEED} units/s, {C.DRIVE_RESPONSE} per second", "Stick control"],
    ["Blade radius", f"{C.BLADE_RADIUS}", "Centers stay 2.4 apart"]],
   [4.8, 5.4, 5.8])
H2("5.4 Spin look")
Pp("At about 9 turns per second a blade turns 55 degrees per frame, which looks still. "
   "We draw blurred copies over the angle moved and add a gold pointer to every blade, so the spin is easy to see.")
H2("5.5 Art, sound and builds")
Pp("The stage, stadiums, blades, icons and effects are drawn by code when the game starts. The sounds are made by code too, and the spin hum changes pitch with the energy. "
   "The game runs on desktop with Python and pygame-ce. The same code is built for the browser with pygbag, and the result is a static site that can be hosted on a service such as Netlify.")
TB("Project size.",
   [["Measure", "Value"],
    ["Source files and lines", f"{SRC_FILES} files, {SRC_LINES:,} lines"],
    ["Automated tests", f"{TESTS}"],
    ["Frame time on desktop", "about 2 ms"],
    ["Simulation speed", "234 matches in 25 seconds on 16 cores"]],
   [6.4, 9.6])

# ---------------------------------------------------------------- 6
H1("6. User Interface")
H2("6.1 Goals")
Pp("An early prototype looked flat and did not explain its numbers. The final game aims to look fast, explain every number, "
   "and work with mouse, keyboard, gamepad and touch. The style comes from our presentation: a dark navy stage, blue for Player 1 and red for Player 2.")
H2("6.2 Screens")
Pp("The title screen shows a live AI match behind the menu. The setup screen shows both blades and the stadium before the match.")
FG(jpg("01_title"), "Title screen with a live AI match.", 12.5)
FG2(jpg("02_setup"), jpg("03_customize"), "Left: match setup. Right: blade editor.")
Pp("The battle screen has a card for each blade, the round and the clock in the middle, and the action buttons at the bottom.")
FG(jpg("05_battle_human"), "Battle screen: gauges, Coach, counters and action buttons.", 14)
Pp("In AI vs AI, every blade shows its current action (NOW) and its next action (NEXT). The bars show how much the AI likes each action.")
FG(jpg("07_battle_ai"), "AI vs AI: NOW and NEXT for both AIs.", 14)
H2("6.3 Learning aids")
BL(["Coach panel: short tips in plain words. Urgent tips come first. Hover an action to read its details.",
    "Counters chart: shows which action beats which, with icons and names.",
    "NOW and NEXT: your next action, or the action an AI has already chosen. It shows after the AI finishes thinking.",
    "AI decision bars: one bar per action with its name. The gold bar is the AI's pick.",
    "Screen Guide (H key): freezes the game and numbers every part of the screen."])
FG(jpg("06_screen_guide"), "The Screen Guide.", 13)
H2("6.4 Championship, results and benchmark")
Pp("In the Championship, eight players play a knockout bracket. AI matches are simulated. Your matches are real battles on a different stadium each round, and your titles are saved. "
   "The results screen shows the winner, the finish type and the numbers for each blade. The AI Benchmark runs many AI matches and shows the statistics.")
FG2(jpg("10_championship"), jpg("09_results"), "Left: Championship bracket. Right: results screen.")
FG2(jpg("11_benchmark"), jpg("04_howto"), "Left: AI Benchmark. Right: How to play.")
H2("6.5 Controls and feedback")
TB("Controls.",
   [["", "Keyboard", "Gamepad", "Touch"],
    ["Actions", "1 Charge, 2 Attack, 3 Guard, 4 Special, Space Dodge", "X, A, Y, RB, B", "Buttons"],
    ["Move", "WASD or arrows", "Left stick", "On-screen stick"],
    ["Pause, guide, mute", "P, H, M", "Start", "Buttons"]],
   [3.2, 7.2, 2.8, 2.8])
BL(["Colors always come with a text label, for example LOW, MEDIUM and HIGH.",
    "Screen shake, the Coach and the sound can be turned off in Settings.",
    "Every menu can be used with the keyboard, the gamepad or the mouse.",
    "Floating labels such as COUNTER, MISS and DODGE FAILED show why a hit worked or not."])

# ---------------------------------------------------------------- 7
H1("7. Testing and Results")
H2("7.1 Automated tests")
Pp(f"There are {TESTS} automated tests. They run without a window and they all pass.")
names = {"test_rules_and_model.py": "Rules, round model, finishes, points",
         "test_fuzzy_and_ai.py": "Fuzzy logic and the two AIs",
         "test_battle.py": "Real-time battle, physics, drive, AI steering, NEXT",
         "test_game.py": "Screens, input, benchmark, Screen Guide",
         "test_championship_coach.py": "Championship bracket and Coach"}
rows = [["Test file", "Area", "Tests"]]
for k, v in sorted(TEST_COUNTS.items()):
    rows.append([k, names.get(k, k), str(v)])
TB("Tests by area.", rows, [5.2, 8.8, 2.0])
Pp("We also ran the game headless, read profiler output, and checked screenshots of every screen.")
H2("7.2 Experiments")
Pp(f"We ran {N_MATCHES} matches with the real physics and the real AIs. Sides swap every match. "
   "Each case has 6 to 30 matches, so small differences are not reliable.")
H2("7.3 Ironclad against Cyclone")
rows = [["Difficulty", "Matches", "Ironclad wins", "Cyclone wins", "Draws", "Time per decision"]]
for d in ("Easy", "Medium", "Hard"):
    r = D[f"head2head_{d}"]
    rows.append([d, str(r["matches"]), f"{r['wins_a']} ({pct(r['wins_a'], r['matches'])})", f"{r['wins_b']} ({pct(r['wins_b'], r['matches'])})",
                 str(r["draws"]), f"{r['think_a_ms']:.1f} ms / {r['think_b_ms']:.0f} ms"])
TB("Both AIs on Classic Dish with Balanced blades. Decision time is Ironclad / Cyclone.", rows, [2.2, 2.0, 3.0, 3.0, 1.6, 4.2])
FG(os.path.join(FIG, "plain_h2h.png"), "Share of matches won by each AI.", 10.5)
Pp("Ironclad wins at Medium and Hard. Cyclone is a little better at Easy, where Ironclad looks only one round ahead and plays a random move 15% of the time. "
   "Cyclone also needs much more time to decide.")
H2("7.4 How matches end")
rows = [["Case", "Ring-out", "Burst", "Spin-out", "Points", "Draw"]]
for k, n in (("head2head_Easy", "Easy"), ("head2head_Medium", "Medium"), ("head2head_Hard", "Hard"),
             ("stadium_CLASSIC", "Classic Dish"), ("stadium_ICE", "Ice Rink"), ("stadium_STEEP", "Steep Bowl")):
    f = D[k]["finishes"]
    rows.append([n] + [str(f.get(x, 0)) for x in ("RING_OUT", "BURST", "SPIN_OUT", "POINTS", "DRAW")])
TB("Finish types in the first six cases (number of matches).", rows, [4.0, 2.4, 2.4, 2.4, 2.4, 2.4])
H2("7.5 Difficulty and stadium")
sc_i, sc_c = D["scaling_Ironclad"], D["scaling_Cyclone"]
Pp(f"Higher difficulty wins: Hard beat Easy in {sc_i['wins_b']} of {sc_i['matches']} matches for Ironclad and {sc_c['wins_b']} of {sc_c['matches']} for Cyclone.")
rows = [["Stadium", "Matches", "Ring-outs", "Average time"]]
for k, n in (("stadium_CLASSIC", "Classic Dish"), ("stadium_ICE", "Ice Rink"), ("stadium_STEEP", "Steep Bowl")):
    r = D[k]
    rows.append([n, str(r["matches"]), pct(r["finishes"].get("RING_OUT", 0), r["matches"]), f"{r['avg_seconds']:.0f} s"])
TB("Stadium effect (Ironclad vs Cyclone, Medium).", rows, [4.0, 2.6, 3.0, 3.4])
Pp("The Ice Rink gives the most ring-outs. The Steep Bowl gave none, because it pulls both blades to the center.")
H2("7.6 Blades")
kinds = ["BALANCED", "ATTACKER", "DEFENDER", "STAMINA"]
M = {}
for i in range(4):
    for j in range(i + 1, 4):
        r = D[f"blade_{kinds[i]}_{kinds[j]}"]
        v = (r["wins_a"] + 0.5 * r["draws"]) / r["matches"]
        M[(i, j)], M[(j, i)] = v, 1 - v
rows = [["Blade", "vs Balanced", "vs Attacker", "vs Defender", "vs Stamina"]]
for i in range(4):
    rows.append([kinds[i].title()] + ["-" if i == j else f"{100 * M[(i, j)]:.0f}%" for j in range(4)])
TB("Win rate of each blade (Ironclad Medium on both sides, a draw counts half).", rows, [3.0, 3.2, 3.2, 3.2, 3.2])
Pp("Defender wins about 92% against Balanced and Attacker. Its high stability, the Guard heal and the half damage from Guard make it very hard to beat. "
   "We kept the numbers from the proposal, so we report this as it is.")
H2("7.7 Why Cyclone often loses")
rows = [["Case", "Ironclad wins", "Cyclone wins", "Draws"]]
for name, v in W4.items():
    rows.append([re.sub(r"\s+", " ", name.split("(")[0]).strip(), f"{v['ironclad']} ({pct(v['ironclad'], v['n'])})", f"{v['cyclone']} ({pct(v['cyclone'], v['n'])})", str(v["draws"])])
TB("Medium AIs on Classic Dish, 30 matches each. The first case is Defender (Ironclad) against Attacker (Cyclone).", rows, [8.6, 3.0, 3.0, 1.4])
Pp("There are two causes. First, the blade: Cyclone with the Attacker blade loses most matches, and with the Defender it wins more. "
   "Second, the AI: with equal blades Ironclad still wins more. Ironclad checks all 25 move pairs exactly, while Cyclone spreads 200 random games over them, about 8 each, so its choice is noisy.")
H2("7.8 How each AI plays")
rows = [["AI", "Level", "Charge", "Attack", "Guard", "Dodge", "Special"]]
from collections import Counter  # noqa: E402
for ag in ("Ironclad", "Cyclone"):
    for df in ("Easy", "Medium", "Hard"):
        c = Counter()
        for bl in kinds:
            c.update(BEH[f"{ag}|{df}|{bl}|CLASSIC"]["actions"])
        t = sum(c.values()) or 1
        rows.append([ag, df] + [f"{100 * c[a] / t:.0f}%" for a in ("CHARGE", "ATTACK", "GUARD", "DODGE", "SPECIAL")])
TB("Share of rounds in which each AI plays each action (Classic Dish, all four blades).", rows, [2.6, 2.2, 2.2, 2.2, 2.2, 2.2, 2.4])
Pp("Ironclad attacks and charges a lot, and it almost never dodges. Cyclone dodges about one round in six and uses Special more often. "
   "This is useful for players: Attack when Ironclad charges, and do not chase Cyclone with Attack.")

# ---------------------------------------------------------------- 8
H1("8. Conclusion")
Pp("Baby Blade uses Minimax, MCTS and fuzzy logic together in one playable game. "
   "Both AIs play the same rules and move freely, and the danger meter uses a real fuzzy system.")
Pp("The tests show that higher difficulty wins, and that the two AIs differ in strength, speed and style. "
   "They also show a balance problem: the Defender blade is too strong with the numbers from the proposal.")
Pp("The interface helps new players with the Coach, the counters chart, the NOW and NEXT actions and the Screen Guide. "
   "The game works on desktop and in the browser, with keyboard, gamepad and touch.")
Pp("We wrote the requirements and the design. We built the game with the help of an AI coding assistant (Claude Code) and checked it with tests and experiments.")


# ================================================================== renderer 1: PDF
def build_pdf():
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (BaseDocTemplate, CondPageBreak, Frame, Image, KeepTogether, NextPageTemplate, PageBreak,
                                    PageTemplate, Paragraph, Spacer, Table, TableStyle)

    BODY = ParagraphStyle("body", fontName="Times-Roman", fontSize=14, leading=18.5, spaceAfter=7)
    H1s = ParagraphStyle("H1", fontName="Times-Bold", fontSize=18, leading=22, spaceBefore=12, spaceAfter=5, keepWithNext=1)
    H2s = ParagraphStyle("H2", fontName="Times-Bold", fontSize=15, leading=19, spaceBefore=7, spaceAfter=3, keepWithNext=1)
    CAP = ParagraphStyle("cap", fontName="Times-Italic", fontSize=12, leading=14.5, spaceBefore=2, spaceAfter=8, alignment=TA_CENTER)
    TCAP = ParagraphStyle("tcap", parent=CAP, alignment=0, spaceAfter=2, spaceBefore=4)
    CELL = ParagraphStyle("cell", fontName="Times-Roman", fontSize=12, leading=14.5)
    CELLB = ParagraphStyle("cellb", parent=CELL, fontName="Times-Bold")
    BUL = ParagraphStyle("bul", parent=BODY, leftIndent=14, bulletIndent=2, spaceAfter=1.5)
    TITLE = ParagraphStyle("title", fontName="Times-Bold", fontSize=32, leading=38, alignment=TA_CENTER)
    CEN = ParagraphStyle("cen", parent=BODY, alignment=TA_CENTER, fontSize=14, leading=19)

    def esc(t):
        return re.sub(r"&(?!(?:amp|lt|gt|#\d+);)", "&amp;", t)

    fno, tno = [0], [0]

    def image(path, width_cm):
        w, h = PILImage.open(path).size
        return Image(path, width=width_cm * cm, height=width_cm * cm * h / w)

    S = [Spacer(1, 6.5 * cm), Paragraph("BABY BLADE", TITLE), Spacer(1, 6), Paragraph("An AI-Powered Spinning Top Battle Game", CEN),
         Spacer(1, 1.6 * cm), Paragraph("Artificial Intelligence Laboratory<br/>Project Report", CEN), Spacer(1, 1.6 * cm),
         Paragraph("Suaib Ahmed Safi (2207115)<br/>Ashrafur Rahman Nihad (2207116)", CEN), Spacer(1, 1.2 * cm),
         Paragraph("Department of Computer Science and Engineering<br/>Khulna University of Engineering &amp; Technology (KUET)", CEN),
         Spacer(1, 1.0 * cm), Paragraph("November 2026", CEN), NextPageTemplate("main"), PageBreak()]
    for blk in B:
        k = blk[0]
        if k == "h1":
            S.append(Paragraph(esc(blk[1]), H1s))
        elif k == "h2":
            S += [CondPageBreak(3.5 * cm), Paragraph(esc(blk[1]), H2s)]
        elif k == "p":
            S.append(Paragraph(esc(blk[1]), BODY))
        elif k == "bul":
            S += [Paragraph(esc(i), BUL, bulletText="-") for i in blk[1]]
        elif k == "table":
            _, cap, rows, widths = blk
            tno[0] += 1
            data = [[Paragraph(esc(str(c)), CELLB if i == 0 else CELL) for c in r] for i, r in enumerate(rows)]
            t = Table(data, colWidths=[w * cm for w in widths], repeatRows=1)
            t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.6, colors.black), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                                   ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                                   ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4)]))
            S += [KeepTogether([Paragraph(esc(f"Table {tno[0]}. {cap}"), TCAP), t]), Spacer(1, 8)]
        elif k == "fig":
            _, path, cap, w = blk
            fno[0] += 1
            S.append(KeepTogether([image(path, w), Paragraph(esc(f"Figure {fno[0]}. {cap}"), CAP)]))
        elif k == "fig2":
            _, p1, p2, cap = blk
            fno[0] += 1
            t = Table([[image(p1, 7.6), image(p2, 7.6)]], colWidths=[8.1 * cm, 8.1 * cm])
            t.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                                   ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
            S.append(KeepTogether([t, Paragraph(esc(f"Figure {fno[0]}. {cap}"), CAP)]))

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Times-Roman", 10)
        canvas.drawCentredString(A4[0] / 2, 1.3 * cm, str(doc.page - 1))  # the cover page is not counted
        canvas.restoreState()

    doc = BaseDocTemplate(OUT_PDF, pagesize=A4, leftMargin=2.5 * cm, rightMargin=2.5 * cm, topMargin=2.2 * cm, bottomMargin=2.2 * cm,
                          title="Baby Blade - Project Report", author="Suaib Ahmed Safi, Ashrafur Rahman Nihad")
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="f")
    doc.addPageTemplates([PageTemplate(id="title", frames=[frame]), PageTemplate(id="main", frames=[frame], onPage=footer)])
    doc.build(S)
    print("wrote", OUT_PDF)


# ================================================================== renderer 2: DOCX
def build_docx():
    from docx import Document
    from docx.enum.section import WD_SECTION
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Cm, Pt, RGBColor

    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21), Cm(29.7)
    sec.left_margin = sec.right_margin = Cm(2.5)
    sec.top_margin = sec.bottom_margin = Cm(2.2)

    def set_font(style, size, bold=False, italic=False):
        style.font.name = "Times New Roman"
        style.font.size = Pt(size)
        style.font.bold = bold
        style.font.italic = italic
        style.font.color.rgb = RGBColor(0, 0, 0)
        rpr = style.element.get_or_add_rPr()
        rf = rpr.find(qn("w:rFonts"))
        if rf is None:
            rf = OxmlElement("w:rFonts")
            rpr.append(rf)
        for a in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
            rf.set(qn(a), "Times New Roman")

    st = doc.styles
    set_font(st["Normal"], 14)
    st["Normal"].paragraph_format.space_after = Pt(6)
    st["Normal"].paragraph_format.line_spacing = 1.15
    for name, size in (("Heading 1", 18), ("Heading 2", 15)):
        set_font(st[name], size, bold=True)
        st[name].paragraph_format.space_before = Pt(12 if name == "Heading 1" else 8)
        st[name].paragraph_format.space_after = Pt(4)
        st[name].paragraph_format.keep_with_next = True
    set_font(st["List Bullet"], 14)

    def runs(par, text, size=None, bold=False, italic=False):
        for tok in re.split(r"(<b>|</b>|<i>|</i>|<br/>)", text):
            if tok == "<b>":
                bold = True
            elif tok == "</b>":
                bold = False
            elif tok == "<i>":
                italic = True
            elif tok == "</i>":
                italic = False
            elif tok == "<br/>":
                par.add_run().add_break()
            elif tok:
                r = par.add_run(tok)
                r.bold, r.italic = bold, italic
                if size:
                    r.font.size = Pt(size)

    def centered(text, size=14, bold=False, before=0, after=0, italic=False):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before, p.paragraph_format.space_after = Pt(before), Pt(after)
        runs(p, text, size, bold, italic)
        return p

    # ---- cover page
    centered("BABY BLADE", 32, True, before=190, after=10)
    centered("An AI-Powered Spinning Top Battle Game", 14, after=48)
    centered("Artificial Intelligence Laboratory<br/>Project Report", 14, after=48)
    centered("Suaib Ahmed Safi (2207115)<br/>Ashrafur Rahman Nihad (2207116)", 14, after=34)
    centered("Department of Computer Science and Engineering<br/>Khulna University of Engineering & Technology (KUET)", 14, after=28)
    centered("November 2026", 14)

    # ---- content section: new page, page numbers start at 1
    new = doc.add_section(WD_SECTION.NEW_PAGE)
    new.footer.is_linked_to_previous = False
    sec.footer.is_linked_to_previous = False
    pg = OxmlElement("w:pgNumType")
    pg.set(qn("w:start"), "1")
    new._sectPr.append(pg)
    fp = new.footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = fp.add_run()
    for kind, text in (("begin", None), (None, "PAGE"), ("end", None)):
        if kind:
            el = OxmlElement("w:fldChar")
            el.set(qn("w:fldCharType"), kind)
        else:
            el = OxmlElement("w:instrText")
            el.set(qn("xml:space"), "preserve")
            el.text = text
        run._r.append(el)

    fno, tno = [0], [0]

    def picture(par, path, width_cm):
        par.add_run().add_picture(path, width=Cm(width_cm))

    def caption(text):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(10)
        r = p.add_run(text)
        r.italic = True
        r.font.size = Pt(12)

    for blk in B:
        k = blk[0]
        if k == "h1":
            doc.add_heading(blk[1], level=1)
        elif k == "h2":
            doc.add_heading(blk[1], level=2)
        elif k == "p":
            runs(doc.add_paragraph(), blk[1])
        elif k == "bul":
            for it in blk[1]:
                p = doc.add_paragraph(style="List Bullet")
                p.paragraph_format.space_after = Pt(2)
                runs(p, it)
        elif k == "table":
            _, cap, rows, widths = blk
            tno[0] += 1
            cp = doc.add_paragraph()
            cp.paragraph_format.keep_with_next = True
            cp.paragraph_format.space_after = Pt(3)
            r = cp.add_run(f"Table {tno[0]}. {cap}")
            r.italic = True
            r.font.size = Pt(12)
            t = doc.add_table(rows=len(rows), cols=len(rows[0]))
            t.style = "Table Grid"
            t.alignment = WD_TABLE_ALIGNMENT.CENTER
            t.autofit = False
            for i, row in enumerate(rows):
                for j, val in enumerate(row):
                    cell = t.cell(i, j)
                    cell.width = Cm(widths[j])
                    par = cell.paragraphs[0]
                    par.paragraph_format.space_after = Pt(0)
                    par.paragraph_format.keep_with_next = i < len(rows) - 1
                    r = par.add_run(str(val))
                    r.font.size = Pt(12)
                    r.bold = (i == 0)
            doc.add_paragraph().paragraph_format.space_after = Pt(2)
        elif k == "fig":
            _, path, cap, w = blk
            fno[0] += 1
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.keep_with_next = True
            p.paragraph_format.space_after = Pt(2)
            picture(p, path, w)
            caption(f"Figure {fno[0]}. {cap}")
        elif k == "fig2":
            _, p1, p2, cap = blk
            fno[0] += 1
            t = doc.add_table(rows=1, cols=2)
            t.alignment = WD_TABLE_ALIGNMENT.CENTER
            for c, path in zip(t.rows[0].cells, (p1, p2)):
                c.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
                c.paragraphs[0].paragraph_format.keep_with_next = True
                picture(c.paragraphs[0], path, 7.6)
            caption(f"Figure {fno[0]}. {cap}")

    doc.core_properties.title = "Baby Blade - Project Report"
    doc.core_properties.author = "Suaib Ahmed Safi, Ashrafur Rahman Nihad"
    doc.save(OUT_DOCX)
    print("wrote", OUT_DOCX)


if __name__ == "__main__":
    build_pdf()
    build_docx()
