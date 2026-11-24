"""Viva guide: simple-words explanation of the logic behind Baby Blade (PDF)."""
import os
import re
import sys

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import BaseDocTemplate, CondPageBreak, Frame, KeepTogether, PageTemplate, Paragraph, Spacer, Table, TableStyle

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from babyblade.sim import fuzzy  # noqa: E402

OUT = os.path.join(HERE, "BabyBlade_Viva_Guide.pdf")
BODY = ParagraphStyle("b", fontName="Times-Roman", fontSize=11.5, leading=15.5, spaceAfter=5)
H1 = ParagraphStyle("h1", fontName="Times-Bold", fontSize=15, leading=19, spaceBefore=12, spaceAfter=5, keepWithNext=1)
H2 = ParagraphStyle("h2", fontName="Times-Bold", fontSize=12.5, leading=16, spaceBefore=7, spaceAfter=3, keepWithNext=1)
BUL = ParagraphStyle("u", parent=BODY, leftIndent=14, bulletIndent=2, spaceAfter=1.5)
CELL = ParagraphStyle("c", fontName="Times-Roman", fontSize=10.5, leading=12.8)
CELLB = ParagraphStyle("cb", parent=CELL, fontName="Times-Bold")
CAP = ParagraphStyle("cap", fontName="Times-Italic", fontSize=10, leading=12, spaceBefore=4, spaceAfter=2)
TITLE = ParagraphStyle("t", fontName="Times-Bold", fontSize=20, leading=25, alignment=TA_CENTER, spaceAfter=4)
SUB = ParagraphStyle("s", parent=BODY, alignment=TA_CENTER)
Q = ParagraphStyle("q", parent=BODY, fontName="Times-Bold", spaceAfter=1, keepWithNext=1)
S = []


def esc(t):
    return re.sub(r"&(?!(?:amp|lt|gt|#\d+);)", "&amp;", t)


def h1(t):
    S.append(Paragraph(esc(t), H1))


def h2(t):
    S.extend([CondPageBreak(3 * cm), Paragraph(esc(t), H2)])


def p(t):
    S.append(Paragraph(esc(t), BODY))


def bl(items):
    S.extend(Paragraph(esc(i), BUL, bulletText="-") for i in items)


def qa(q, a):
    S.append(KeepTogether([Paragraph(esc("Q. " + q), Q), Paragraph(esc(a), BODY)]))


def tb(cap, rows, widths):
    data = [[Paragraph(esc(str(c)), CELLB if i == 0 else CELL) for c in r] for i, r in enumerate(rows)]
    t = Table(data, colWidths=[w * cm for w in widths], repeatRows=1)
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.6, colors.black), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                           ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    S.extend([KeepTogether([Paragraph(esc(cap), CAP), t]), Spacer(1, 8)])


S += [Paragraph("BABY BLADE - Viva Guide", TITLE),
      Paragraph("The logic behind the game, in simple words. Use it to answer teacher questions.", SUB)]

h1("1. The game in 30 seconds")
p("Two spinning tops (blades) fight in a round stadium. A match has 40 rounds of 3 seconds. At the start of every round "
  "both players pick one action: Charge, Attack, Guard, Dodge or Special. Both actions start together. "
  "Then real-time physics plays the round. You win by pushing the rival out (ring-out), breaking its stability (burst), "
  "or making it run out of spin (spin-out). If nobody finishes, points decide. Every 6 rounds the stadium gets smaller.")
p("The AI part of the project has three pieces: a Minimax player (Ironclad), an MCTS player (Cyclone), and a fuzzy logic danger meter used by both.")

h1("2. Fuzzy logic")
h2("2.1 Which fuzzy logic? Mamdani")
p("We use a <b>Mamdani fuzzy inference system</b>. Its rules are written in plain words (IF edge is near AND energy is low THEN danger is high). "
  "Both the inputs and the output are fuzzy sets. The other common type, Sugeno, gives the output as a number or formula, which is harder to read. "
  "We chose Mamdani because it is easy to explain and it is the type taught in our AI lab.")
h2("2.2 What it does")
p("It answers one question: how much danger is this blade in right now? The answer is a number from 0 to 100, shown on screen as LOW, MEDIUM or HIGH.")
tb("Inputs and output.", [["", "Meaning", "Fuzzy sets"],
                          ["Input 1: edge margin", "0 = on the rim, 1 = at the center", "Near, Middle, Far"],
                          ["Input 2: spin energy", "0 to 100 left", "Low, Medium, High"],
                          ["Output: danger", "0 to 100", "Low, Medium, High"]], [4.0, 6.5, 5.5])
h2("2.3 The five Mamdani steps")
bl(["Fuzzification: turn the two numbers into degrees from 0 to 1 for each set. We use triangle and trapezoid shapes. A blade can be partly Near and partly Middle at the same time.",
    "Rule evaluation: the strength of each rule is the minimum of its two conditions (AND = min).",
    "Implication: cut (clip) the output set at that strength.",
    "Aggregation: combine all clipped output sets with maximum (OR = max).",
    "Defuzzification: take the centroid (center of area) of the combined shape. This is the final danger number."])
tb("The 9 rules (danger for each pair).", [["Edge margin", "Energy low", "Energy medium", "Energy high"],
                                           ["Near", "High", "High", "Medium"], ["Middle", "High", "Medium", "Low"], ["Far", "Medium", "Low", "Low"]], [3.4, 3.6, 3.6, 3.6])
p("The logic: near the rim with low energy is the worst. Far from the rim with high energy is the safest.")
ex = []
for m, e in ((0.4, 50), (0.1, 20), (0.9, 95)):
    d, _ = fuzzy.infer(m, e)
    ex.append([str(m), str(e), f"{d:.0f}", fuzzy.label(d)])
tb("Results from the real code.", [["Edge margin", "Spin energy", "Danger", "Shown as"]] + ex, [3.5, 3.5, 3.5, 3.5])
p("Example by hand: margin 0.4 is 100% Middle (the peak of its triangle). Energy 50 is 100% Medium. Only the rule Middle + Medium = Medium fires, with strength 1. "
  "The Medium triangle spans 25 to 75, so its centroid is 50. Danger = 50, MEDIUM.")
h2("2.4 Why we use it")
bl(["Danger is not a sharp yes/no. A blade slowly becomes more dangerous, and fuzzy logic gives a smooth number.",
    "The player sees it as a live meter, so it helps learning.",
    "Both AIs use it inside their score (20% weight), so they avoid risky positions and attack rivals that are in danger.",
    "For speed, we precompute a 41 x 41 table and use bilinear interpolation, so the AI can ask for danger thousands of times per decision."])

h1("3. The two search algorithms")
h2("3.1 Why two AIs")
p("The lab asks for adversarial search. We built two different kinds so that we can compare them: Minimax looks at everything but only a few moves ahead. "
  "MCTS samples many random futures. Both play the same game with the same rules.")
h2("3.2 Minimax with alpha-beta (Ironclad)")
p("Idea: pick the action whose worst case is the best. The AI assumes the rival will reply in the way that hurts most.")
bl(["The AI has 5 actions and the rival has 5 replies, so one round has 25 action pairs.",
    "For each of my actions, it looks at all 5 rival replies and keeps the worst result (MIN). Then it picks the action with the best worst result (MAX).",
    "Depth means how many rounds ahead it looks: Easy 1, Medium 2, Hard 3. At depth 3 there are up to 25 x 25 x 25 = 15,625 end positions.",
    "Alpha-beta pruning skips branches that cannot change the final choice. The answer stays the same, only faster.",
    "Iterative deepening searches depth 1, then 2, then 3. If time runs out, the last finished depth is used.",
    "At the end of the search a position is scored with the heuristic: 30% energy, 30% stability, 15% position, 5% special ready, 20% fuzzy danger."])
p("Both players move at the same time, so a normal turn-based game tree does not fit. Ironclad treats the rival as if it sees our choice first. This is careful but a bit pessimistic.")
h2("3.3 Monte Carlo Tree Search (Cyclone)")
p("Idea: do not look at everything. Play many quick random games and trust the actions that win most often.")
bl(["Selection: walk down the tree. At each step, pick an action with UCB1: average reward + 1.4 x square root of (ln total visits / action visits). The first part exploits good actions, the second part explores rarely tried ones.",
    "Expansion: add one new position to the tree.",
    "Simulation (rollout): play up to 4 rounds with a mix of random and greedy moves. Score the end with the heuristic.",
    "Backpropagation: send the result back up the path and update the counts and averages.",
    "After all iterations, play the most visited action. Easy uses 60 iterations, Medium 200, Hard 500.",
    "Because both players move together, each player keeps its own counts at every node (decoupled UCT)."])
tb("Ironclad compared with Cyclone.", [["", "Ironclad (Minimax)", "Cyclone (MCTS)"],
                                       ["Method", "Exact search, a few rounds deep", "Random sampling, many games"],
                                       ["Strong point", "Never misses a clear threat. Same input gives the same move.", "Can look further. Handles uncertainty. More iterations make it better."],
                                       ["Weak point", "Sees only 1 to 3 rounds. Assumes the worst reply.", "Noisy with few iterations: 200 games over 25 pairs is about 8 each."],
                                       ["Speed", "Fast, about 1 ms", "Slow, about 50 to 100 ms"],
                                       ["Style in our tests", "Charges and attacks, almost never dodges", "Mixes all actions, dodges about 1 round in 6"]], [3.0, 6.5, 6.5])
h2("3.4 Which algorithm for which blade?")
p("<b>The algorithm is not tied to a blade.</b> The algorithm belongs to the AI player. Any AI can use any blade. "
  "In Human vs AI you choose Ironclad or Cyclone, then you and the AI each choose a blade.")
tb("What is chosen by what.", [["Choice", "Decided by"],
                               ["Which algorithm plays (Minimax or MCTS)", "The AI you pick: Ironclad or Cyclone"],
                               ["How strong it is", "Difficulty: Easy, Medium, Hard"],
                               ["Numbers of the blade (health, power, abilities)", "The blade type: Balanced, Attacker, Defender, Stamina"],
                               ["Fuzzy danger", "Used by both AIs for every blade"],
                               ["Colors and shape of the blade", "Customize screen (looks only)"]], [8.0, 8.0])
p("Both AIs read the real numbers of the chosen blade in their round model. For example, a Defender AI knows Guard heals 10 stability, so Guard is worth more to it. "
  "A Stamina AI knows Charge gives 25 energy.")

h1("4. What each setting changes")
h2("4.1 Difficulty")
tb("Difficulty levels.", [["Level", "Ironclad depth", "Cyclone games", "Random move", "Steering skill"],
                          ["Easy", "1 round", "60", "15%", "60%"], ["Medium", "2 rounds", "200", "0%", "85%"], ["Hard", "3 rounds", "500", "0%", "100%"]], [2.4, 3.4, 3.4, 3.4, 3.4])
p("Harder means the AI thinks further or samples more, makes no random mistakes, and moves its blade more sharply. In our tests Hard beat Easy in 17 of 18 matches (Ironclad) and 16 of 18 (Cyclone).")
h2("4.2 Blade type")
tb("Blades and their trade-offs.", [["Blade", "Stability", "Spin loss / round", "Power", "Special trait", "Play style"],
                                    ["Balanced", "100", "3", "1.00", "None", "Simple, no weakness"],
                                    ["Attacker", "90", "4", "1.25", "Hits 25% harder", "Fast kills, but fragile and loses spin faster"],
                                    ["Defender", "120", "3", "0.85", "Guard heals 10", "Tough, wins by waiting and countering"],
                                    ["Stamina", "100", "2", "1.00", "Charge gives 25 energy", "Lasts long, wins on spin and points"]], [2.2, 2.0, 2.6, 1.6, 3.4, 4.2])
p("Logic: this is a trade-off design. Power costs stability or spin. Stability costs damage. "
  "Honest result: with the proposal's numbers the Defender is too strong (about 92% win rate against Balanced and Attacker). We kept the proposal's numbers and reported it.")
h2("4.3 Stadium")
tb("Stadiums.", [["Stadium", "Physics change", "Effect on play", "Ring-outs measured"],
                 ["Classic Dish", "Normal pull toward center, normal friction", "Balanced fights", "6%"],
                 ["Ice Rink", "Push and movement x1.25, friction x0.6", "Blades slide far, hits send rivals flying", "28%"],
                 ["Steep Bowl", "Pull toward center about 2x stronger (1.05 vs 0.55)", "Blades stay in the middle, constant clashes, the edge is safe", "0%"]], [2.6, 5.0, 5.4, 3.0])
p("All three stadiums shrink the same way: radius 10 at the start, minus 1 after rounds 6, 12, 18 and 24, ending at 6. "
  "A smaller stadium means less room, more contact and more ring-outs late in the match. The shrink is announced one round before.")
h2("4.4 Customize screen")
p("Shape, claws, tip and color only change how the blade looks. The blade type sets the rules and its real numbers are shown next to it. This keeps the game fair.")

h1("5. Physics and math")
bl(["<b>Fixed time step.</b> Physics runs 120 times per second. Each step moves positions by velocity x time. A fixed step gives the same results on every computer.",
    "<b>Bowl pull.</b> A force toward the center, like a ball rolling in a dish. It is why tops drift back to the middle. Steep Bowl uses a stronger pull.",
    "<b>Damping (friction).</b> Speed shrinks by a small fraction every step (1.6 per second). Ice multiplies this by 0.6, so it is slippery.",
    "<b>Rim wall.</b> From 0.88 of the radius outward, a strong push back works against leaving. Only a hard hit can get a blade over it.",
    "<b>Dashes.</b> Attack, Special and Dodge add a burst of speed at round start: 7.5, 10.5 and 8.0 units per second. Attack and Special also steer toward the rival for 0.9 seconds (homing).",
    "<b>Direct-drive control.</b> The stick sets a target velocity (up to 7 units per second). The blade follows it in about 45 ms. This is a first-order lag, so control feels instant but not jumpy. A blade cannot drive itself over the rim.",
    "<b>Collisions.</b> Blades have radius 1.2, so their centers stay at least 2.4 apart (no overlap). When they touch, velocities change with an elastic collision that depends on mass, with restitution 0.75 (some bounce energy is lost). Guard raises the mass to 1.8, so a guarding blade is hard to push.",
    "<b>Hits.</b> A hit counts when blades are within 2.6 and the attacker is attacking. Each attacker hits once per round. Damage = base (12 or 25) x blade power x modifier. Modifiers: target Charging x1.25, target Guard x0.5 (Attack) or x0.7 (Special). Dodge makes the hit miss.",
    "<b>Dodge rule.</b> A successful Dodge makes attacks miss for 0.7 seconds. It fails if the blade would end within 0.5 of the rim.",
    "<b>Spin and stability.</b> Energy and stability change a little each step, so the bars move smoothly. The totals per round equal the proposal's numbers (costs, losses and recoveries).",
    "<b>Points decision.</b> Score = 0.4 x energy share + 0.4 x stability share + 0.2 x closeness to center. The higher score wins.",
    "<b>Seeing the spin.</b> At full speed a blade turns about 55 degrees per frame, which looks still. We draw blurred copies and a gold pointer so the spin is visible."])
h2("5.1 Why the AI uses a simple model")
p("Running full physics inside a search would be far too slow. The AI uses an abstract round model with the same costs, damages and recoveries as the game: "
  "ACTIONS (legal moves), RESULT (what one round does), TERMINAL (is the match over) and UTILITY (win, loss or draw). "
  "The real physics then plays out the chosen action. The AI also chooses how to steer: toward the rival for Attack and Special, sideways for Dodge, to the center for Charge, and away from the rim at all times.")
h2("5.2 Thinking without freezing")
p("Each AI search is a generator that runs a few milliseconds per frame, starting 1.2 seconds before the round ends. This is needed because a browser has no threads.")

h1("6. What we observed in play")
bl(["Ironclad beat Cyclone at Medium (19 of 24) and Hard (19 of 24). Cyclone was a little better at Easy (14 vs 9).",
    "Cyclone loses mostly because of random noise from few games, and because the Attacker blade is weak against the Defender. With equal blades Ironclad still wins more.",
    "Ice Rink has the most ring-outs. Steep Bowl has none. Classic is in between.",
    "Defender is the strongest blade. Attacker is the weakest in a long match.",
    "Ironclad charges and attacks a lot. Cyclone dodges and guards more. A player can beat Ironclad with Guard after it charges, and Cyclone by not chasing it."])

h1("7. Likely teacher questions")
qa("Why did you use Mamdani and not Sugeno?", "Mamdani rules are readable sentences and the output is a fuzzy set, so it is easy to explain and to show on screen. It is also the type from our lab.")
qa("What is defuzzification and which method did you use?", "It turns the combined fuzzy output back into one number. We used the centroid (center of area) over 0 to 100.")
qa("What is the use of fuzzy logic in the game?", "It makes the live danger meter and it adds 20% of both AIs' position score, so both AIs avoid danger and attack weak rivals.")
qa("Why Minimax if both players move together?", "A round has simultaneous moves. Minimax handles this by taking the worst case over the rival's 5 replies for each of our actions. It is safe but pessimistic.")
qa("What does alpha-beta pruning do?", "It skips branches that cannot change the final choice. The result is the same as plain Minimax, but with less work.")
qa("What is UCB1 and why is it used?", "It is the rule that balances trying good actions and trying rare ones: average reward + C x sqrt(ln N / n), with C = 1.4. Without it MCTS would either repeat one action or only explore.")
qa("Why does MCTS lose to Minimax here?", "The search space is small (5 x 5 actions), so Minimax can check everything exactly. MCTS spends its games on random rollouts and its answer is noisy. MCTS gains more in a much bigger game.")
qa("Does each blade have its own algorithm?", "No. The algorithm belongs to the AI player. Any blade can be played by any AI. The blade only changes the numbers the AI uses.")
qa("What does difficulty change?", "Search depth (1, 2, 3) for Ironclad, number of games (60, 200, 500) for Cyclone, random mistakes on Easy, and how well the blade is steered.")
qa("Why does the stadium shrink?", "It forces action. Without it, two careful players could stall until points decide. A smaller stadium means more contact and more ring-outs.")
qa("How do you stop blades from overlapping?", "Each blade has radius 1.2 and the centers are kept at least 2.4 apart. If they get closer, they are pushed apart.")
qa("Is the game balanced?", "Mostly. The Defender is too strong with the proposal's numbers. We did not change them, because the proposal fixed them, and we report it in the results.")
qa("Why real-time physics and not just numbers per round?", "Our first version resolved each round instantly and looked static. Real-time physics keeps the same rules but shows the fight, and it allows free movement for humans and AIs.")
qa("How do you test it?", "67 automated tests (rules, fuzzy, AIs, battle, game screens, championship) and 522 matches in experiments with the real physics and the real AIs.")


def foot(c, d):
    c.saveState()
    c.setFont("Times-Roman", 10)
    c.drawCentredString(A4[0] / 2, 1.3 * cm, str(d.page))
    c.restoreState()


doc = BaseDocTemplate(OUT, pagesize=A4, leftMargin=2.3 * cm, rightMargin=2.3 * cm, topMargin=2 * cm, bottomMargin=2 * cm, title="Baby Blade - Viva Guide")
doc.addPageTemplates([PageTemplate(id="m", frames=[Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height)], onPage=foot)])
doc.build(S)
print("wrote", OUT)
