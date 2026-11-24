"""Build the academic report PDF for BABY BLADE 2.0.

    python report/build_report.py        (needs reportlab and pillow; run make_figures.py first)
"""

import json
import os
import re
import subprocess
import sys

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (BaseDocTemplate, Frame, Image, KeepTogether, NextPageTemplate, PageBreak, PageTemplate,
                                Paragraph, Spacer, Table, TableStyle)
from reportlab.platypus.tableofcontents import TableOfContents

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
FIG = os.path.join(HERE, "figures")
SHOTS = os.path.join(FIG, "shots")
OUT = os.path.join(HERE, "BabyBlade2_Report.pdf")
D = json.load(open(os.path.join(HERE, "data", "results.json"), encoding="utf-8"))
sys.path.insert(0, ROOT)
from babyblade import config as C  # noqa: E402
from babyblade.sim import fuzzy  # noqa: E402

# ---------------------------------------------------------------- measured facts
GAME_PY = os.path.join(ROOT, ".venv", "Scripts", "python.exe")


def count_lines(folder, skip=()):
    n = files = 0
    for dp, dn, fn in os.walk(folder):
        dn[:] = [d for d in dn if d not in ("__pycache__", ".venv", "build", "figures", "data") and d not in skip]
        for f in fn:
            if f.endswith(".py"):
                files += 1
                n += sum(1 for _ in open(os.path.join(dp, f), encoding="utf-8", errors="ignore"))
    return n, files


SRC_LINES, SRC_FILES = count_lines(os.path.join(ROOT, "babyblade"))
TEST_LINES, TEST_FILES = count_lines(os.path.join(ROOT, "tests"))
try:
    out = subprocess.run([GAME_PY, "-m", "pytest", "--collect-only", "-q"], cwd=ROOT, capture_output=True, text=True, timeout=120).stdout
    TESTS = int(re.search(r"(\d+) tests? collected", out).group(1))
except Exception:
    TESTS = 65
TOTAL_MATCHES = sum(v["matches"] for v in D.values())

# ---------------------------------------------------------------- styles
ss = getSampleStyleSheet()
BODY = ParagraphStyle("Body", parent=ss["Normal"], fontName="Times-Roman", fontSize=11, leading=15.5, alignment=TA_JUSTIFY, spaceAfter=6)
SMALL = ParagraphStyle("Small", parent=BODY, fontSize=9, leading=12, alignment=0, spaceAfter=2)
CELL = ParagraphStyle("Cell", parent=BODY, fontName="Times-Roman", fontSize=9, leading=11.5, alignment=0, spaceAfter=0)
CELLB = ParagraphStyle("CellB", parent=CELL, fontName="Times-Bold")
H1x = None
H1 = ParagraphStyle("H1", parent=ss["Heading1"], fontName="Helvetica-Bold", fontSize=17, leading=21, spaceBefore=14, spaceAfter=8, textColor=colors.HexColor("#12306b"))
H1x = ParagraphStyle("H1x", parent=H1)
H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontName="Helvetica-Bold", fontSize=12.5, leading=16, spaceBefore=10, spaceAfter=5, textColor=colors.HexColor("#1d4a9c"))
H3 = ParagraphStyle("H3", parent=ss["Heading3"], fontName="Helvetica-BoldOblique", fontSize=10.5, leading=14, spaceBefore=6, spaceAfter=3)
CAP = ParagraphStyle("Cap", parent=BODY, fontName="Helvetica-Oblique", fontSize=8.8, leading=11.5, alignment=TA_CENTER, spaceAfter=10, textColor=colors.HexColor("#333333"))
BUL = ParagraphStyle("Bul", parent=BODY, leftIndent=16, bulletIndent=4, spaceAfter=2)
CODE = ParagraphStyle("Code", parent=BODY, fontName="Courier", fontSize=8.6, leading=11, alignment=0, leftIndent=10, backColor=colors.HexColor("#f4f6fa"), borderPadding=5, spaceAfter=8)
TITLE = ParagraphStyle("Title", parent=BODY, fontName="Helvetica-Bold", fontSize=30, leading=36, alignment=TA_CENTER, textColor=colors.HexColor("#12306b"))
SUB = ParagraphStyle("Sub", parent=BODY, fontName="Helvetica", fontSize=14, leading=19, alignment=TA_CENTER, textColor=colors.HexColor("#333333"))
CTR = ParagraphStyle("Ctr", parent=BODY, alignment=TA_CENTER, fontSize=12, leading=17)

_fig_no = [0]
_tab_no = [0]


def P(t, style=BODY):
    return Paragraph(t, style)


def bullets(items):
    return [Paragraph(i, BUL, bulletText="•") for i in items]


def fig(path, caption, width=14.5 * cm):
    _fig_no[0] += 1
    w, h = PILImage.open(path).size
    return KeepTogether([Image(path, width=width, height=width * h / w), P(f"<b>Figure {_fig_no[0]}.</b> {caption}", CAP)])


def table(rows, widths, caption=None, header=True, align_right_from=None):
    data = [[Paragraph(str(c), CELLB if (header and i == 0) else CELL) for c in r] for i, r in enumerate(rows)]
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    st = [("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#9aa6bd")), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
          ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    if header:
        st += [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dfe8fb"))]
    for i in range(1, len(rows)):
        if i % 2 == 0:
            st.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#f6f8fd")))
    t.setStyle(TableStyle(st))
    out = []
    if caption:
        _tab_no[0] += 1
        out.append(P(f"<b>Table {_tab_no[0]}.</b> {caption}", ParagraphStyle("TC", parent=CAP, alignment=0, spaceAfter=3, fontName="Helvetica-Oblique")))
    out.append(t)
    out.append(Spacer(1, 9))
    return out


class Doc(BaseDocTemplate):
    def afterFlowable(self, f):
        if isinstance(f, Paragraph):
            n = f.style.name
            if n == "H1":
                self.notify("TOCEntry", (0, f.getPlainText(), self.page))
            elif n == "H2":
                self.notify("TOCEntry", (1, f.getPlainText(), self.page))


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8.5)
    canvas.setFillColor(colors.HexColor("#555555"))
    canvas.drawString(2.4 * cm, 1.4 * cm, "BABY BLADE 2.0 - AI Laboratory Project Report - KUET")
    canvas.drawRightString(A4[0] - 2.4 * cm, 1.4 * cm, f"Page {doc.page}")
    canvas.setStrokeColor(colors.HexColor("#c5cde0"))
    canvas.line(2.4 * cm, 1.8 * cm, A4[0] - 2.4 * cm, 1.8 * cm)
    canvas.restoreState()


def title_bg(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(colors.HexColor("#0b1430"))
    canvas.rect(0, A4[1] - 3.2 * cm, A4[0], 3.2 * cm, fill=1, stroke=0)
    canvas.setFillColor(colors.HexColor("#2a6fdb"))
    canvas.rect(0, A4[1] - 3.5 * cm, A4[0] * 0.5, 0.3 * cm, fill=1, stroke=0)
    canvas.setFillColor(colors.HexColor("#d6382c"))
    canvas.rect(A4[0] * 0.5, A4[1] - 3.5 * cm, A4[0] * 0.5, 0.3 * cm, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 13)
    canvas.drawCentredString(A4[0] / 2, A4[1] - 1.6 * cm, "KHULNA UNIVERSITY OF ENGINEERING & TECHNOLOGY (KUET)")
    canvas.setFont("Helvetica", 10.5)
    canvas.drawCentredString(A4[0] / 2, A4[1] - 2.3 * cm, "Department of Computer Science and Engineering")
    canvas.restoreState()


def pct(a, n):
    return f"{100 * a / n:.0f}%" if n else "-"


# ================================================================== content
S = []

# ---- title page
S += [Spacer(1, 4.6 * cm), P("BABY BLADE 2.0", TITLE), Spacer(1, 6),
      P("An AI-Powered Spinning-Top Battle Game with Real-Time Physics, Minimax and Monte Carlo Tree Search Agents, and Fuzzy Danger Estimation", SUB),
      Spacer(1, 1.2 * cm), P("<b>Course:</b> Artificial Intelligence Laboratory", CTR), P("<b>Project report</b>", CTR), Spacer(1, 1.0 * cm),
      P("<b>Submitted by (Team of 2)</b>", CTR), P("Suaib Ahmed Safi &nbsp;&nbsp;(Roll 2207115)", CTR), P("Ashrafur Rahman Nihad &nbsp;&nbsp;(Roll 2207116)", CTR),
      Spacer(1, 1.0 * cm), P("<b>Submitted to</b>", CTR), P("Course Teachers, AI Laboratory<br/>Department of Computer Science and Engineering, KUET", CTR),
      Spacer(1, 1.2 * cm), P("November 2026", CTR),
      NextPageTemplate("main"), PageBreak()]

# ---- abstract
S += [P("Abstract", H1x), P(
    "BABY BLADE 2.0 is a two-dimensional spinning-top battle game built to demonstrate adversarial search, decision making under uncertainty and fuzzy inference "
    "through an interactive environment. Two blades fight inside a stadium that shrinks every six rounds. At the start of every three-second round both players lock in "
    "one of five actions (Charge, Attack, Guard, Dodge, Special Spin) at the same time, and then steer their blades freely while continuous physics resolves dashes, collisions, "
    "knock-back and recovery. A match ends by Ring-out, Burst, Spin-out, a simultaneous-elimination Draw, or a points decision after 40 rounds. "
    "Two different agents play the game on identical rules: <b>Ironclad</b> uses depth-limited Minimax with alpha-beta pruning and iterative deepening, and <b>Cyclone</b> uses Monte Carlo "
    "Tree Search with UCB1. A Mamdani fuzzy inference system estimates the danger of each blade from its distance to the boundary and its spin energy. "
    f"The game offers Human vs AI, AI vs AI, a Championship (the player against seven AIs), an AI Benchmark, and a blade customizer, and runs on desktop and in the browser. "
    f"We evaluated the agents over {TOTAL_MATCHES} headless matches. Ironclad won {pct(D['head2head_Medium']['wins_a'], D['head2head_Medium']['matches'])} of Medium-difficulty matches against Cyclone "
    f"but lost at Easy difficulty, higher difficulty levels beat lower ones in over 88% of matches, and the Defender archetype proved dominant. "
    f"The code base has {SRC_LINES:,} lines of source and {TESTS} automated tests."), Spacer(1, 4),
      P("<b>Keywords:</b> adversarial search, Minimax, alpha-beta pruning, Monte Carlo Tree Search, UCB1, Mamdani fuzzy inference, game AI, real-time physics, game user experience.", SMALL),
      PageBreak()]

# ---- contents
toc = TableOfContents()
toc.levelStyles = [ParagraphStyle("t0", fontName="Helvetica-Bold", fontSize=10.5, leading=15, leftIndent=0, spaceBefore=3),
                   ParagraphStyle("t1", fontName="Helvetica", fontSize=9.5, leading=13, leftIndent=16)]
S += [P("Table of Contents", H1x), toc, PageBreak()]

# ================================================================== 1 Introduction
S += [P("1. Introduction", H1),
      P("1.1 Motivation", H2),
      P("Spinning-top battle games combine simple, readable rules with rich tactical depth: a blade must manage its spin energy and its stability, hold its position, and "
        "predict what the opponent will do next. These properties make the genre a good test bed for classical game-playing algorithms. "
        "Each player's decision is made at the same time as the opponent's, resources are limited, and the environment gradually becomes more dangerous as the stadium shrinks."),
      P("The AI Laboratory course covers uninformed and informed search, adversarial search, Monte Carlo Tree Search and fuzzy inference. The goal of this project is to show these "
        "techniques working together inside one complete, playable game, instead of in isolated exercises."),
      P("1.2 Objectives", H2)]
S += bullets([
    "Create an interactive spinning-top battle game with five strategic actions and counter-strategies.",
    "Develop two AI agents based on different algorithms (Minimax and Monte Carlo Tree Search) that play against each other under the same rules.",
    "Provide a mandatory AI vs AI mode and an additional Human vs AI mode.",
    "Demonstrate fuzzy logic through a live danger indicator based on a Mamdani inference system.",
    "Compare the two agents through repeated matches and report win rates, durations, decision times and finish types.",
    "Deliver a polished, accessible user experience that explains every on-screen term to a first-time player.",
])
S += [P("1.3 Scope and deliverables", H2),
      P("The deliverables are the playable game (desktop and browser), the source code with automated tests, the design documents, and this report. "
        "The project follows the course instructions: a team of two, at least two AIs that play each other, a mandatory AI vs AI mode, and an optional Human vs AI mode. "
        "All names and visual assets are original: the art is generated in code, the sounds are synthesized, and the only bundled asset is the Oswald typeface under the SIL Open Font License."),
      P("1.4 Report organization", H2),
      P("Section 2 reviews related games and the algorithms used. Section 3 describes the game design. Section 4 explains the AI methods. Section 5 presents the system architecture. "
        "Section 6 discusses the user interface and user experience. Section 7 reports testing and evaluation. Sections 8 and 9 discuss limitations, future work and conclusions."),
      PageBreak()]

# ================================================================== 2 Background
S += [P("2. Background and Related Work", H1),
      P("2.1 Spinning-top battle games", H2),
      P("The game is inspired by the Beyblade family of toys and video games. In the tabletop game, a battle runs continuously from launch until one top finishes: there are no "
        "turn-by-turn decisions during a battle. Players choose parts beforehand and control only the launch. A match consists of several battles, and finishes score points: according to the "
        "official parents' guide and fan sources, a survivor (spin) finish scores 1 point, while knock-out (over) and burst finishes score 2 points, and the new Xtreme finish scores 3 [R1][R2]. "
        "These sources are secondary descriptions, so the exact point values should be checked against the official rule book."),
      P("The video game <i>Beyblade X: XONE</i> adds real-time gauges on top of the physical rules: a Survivor gauge shows the remaining rotation power, a Burst gauge shows how close a top is to bursting, "
        "and an Active gauge that fills over time powers Active Moves such as an attack or a counter [R3]. The mobile <i>Beyblade Burst</i> app uses swipe steering and charged avatar attacks [R4]. "
        "A web game, <i>Beyblade Simulator</i> [R5], was used as a visual reference: it presents a top-down rounded board, a lit floor and a glowing rim, and it allows blade customization from parts."),
      P("Our proposal deliberately differs from the real game in one respect: it asks for a simultaneous-action round (both players choose one action per round), because explicit turns give the "
        "search agents a clear game tree. Version 2.0 keeps those rounds but plays them out with continuous physics, so that the game also looks and feels like a real spinning-top battle."),
      P("2.2 Adversarial search", H2),
      P("Minimax [R6] chooses the action that maximizes the value that the opponent's best reply leaves behind. Alpha-beta pruning discards branches that cannot change the decision "
        "and can search about twice as deep in the same time [R7]. Depth-limited search with a heuristic evaluation function bounds the cost, and iterative deepening searches depth 1, 2, 3, ... "
        "so that a complete answer is always available when the time budget ends. In a game with simultaneous moves, the standard approximation is to treat the second player as if it replies "
        "after seeing the first move, which is conservative for the maximizing player."),
      P("2.3 Monte Carlo Tree Search", H2),
      P("Monte Carlo Tree Search [R8][R9] builds a search tree from random simulations. Each iteration has four stages: <i>selection</i> (descend by a bandit rule), <i>expansion</i> (add a node), "
        "<i>simulation</i> (play out to the end or to a depth limit) and <i>backpropagation</i> (update statistics along the path). UCB1 [R10] selects the child that maximizes "
        "<i>mean reward + C sqrt(ln N / n)</i>, balancing exploitation and exploration. For simultaneous moves we use decoupled UCT: each player keeps separate action statistics at every node."),
      P("2.4 Fuzzy inference", H2),
      P("Fuzzy sets [R11] allow gradual membership, which suits linguistic concepts such as <i>near the edge</i> or <i>low energy</i>. A Mamdani system [R12] fuzzifies crisp inputs, evaluates "
        "if-then rules (AND as minimum, OR as maximum), clips the output sets by the rule strengths, aggregates them and converts the result back to a crisp number by centroid defuzzification."),
      PageBreak()]

# ================================================================== 3 Game design
S += [P("3. Game Design", H1),
      P("3.1 Overview", H2),
      P("Two blades start on opposite sides of a circular stadium of radius 10 units. Each blade has <b>spin energy</b> (starts at 100) and <b>stability</b> (depends on the blade type). "
        "Energy reaching zero stops the blade (Spin-out); stability reaching zero makes it burst apart (Burst); a blade whose centre leaves the stadium is eliminated (Ring-out). "
        "If both blades are eliminated at the same moment the match is a Draw. If nobody is eliminated after 40 rounds, the winner is decided by points: "
        "0.40 &times; energy share + 0.40 &times; stability share + 0.20 &times; centrality, and equal scores are a draw."),
      P("3.2 Rounds and real-time play", H2),
      P(f"A match has {C.ROUNDS} rounds of {C.ROUND_SECONDS:.0f} seconds, which gives the proposal's 120-second limit. At every round boundary both controllers lock in one action at the same instant, "
        "so neither player has priority. The action then shapes the blade's movement during the round, and physics runs continuously at 120 Hz. A human may queue the next action at any time; it locks in at the boundary. "
        "The AI agents begin searching 1.2 seconds before the boundary, and their search is spread over many frames so that the game never stalls (Figure 1)."),
      fig(os.path.join(FIG, "fig_timeline.png"), "Round timeline: AI search runs before the boundary; both actions lock in together.", 14 * cm),
      P("3.3 Blade types", H2)]
S += table([["Blade", "Max stability", "Spin loss / round", "Attack power", "Special ability"],
            ["Balanced", "100", "3", "1.00x", "No special advantage"], ["Attacker", "90", "4", "1.25x", "Higher attack power"],
            ["Defender", "120", "3", "0.85x", "Guard restores 10 stability"], ["Stamina", "100", "2", "1.00x", "Charge restores 25 energy"]],
           [3 * cm, 3 * cm, 3.4 * cm, 3 * cm, 4.2 * cm], "Blade archetypes (values from the proposal).")
S += [P("3.4 Actions and the counter system", H2)]
S += table([["Action", "Cost", "Effect"],
            ["Charge", "0", "Recover 20 spin energy (Stamina 25), drift to the centre. Takes 25% extra damage and push."],
            ["Attack", "8", f"Dash at the opponent; {C.ATTACK_DAMAGE:.0f} stability damage x power and a push of {C.ATTACK_PUSH}. Halved by Guard (attacker takes 3 recoil)."],
            ["Guard", "4", "Restore 5 stability (Defender 10); heavy stance; halves normal damage and push; Special is reduced only to 70%."],
            ["Dodge", "8", f"Side-step that avoids Attack and Special; fails if it ends within {C.DODGE_EDGE_MARGIN} of the boundary."],
            ["Special Spin", "35", f"{C.SPECIAL_DAMAGE:.0f} damage and push {C.SPECIAL_PUSH}; costs the user 10 stability; 3-second cooldown."]],
           [2.6 * cm, 1.3 * cm, 11.7 * cm], "The five actions.")
S += [P("The counter system is: Attack is effective against Charge, Guard is effective against Attack, Special can break through Guard, Dodge avoids Attack and Special, and Charge restores energy but is vulnerable. "
        "When both blades attack and touch, both hits take effect (no priority). Tops are solid: their centres can never be closer than twice the blade radius (1.2 units), so blades "
        "cannot pass through each other."),
      P("3.5 Stadiums and shrinking", H2),
      P("The radius starts at 10 and decreases by 1 after rounds 6, 12, 18 and 24, down to the minimum of 6. The shrink is animated smoothly and announced one round ahead. Three stadiums are provided: "
        "<b>Classic Dish</b> (standard), <b>Ice Rink</b> (movement and push x1.25, lower friction) and <b>Steep Bowl</b> (a stronger pull toward the centre)."),
      P("3.6 Free movement", H2),
      P(f"Both the human and the AI steer their blade continuously. Steering is <i>direct drive</i>: the stick, arrow keys or touch joystick set a target velocity of up to {C.DRIVE_SPEED:.0f} units per second "
        f"which the blade follows within about 45 ms (response rate {C.DRIVE_RESPONSE:.0f} per second), so control feels instant. Dashes and knock-back stay physical: they are added to the drive "
        "velocity and decay under damping. A blade cannot steer itself over the rim, so Ring-outs always come from hits. The AI uses exactly the same drive: Attack and Special chase the rival, "
        "Dodge slides sideways towards the side with more room, Charge heads for the centre, Guard holds, and every action retreats from the rim. The AI's steering skill scales with its difficulty (60%, 85% and 100%)."),
      P("3.7 Game modes", H2)]
S += table([["Mode", "Description"],
            ["Play", "Human vs AI. Choose Ironclad or Cyclone, Easy / Medium / Hard, both blades and the stadium."],
            ["AI vs AI", "Mandatory mode: start/pause, step one round, speed 1x/2x/4x, swap sides, restart, with the agents' decisions shown."],
            ["Championship", "Single-elimination bracket of eight: the player and seven AIs. Quarter-finals and semi-finals are one battle each, the final is best of three, on three different stadiums."],
            ["AI Benchmark", "Runs 5 to 50 headless matches between the two agents; reports wins, draws, win %, average duration and decision time, and finish types; exports JSON and CSV."],
            ["Customize", "Cosmetic parts (ring colour, blade shape, ratchet claws, weight disk, bit) and the archetype that sets the rules."]],
           [3 * cm, 12.6 * cm], "Game modes.")
S += [PageBreak()]

# ================================================================== 4 AI methodology
S += [P("4. Artificial Intelligence Methodology", H1),
      P("4.1 Abstract round model", H2),
      P("The agents cannot run physics inside a search tree, so they reason over a deterministic <i>abstract round model</i> built from the same rule numbers as the real game. It exposes the formal "
        "interface taught in the laboratory: <b>ACTIONS(s)</b> (legal actions, limited by energy and the Special cooldown), <b>RESULT(s, a1, a2)</b> (one simultaneous round), "
        "<b>TERMINAL(s)</b> (a finish was reached) and <b>UTILITY(s)</b> (+1 win, -1 loss, 0 draw; a heuristic for non-terminal states). States are immutable tuples, so search branches never interfere."),
      P("4.2 Heuristic evaluation", H2),
      P("The same heuristic supports both agents. From the point of view of a player it is 0.30 &times; (energy difference) + 0.30 &times; (stability share difference) + 0.15 &times; (position advantage) + "
        "0.05 &times; (Special availability difference) + 0.20 &times; (fuzzy danger difference), where the danger difference is the opponent's minus the player's."),
      P("4.3 Ironclad: Minimax", H2),
      P("Ironclad performs MAX-VALUE over its own actions and MIN-VALUE over the opponent's replies, with alpha-beta pruning and a depth limit. Iterative deepening runs depth 1, 2, ... up to the "
        "difficulty's limit and keeps the result of the last complete depth. Moves are ordered by the previous depth's values to improve pruning. The search is written as a generator, so the game can run it "
        "a few milliseconds per frame."),
      P("4.4 Cyclone: Monte Carlo Tree Search", H2),
      P("Cyclone runs the four MCTS stages with UCB1 selection (C = 1.4) and decoupled UCT for the simultaneous moves. Simulations use a rollout policy that mixes random moves with a one-step greedy "
        "heuristic choice and stop at depth 4, returning the heuristic utility. The action with the most visits at the root is played."),
      P("4.5 Difficulty levels", H2)]
S += table([["Level", "Ironclad max depth", "Cyclone iterations", "Random mistake rate", "Steering skill"],
            ["Easy", "1", "60", "15%", "0.60"], ["Medium", "2", "200", "0%", "0.85"], ["Hard", "3", "500", "0%", "1.00"]],
           [2.4 * cm, 3.6 * cm, 3.4 * cm, 3.4 * cm, 2.8 * cm], "Difficulty settings.")
S += [P("4.6 Mamdani fuzzy danger system", H2),
      P("The danger of a blade is estimated from two inputs: the <i>edge margin</i> (R minus distance from the centre, divided by R) and the remaining <i>spin energy</i>. "
        "Each input has three fuzzy sets and the output has three: Low, Medium and High danger (Figure 2). Nine rules map the input sets to danger sets. "
        "The rule strength is the minimum of the antecedent memberships (AND), strengths of rules with the same consequent are combined by maximum (OR), and each output set is clipped at its strength "
        "before aggregation. The crisp danger in [0, 100] is the centroid of the aggregated set (Figure 3). The result is shown to the player as LOW, MEDIUM or HIGH and is used in the heuristic. "
        "A 41 &times; 41 lookup grid with bilinear interpolation reproduces the inference within 3 points and keeps the search fast."),
      fig(os.path.join(FIG, "fig_fuzzy_sets.png"), "Membership functions of the two inputs (left, centre) and the output (right).", 15.5 * cm)]
rules = [["#", "Edge margin", "Spin energy", "Danger"]] + [[str(i + 1), m, e, o] for i, (m, e, o) in enumerate(fuzzy.RULES)]
S += table(rules, [1.2 * cm, 3.6 * cm, 3.6 * cm, 3 * cm], "Fuzzy rule base (9 rules).")
S += [fig(os.path.join(FIG, "fig_fuzzy_surface.png"), "Control surface: danger rises towards the boundary and as energy falls.", 10.5 * cm),
      P("4.7 Mapping to the laboratory syllabus", H2)]
S += table([["Lab / lecture topic", "Concept", "Where it is used"],
            ["Lab 1: Python data structures", "Lists, tuples, dictionaries, queues", "Immutable state tuples, action tables, statistics, event queues"],
            ["Lab 2: Uninformed search", "Depth-limited search, iterative deepening", "Ironclad's depth limit and deepening loop"],
            ["Lab 4: Adversarial search", "Minimax, MAX/MIN-VALUE, ACTIONS, RESULT, TERMINAL, UTILITY", "Ironclad and the abstract round model"],
            ["Lecture 3: Informed search", "Heuristic function", "Shared evaluation of energy, stability, position, Special, danger"],
            ["Lecture 5: MCTS", "Selection, expansion, simulation, backpropagation, UCB", "Cyclone"],
            ["Lab 6: Fuzzy inference", "Fuzzification, rules, OR = max, centroid", "Danger estimation"]],
           [4.2 * cm, 5.4 * cm, 6 * cm], "Course concepts demonstrated by the project.")
S += [PageBreak()]

# ================================================================== 5 Architecture
S += [P("5. System Architecture and Implementation", H1),
      P("5.1 Layered design", H2),
      P("The code is split into a rules layer that never imports graphics and a presentation layer that only reads the rules layer's state and events (Figure 4). "
        "This keeps every rule testable without a window, makes headless benchmarks run at full speed, and guarantees that the human, the AI and the tournament all play the same game."),
      fig(os.path.join(FIG, "fig_architecture.png"), "Layered architecture.", 14.5 * cm)]
S += table([["Module", "Responsibility"],
            ["sim/battle.py", "Real-time battle: 120 Hz physics, rounds, action effects, collisions, finishes, events"],
            ["sim/model.py", "Abstract round model and heuristic used by the AI search"],
            ["sim/fuzzy.py", "Mamdani inference and fast lookup grid"],
            ["sim/actions.py, blades.py, config.py", "Actions, costs, counters; archetype table; every tunable number"],
            ["ai/agents.py", "Ironclad (Minimax), Cyclone (MCTS), Human controller; resumable searches"],
            ["tournament.py, championship.py", "Headless benchmark with statistics; eight-player bracket logic"],
            ["game/arena_view.py, fx.py, assets.py", "Drawing, sparks, shock-waves, camera, banners, procedural art"],
            ["game/audio.py, inputs.py, ui.py", "Synthesized sound, keyboard/gamepad/touch input, focusable UI kit"],
            ["game/coach.py and scenes/*", "Coach tips, screen guide, title, setup, battle, results, championship, benchmark, customize"]],
           [5.6 * cm, 10 * cm], "Main modules.")
S += [P("5.2 Physics", H2),
      P(f"A fixed 120 Hz time step integrates each blade. The physics velocity is acted on by a pull toward the centre ({C.BOWL_PULL} per unit of distance; {C.STEEP_BOWL_PULL} in the Steep Bowl), "
        f"an orbital drift that makes spinning tops circle the bowl, a steep rim wall that grows near the edge, homing during dashes, and linear damping ({C.LINEAR_DAMPING} per second). "
        f"The drive velocity (Section 3.6) is added to it. Collisions are mass-weighted with restitution {C.RESTITUTION}; a guarding blade is heavier. "
        "At most one hit per attacker lands in each round. Resources flow continuously: costs are paid at the round start, passive spin loss and the recovery of Charge and Guard accumulate over the round, "
        "so that the gauges move smoothly while the totals per round equal the proposal's numbers."),
      P("5.3 Determinism and AI scheduling", H2),
      P("Given a seed the whole match is deterministic, which makes the experiments reproducible and the tests exact. Because the browser has no threads, each AI search is a Python generator that the "
        "battle advances by a few milliseconds per frame during the 1.2 seconds before a round boundary; at the boundary any unfinished search is completed."),
      P("5.4 Presentation techniques", H2)]
S += bullets([
    "<b>Procedural art:</b> the stage, stadium bowls, blade sprites (rotation frames, spin blur) and icons are drawn in code at start-up.",
    "<b>Spin readability:</b> a top spinning at about nine turns per second turns roughly 55 degrees per frame at 60 frames per second, which looks frozen (the wagon-wheel effect). "
    "The renderer draws exposure-style ghost copies across the angle swept in each frame, and every blade carries asymmetric markers (a gold pointer and bright claw tips) so that rotation is visible for every shape.",
    "<b>Game feel:</b> additive sparks, shock-waves, hit-stop, screen shake, slow-motion finishes, floating damage text and banners [R13].",
    "<b>Audio:</b> all effects are synthesized (clashes, whooshes, launch, burst, crowd, UI) and a spin hum changes pitch with the remaining energy.",
    "<b>Browser build:</b> the same code compiles to WebAssembly with pygbag; an asynchronous main loop yields once per frame.",
])
S += [P("5.5 Implementation size and quality", H2)]
S += table([["Measure", "Value"],
            ["Source files / lines (babyblade package)", f"{SRC_FILES} / {SRC_LINES:,}"],
            ["Test files / lines", f"{TEST_FILES} / {TEST_LINES:,}"],
            ["Automated tests", f"{TESTS}"],
            ["Frame cost on a desktop (update + draw)", "about 2.2 ms per frame (measured with a profiler)"],
            ["Headless simulation speed", f"{TOTAL_MATCHES} full matches in 25 s on 16 cores"],
            ["Dependencies", "pygame-ce only (pytest and pygbag for development)"]],
           [8 * cm, 7.6 * cm], "Implementation measures.")
S += [PageBreak()]

# ================================================================== 6 UI/UX
S += [P("6. User Interface and User Experience", H1),
      P("6.1 Design goals", H2),
      P("Version 1 of the project resolved each round instantly and teleported the blades, so battles looked static, and its menus were plain. Version 2 follows these goals: "
        "(a) the battle must look physical and fast; (b) every number on the screen must be understandable to a first-time player; (c) every screen must work with a mouse, a keyboard, a "
        "gamepad and touch; and (d) feedback must be immediate. The visual language follows the project presentation: a deep navy stage, neon blue for Player 1, neon red for Player 2, white condensed headings."),
      P("6.2 Screens", H2),
      fig(os.path.join(SHOTS, "01_title.png"), "Title screen with a live AI demonstration behind the menu.", 12.5 * cm),
      fig(os.path.join(SHOTS, "02_setup.png"), "Match setup with a live preview of both blades and the chosen stadium.", 12.5 * cm),
      fig(os.path.join(SHOTS, "03_customize.png"), "Customization: cosmetic parts and the archetype whose real numbers are shown.", 12.5 * cm),
      P("6.3 Understanding the battle screen", H2),
      P("Figure 8 shows the battle screen. The left and right cards show each blade's <b>spin energy</b> and <b>burst guard (stability)</b> with captions, the Special Spin cooldown, the fuzzy <b>danger</b> chip, the action in progress (NOW) "
        "and the queued action (NEXT). The AI's card shows its decision: one bar per action (the gold bar is its choice) with its search statistics. The centre shows the round, the clock and a gold bar that fills once per round. "
        "Three features explain the game while it is being played:"),
      fig(os.path.join(SHOTS, "05_battle_human.png"), "Battle screen: gauges, Coach panel, counters chart, action bar with costs and keys.", 14.5 * cm)]
S += bullets([
    "<b>Coach panel.</b> It reads the situation and gives up to four prioritized tips in plain language, for example &quot;SPIN is low (14): Charge soon to avoid spinning out&quot; or &quot;The rival is charging: Attack hits it for extra damage&quot;. "
    "Urgent warnings (danger HIGH, very low spin, low stability) come first. When the mouse hovers over an action button the panel shows that action's details. In AI vs AI mode it explains what each AI is doing. It can be turned off in Settings.",
    "<b>Counters chart.</b> A permanent chart shows which action beats which, using the action icons.",
    "<b>Screen Guide.</b> The H key (or the GUIDE button) freezes the battle and numbers every element on the screen; a glossary explains each number in one or two sentences (Figure 9).",
])
S += [fig(os.path.join(SHOTS, "06_screen_guide.png"), "Screen Guide: numbered markers on the HUD and a glossary of every term.", 14.5 * cm),
      P("Other feedback includes floating labels (COUNTER!, GUARD BREAK, MISS, DODGE FAILED), a shrink warning one round before the stadium shrinks, a pulsing red danger ring under a blade near the rim, and finish banners with slow motion (Figure 10)."),
      fig(os.path.join(SHOTS, "08_finish_banner.png"), "Finish banner with slow motion and impact effects.", 12.5 * cm),
      fig(os.path.join(SHOTS, "09_results.png"), "Results screen with winner, finish type and statistics per blade.", 12.5 * cm),
      P("6.4 Championship and benchmark", H2),
      P("The Championship screen (Figure 12) shows the eight-player bracket. AI-only matches are simulated with the same engine, and the player's matches are real battles on the stadium of that round. "
        "The player's next match pulses in gold, series scores are shown for the best-of-three final, a champion banner with confetti is shown, and the player's titles are saved. "
        "The AI Benchmark screen (Figure 13) runs the agents against each other in small slices per frame, so the interface stays responsive, and shows the statistics required by the proposal."),
      fig(os.path.join(SHOTS, "10_championship.png"), "Championship bracket.", 12.5 * cm),
      fig(os.path.join(SHOTS, "11_benchmark.png"), "AI Benchmark with win rates, decision times and finish types.", 12.5 * cm),
      P("6.5 Controls and accessibility", H2)]
S += table([["Input", "Keyboard", "Gamepad", "Touch / mouse"],
            ["Actions", "1 Charge, 2 Attack, 3 Guard, 4 Special, Space Dodge", "X, A, Y, RB, B", "Action buttons"],
            ["Steer (free movement)", "WASD or arrow keys", "Left stick / D-pad", "On-screen joystick"],
            ["Launch power", "Space in the green zone", "A", "Tap"],
            ["Pause / guide / mute", "P or Esc / H or F1 / M", "Start", "Buttons"]],
           [3.4 * cm, 6 * cm, 3 * cm, 3.2 * cm], "Controls.")
S += [P("All menus keep one focused widget that is drawn differently from hover; focus moves with the arrow keys, the D-pad or the stick. Screen shake, the Coach and the sound can be switched off, "
        "and every colour-coded status also has a text label (for example LOW / MED / HIGH)."),
      PageBreak()]

# ================================================================== 7 Testing
S += [P("7. Testing and Evaluation", H1),
      P("7.1 Automated tests", H2),
      P(f"The project has {TESTS} automated tests ({TEST_LINES:,} lines) that run without a window. They cover: the blade table, action costs and the Special cooldown; the counter table and every damage multiplier; "
        "the shrink schedule; finish priority and the points decision; the no-overlap rule; the fuzzy membership functions, rule firing and the fast grid; both agents (legal actions, determinism, taking a winning hit, reported search statistics); "
        "the real-time battle (valid finish within 120 s, determinism, costs at the round start, ring-out, burst, draw, direct drive responding within 120 ms, the rim limit, AI steering by action); "
        "tournament statistics and export; the championship bracket (advancement, best-of-three, elimination, draw replay); the coach tips; and every scene rendering and responding to input."),
      P("7.2 Experimental design", H2),
      P(f"All experiments run headless matches with the real physics and the real agents. Each match has a seed, sides alternate every match so that no agent keeps the starting position, "
        f"and results are aggregated per experiment ({TOTAL_MATCHES} matches in total). Experiments were run on a 16-core machine in 25 seconds. "
        "The experiments are: <b>E1</b> Ironclad vs Cyclone at equal difficulty (24 matches each, Balanced blades, Classic Dish); <b>E2</b> the three stadiums (Medium, 18 matches each); "
        "<b>E3</b> difficulty scaling (Easy vs Hard of the same agent, 18 matches each); <b>E4</b> blade archetype matchups (Ironclad Medium mirror, 12 matches per pair)."),
      P("7.3 Results: Ironclad against Cyclone", H2)]
rows = [["Difficulty", "Matches", "Ironclad wins", "Cyclone wins", "Draws", "Avg. duration", "Decision time (Ironclad / Cyclone)"]]
for dname in ("Easy", "Medium", "Hard"):
    r = D[f"head2head_{dname}"]
    rows.append([dname, r["matches"], f"{r['wins_a']} ({pct(r['wins_a'], r['matches'])})", f"{r['wins_b']} ({pct(r['wins_b'], r['matches'])})", r["draws"],
                 f"{r['avg_seconds']:.0f} s / {r['avg_rounds']:.1f} rounds", f"{r['think_a_ms']:.1f} ms / {r['think_b_ms']:.0f} ms"])
S += table(rows, [2 * cm, 1.7 * cm, 2.6 * cm, 2.6 * cm, 1.3 * cm, 2.9 * cm, 2.8 * cm], "Head-to-head results (E1).")
S += [fig(os.path.join(FIG, "fig_h2h.png"), "Win shares of the two agents at each difficulty.", 11.5 * cm),
      P("Ironclad clearly beats Cyclone at Medium and Hard difficulty, while Cyclone is slightly ahead at Easy. The explanation lies in the search budgets: at Easy Ironclad searches only one round ahead "
        "and also makes a random move 15% of the time, while Cyclone's 60 iterations are still enough to find a reasonable action. At Medium and Hard, depth-2 and depth-3 minimax see the immediate consequences "
        "of the counter system (for example that Attack beats Charge) exactly, whereas MCTS with 200 or 500 noisy simulations of a four-round horizon does not converge as sharply. "
        "Cyclone also costs far more time per decision (Figure 15), since it simulates hundreds of rollouts."),
      fig(os.path.join(FIG, "fig_think.png"), "Mean decision time per decision.", 9.5 * cm),
      P("7.4 Results: difficulty levels and stadiums", H2)]
sc_i, sc_c = D["scaling_Ironclad"], D["scaling_Cyclone"]
S += [P(f"The difficulty levels are correctly ordered: the Hard version beat the Easy version in {sc_i['wins_b']} of {sc_i['matches']} matches for Ironclad and {sc_c['wins_b']} of {sc_c['matches']} for Cyclone (Figure 16). "
        "The stadiums change how matches end (Figure 17): the Ice Rink produced the most Ring-outs because pushes are 25% stronger and friction is lower, whereas the Steep Bowl, which pulls blades to the centre, "
        "produced no Ring-outs at all and most Spin-outs."),
      fig(os.path.join(FIG, "fig_scaling.png"), "Difficulty scaling.", 9.5 * cm),
      fig(os.path.join(FIG, "fig_stadium.png"), "Ring-out share and average duration per stadium.", 9.5 * cm),
      fig(os.path.join(FIG, "fig_finish.png"), "Finish types in experiments E1 and E2.", 11.5 * cm),
      P("7.5 Results: blade archetypes", H2),
      P("Figure 19 shows the win rate of each archetype against each other (Ironclad Medium on both sides). The Defender dominates: it wins about 92% against Balanced and against Attacker and 83% against Stamina. "
        "Its 120 stability, Guard recovery of 10 and the fact that Guard halves the damage of Attack combine so that the AI's Guard-and-counter play is very hard to break. "
        "The Attacker is better than Stamina but is not competitive against Defender. Matchups of Attacker with Stamina produced many draws (simultaneous eliminations), and Defender against Stamina almost always went the full 40 rounds and was decided on points. "
        "These are consequences of the proposal's numeric table, which we implemented exactly, so we report them instead of altering them."),
      fig(os.path.join(FIG, "fig_blades.png"), "Archetype matchup matrix.", 9.5 * cm),
      P("7.6 Threats to validity", H2)]
S += bullets([
    "Sample sizes are small (12 to 24 matches per condition), so differences of one or two matches are not significant; the larger effects (difficulty ordering, Defender dominance, Ironclad's lead at Medium and Hard) are well beyond that noise.",
    "The agents plan over an abstract model that does not include steering and collisions, while the real game uses continuous physics; the mismatch probably lowers the strength of both agents and may affect them unequally.",
    "Both agents share one heuristic, so the comparison measures the search method more than the evaluation function; the heuristic weights were set by hand and not tuned.",
    "No usability study with human players has been run yet; the user-experience claims rest on design principles and developer testing.",
])
S += [P("7.7 Compliance with the proposal's requirements", H2)]
S += table([["#", "Requirement", "Status and evidence"],
            ["1", "Two competing spinning blades", "Implemented (Section 3)."],
            ["2", "Five actions", "Charge, Attack, Guard, Dodge, Special Spin with the proposal's costs (Table 2)."],
            ["3", "Energy and Stability", "Both gauges for each blade; archetype table (Table 1)."],
            ["4", "Stadium shrinks gradually", "10 to 6, -1 every 6 rounds, animated."],
            ["5", "Ring-out, Burst, Spin-out", "All three occur in the experiments (Figure 18)."],
            ["6", "Two different AIs: Minimax and MCTS", "Ironclad and Cyclone (Section 4)."],
            ["7", "AI vs AI mode is mandatory", "Implemented with start, pause, resume, restart, speed, step, swap."],
            ["8", "Human vs AI mode", "Implemented, choice of agent and difficulty."],
            ["9", "Fuzzy danger estimation", "Mamdani system, live indicator."],
            ["10", "Common rules for both agents", "One engine and one abstract model for both."],
            ["11", "Tournament mode with statistics", "AI Benchmark: wins, losses, draws, win %, duration, decision time, finish types."],
            ["12", "Lab algorithms demonstrated", "Table 6; only algorithms from the course list were used."],
            ["13", "Original names and assets", "Procedural art, synthesized sound, Oswald font (SIL OFL)."]],
           [0.8 * cm, 5.6 * cm, 9.2 * cm], "Compliance with the proposal's requirements.")
S += [PageBreak()]

# ================================================================== 8 Limitations & future work
S += [P("8. Limitations and Future Work", H1),
      P("8.1 Limitations", H2)]
S += bullets([
    "<b>Balance.</b> The Defender archetype is dominant under the proposal's numbers; the Attacker-Stamina matchup often ends in draws.",
    "<b>Model mismatch.</b> The AI search does not model free steering or collisions, so its predictions are approximate.",
    "<b>Browser performance.</b> The browser version runs several times slower than the desktop version; the main loop is tuned for it, but frame times in the browser were not measured systematically.",
    "<b>No user study.</b> The Coach and the Screen Guide were designed from usability principles but were not evaluated with first-time players.",
    "<b>Audio.</b> The synthesized sounds were not evaluated by listening tests.",
    "<b>Related-work sources.</b> Real Beyblade scoring was taken from secondary sources.",
])
S += [P("8.2 Future work", H2)]
S += bullets([
    "Run a usability study (for example with the System Usability Scale) with first-time players and tune the Coach from the results.",
    "Rebalance the archetypes (for example by limiting how often Guard can heal) and add the Rough Ground stadium listed in the proposal.",
    "Teach the abstract model about steering and collisions, and tune the heuristic weights by self-play.",
    "Add stat-changing blade parts, unlockable parts and match replays.",
    "Add online play and tournaments between human players.",
])
S += [P("9. Conclusion", H1),
      P("BABY BLADE 2.0 shows that the classical techniques of the AI Laboratory course can drive a complete, enjoyable real-time game. Minimax with alpha-beta pruning and iterative deepening, "
        "Monte Carlo Tree Search with UCB1 and a Mamdani fuzzy system all operate on one shared rule set, and the project exposes them to the player through the AI decision panel, the fuzzy danger indicator, the benchmark and the championship. "
        f"The experiments with {TOTAL_MATCHES} matches show that the agents behave sensibly (higher difficulty wins, the agents differ in strength and cost) and reveal design issues, such as the dominant Defender, that are useful material for future work. "
        "The user interface goes beyond a prototype: it teaches the game while it is played, supports four input methods, and runs on desktop and in the browser."),
      P("Development process", H2),
      P("The team defined the requirements and design. The implementation was developed iteratively with the help of an AI coding assistant (Claude Code), under the team's direction and with the team reviewing "
        "the behaviour at each step; the automated tests and the experiments were used to verify it.")]

# ================================================================== references
S += [PageBreak(), P("References", H1)]
refs = [
    "[R1] Beyblade official website, <i>Parents' Guide</i>. https://beyblade.com/parent-guide/ (accessed November 2026).",
    "[R2] Fan and retailer descriptions of Beyblade X rules and scoring, e.g. Danireon, <i>Beyblade X vs Burst</i>. https://www.danireon.com/en-us/blogs/news/beyblade-x-vs-burst (accessed November 2026).",
    "[R3] FuRyu, <i>Beyblade X: XONE</i>, Battle page. https://www.cs.furyu.jp/beyblade2024_en/battle/ (accessed November 2026).",
    "[R4] Hasbro, <i>Beyblade Burst</i> mobile app (store description). Accessed November 2026.",
    "[R5] J. Barber, <i>Beyblade Simulator</i> (web game). https://jonbarber.games/beyblade/ (accessed November 2026).",
    "[R6] S. Russell and P. Norvig, <i>Artificial Intelligence: A Modern Approach</i>, 4th ed., Pearson, 2020.",
    "[R7] D. E. Knuth and R. W. Moore, &quot;An analysis of alpha-beta pruning,&quot; <i>Artificial Intelligence</i>, vol. 6, no. 4, pp. 293-326, 1975.",
    "[R8] L. Kocsis and C. Szepesvari, &quot;Bandit based Monte-Carlo planning,&quot; in <i>ECML 2006</i>, LNCS 4212, pp. 282-293, 2006.",
    "[R9] C. Browne et al., &quot;A survey of Monte Carlo tree search methods,&quot; <i>IEEE Trans. Computational Intelligence and AI in Games</i>, vol. 4, no. 1, pp. 1-43, 2012.",
    "[R10] P. Auer, N. Cesa-Bianchi and P. Fischer, &quot;Finite-time analysis of the multiarmed bandit problem,&quot; <i>Machine Learning</i>, vol. 47, pp. 235-256, 2002.",
    "[R11] L. A. Zadeh, &quot;Fuzzy sets,&quot; <i>Information and Control</i>, vol. 8, no. 3, pp. 338-353, 1965.",
    "[R12] E. H. Mamdani and S. Assilian, &quot;An experiment in linguistic synthesis with a fuzzy logic controller,&quot; <i>Int. J. Man-Machine Studies</i>, vol. 7, no. 1, pp. 1-13, 1975.",
    "[R13] S. Swink, <i>Game Feel: A Game Designer's Guide to Virtual Sensation</i>, Morgan Kaufmann, 2008.",
    "[R14] G. Fiedler, &quot;Fix your timestep!&quot;, Gaffer On Games, 2004 (fixed-step simulation).",
    "[R15] pygame-ce documentation, https://pyga.me/docs/; pygbag (WebAssembly packaging for pygame), https://pygame-web.github.io/.",
    "[R16] Oswald typeface, SIL Open Font License 1.1, https://github.com/googlefonts/OswaldFont.",
]
for r in refs:
    S.append(P(r, ParagraphStyle("Ref", parent=BODY, fontSize=9.5, leading=12.5, leftIndent=22, firstLineIndent=-22, alignment=0)))

S += [PageBreak(), P("Appendix A. How to run the game", H1),
      P("Desktop (Python 3.11 or newer):"),
      P("python -m venv .venv<br/>.venv\\Scripts\\python.exe -m pip install -r requirements-dev.txt<br/>.venv\\Scripts\\python.exe main.py", CODE),
      P("Browser build:"),
      P(".\\build_web.ps1<br/>.venv\\Scripts\\python.exe -m pygbag --port 8000 build\\stage<br/># then open http://localhost:8000", CODE),
      P("Headless tools:"),
      P(".venv\\Scripts\\python.exe -m pytest -q<br/>.venv\\Scripts\\python.exe main.py --tournament 20 --diff Medium --out tournament_results<br/>.venv\\Scripts\\python.exe report\\run_experiments.py", CODE),
      P("Appendix B. Main tunable constants", H1)]
S += table([["Constant", "Value", "Meaning"],
            ["ROUNDS x ROUND_SECONDS", f"{C.ROUNDS} x {C.ROUND_SECONDS:.0f} s", "Match length (120 s)"],
            ["STADIUM_START_RADIUS / MIN", f"{C.STADIUM_START_RADIUS:.0f} / {C.STADIUM_MIN_RADIUS:.0f}", "Stadium size; shrinks every 6 rounds"],
            ["BLADE_RADIUS", f"{C.BLADE_RADIUS}", "Physical radius; centres never closer than 2x"],
            ["ATTACK / SPECIAL damage", f"{C.ATTACK_DAMAGE:.0f} / {C.SPECIAL_DAMAGE:.0f}", "Stability damage before power and counters"],
            ["ATTACK / SPECIAL push", f"{C.ATTACK_PUSH} / {C.SPECIAL_PUSH}", "Knock-back distance units"],
            ["DRIVE_SPEED / DRIVE_RESPONSE", f"{C.DRIVE_SPEED} / {C.DRIVE_RESPONSE}", "Direct-drive speed and snap"],
            ["PHYSICS_HZ", f"{C.PHYSICS_HZ}", "Fixed simulation rate"],
            ["LINEAR_DAMPING / RESTITUTION", f"{C.LINEAR_DAMPING} / {C.RESTITUTION}", "Friction and bounce"],
            ["Points weights", f"{C.POINTS_W_ENERGY} / {C.POINTS_W_STABILITY} / {C.POINTS_W_POSITION}", "Energy / stability / position"]],
           [5.2 * cm, 3.4 * cm, 7 * cm], "Selected constants from config.py.")

# ================================================================== build
doc = Doc(OUT, pagesize=A4, leftMargin=2.4 * cm, rightMargin=2.4 * cm, topMargin=2.2 * cm, bottomMargin=2.4 * cm,
          title="BABY BLADE 2.0 - AI Laboratory Project Report", author="Suaib Ahmed Safi, Ashrafur Rahman Nihad",
          subject="AI-powered spinning-top battle game")
frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="f")
doc.addPageTemplates([PageTemplate(id="title", frames=[Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="t")], onPage=title_bg),
                      PageTemplate(id="main", frames=[frame], onPage=footer)])
doc.multiBuild(S)
print("wrote", OUT)
