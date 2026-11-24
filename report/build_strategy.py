"""Two-page cheat sheet: how choices change the match, how the AI decides, how to beat it."""

import os

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "BabyBlade2_Strategy_Guide.pdf")
NAVY, BLUE, RED, GREY = colors.HexColor("#12306b"), colors.HexColor("#2a6fdb"), colors.HexColor("#d6382c"), colors.HexColor("#555555")

TXT = ParagraphStyle("t", fontName="Helvetica", fontSize=8.3, leading=10.2)
TXTB = ParagraphStyle("tb", parent=TXT, fontName="Helvetica-Bold")
HEAD = ParagraphStyle("h", fontName="Helvetica-Bold", fontSize=8.3, leading=10, textColor=colors.white)
H1 = ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=11.5, leading=14, textColor=NAVY, spaceBefore=7, spaceAfter=3)
TITLE = ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=17, leading=20, textColor=NAVY)
SUBT = ParagraphStyle("sub", fontName="Helvetica", fontSize=8.8, leading=11, textColor=GREY, spaceAfter=3)
BUL = ParagraphStyle("b", parent=TXT, leftIndent=9, bulletIndent=0, spaceAfter=1.5)
NOTE = ParagraphStyle("n", parent=TXT, fontSize=7.3, leading=9, textColor=GREY)


def p(t, st=TXT):
    return Paragraph(t, st)


def tbl(rows, widths, head_col=BLUE):
    data = [[p(c, HEAD if i == 0 else (TXTB if j == 0 else TXT)) for j, c in enumerate(r)] for i, r in enumerate(rows)]
    t = Table(data, colWidths=widths, repeatRows=1)
    st = [("BACKGROUND", (0, 0), (-1, 0), head_col), ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#b4bdd0")),
          ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
          ("LEFTPADDING", (0, 0), (-1, -1), 3.5), ("RIGHTPADDING", (0, 0), (-1, -1), 3.5)]
    for i in range(2, len(rows), 2):
        st.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#f2f5fb")))
    t.setStyle(TableStyle(st))
    return t


def footer(c, d):
    c.saveState()
    c.setFont("Helvetica", 7.5)
    c.setFillColor(GREY)
    c.drawString(1.6 * cm, 0.9 * cm, "BABY BLADE 2.0 - choice and strategy cheat sheet")
    c.drawRightString(A4[0] - 1.6 * cm, 0.9 * cm, f"{d.page} / 2")
    c.restoreState()


W = A4[0] - 3.2 * cm
S = [p("BABY BLADE 2.0 - Choices and How to Beat the AI", TITLE),
     p("Short guide. Numbers come from the game rules and from 400+ headless matches (12-24 per case, so treat small gaps as hints).", SUBT)]

# ------------------------------------------------------------------ 1. choices
S += [p("1. What each choice changes", H1)]
S.append(tbl([
    ["Choice", "What it does", "Consequence (Human vs AI and AI vs AI)"],
    ["Blade: Balanced", "100 stability, spin loss 3, power 1.0", "No weakness, no edge. About 50% against Attacker, 54% against Stamina, loses to Defender."],
    ["Blade: Attacker", "90 stability, spin loss 4, power 1.25", "Hits hardest (Attack 15) but bursts and spins out fastest. Beats Stamina (71%), ties Balanced, loses to Defender (8%)."],
    ["Blade: Defender", "120 stability, power 0.85, Guard heals 10", "Strongest overall: about 92% against Balanced and Attacker, 83% against Stamina. Fights are long; often decided on points."],
    ["Blade: Stamina", "Spin loss 2, Charge gives 25", "Hardest to spin out, but weakest in duels (17-46%). Best on the Steep Bowl, where matches are decided by spin."],
    ["Difficulty: Easy", "Ironclad searches 1 round and plays a random move 15% of the time; Cyclone 60 simulations; steering at 60% speed", "Beatable with the basic counters. Hard beats Easy in 89-94% of matches."],
    ["Difficulty: Medium", "Ironclad depth 2; Cyclone 200 simulations; steering 85%", "Solid. Ironclad takes about 4 ms per decision, Cyclone about 50 ms."],
    ["Difficulty: Hard", "Ironclad depth 3; Cyclone 500 simulations; steering 100%", "Plays the counters accurately and moves as fast as you. Cyclone takes about 100 ms per decision (slower in the browser)."],
    ["Stadium: Classic Dish", "Standard physics", "Mostly Burst and Spin-out finishes; Ring-out is rare (about 6%)."],
    ["Stadium: Ice Rink", "Movement and pushes x1.25, low friction", "Most Ring-outs (about 28%). Positioning matters more; Ironclad turns defensive (Guard 25%)."],
    ["Stadium: Steep Bowl", "Strong pull to the centre", "Almost no Ring-outs (0% measured); matches end by Spin-out or Burst, so spin management wins."],
    ["Mode: Human vs AI", "You pick one action per round and steer freely", "The AI reads the situation every 3 s and steers by its action. You can out-think it with the counters below."],
    ["Mode: AI vs AI", "Both sides are agents", "Ironclad beats Cyclone at Medium and Hard (79%); Cyclone leads at Easy (58% to 38%). The blade matters as much as the agent."],
], [3.1 * cm, 5.6 * cm, W - 8.7 * cm]))

# ------------------------------------------------------------------ 2. AI logic
S += [p("2. How the AI decides", H1)]
for t in [
    "<b>Ironclad (Minimax):</b> looks ahead 1-3 rounds and assumes your best reply, scoring spin, stability, position, Special readiness and fuzzy danger. "
    "<b>Measured habits:</b> Charge 38-44% and Attack 33-45% of rounds, Guard 12-21%, and it <b>almost never Dodges (0-6%) or uses Special (1-4%)</b>.",
    "<b>Cyclone (MCTS):</b> simulates many random futures and picks the most visited action. <b>Measured habits:</b> Charge about 31%, Attack 22-27%, Guard 19-23%, "
    "<b>Dodge 15-17%</b> and Special 5-9%, so it is harder to hit and uses its big move more often.",
    "Both lock one action every 3 seconds, then steer: Attack and Special chase you, Dodge slides sideways, Charge heads to the centre, Guard holds, and every action retreats from the rim.",
]:
    S.append(Paragraph(t, BUL, bulletText="•"))

# ------------------------------------------------------------------ 3. beat the AI
S += [p("3. How to beat the AI", H1), p("<b>Read what the AI is doing now</b> (NOW on its card, and the Coach panel) and answer with the counter:", TXT), Spacer(1, 2)]
S.append(tbl([
    ["If the AI is...", "Your best answer", "Why"],
    ["Charging", "Attack", "Charging takes x1.25 damage and push; this is the AI's most common move."],
    ["Attacking", "Guard, or Dodge and steer away", "Guard halves the hit and the attacker takes 3 recoil. Dodge makes it miss. Hits need contact, so running away also works against Easy/Medium (they steer slower than you)."],
    ["Guarding", "Special (70% gets through) or Charge", "Attack does only half and hurts you 3. Do not waste spin on Attack."],
    ["Dodging", "Guard or Charge, do not attack", "Attack and Special both miss a successful Dodge (it fails near the rim)."],
    ["Using Special", "Dodge", "Guard still lets 70% through."],
], [2.8 * cm, 4.7 * cm, W - 7.5 * cm], head_col=RED))
S.append(Spacer(1, 4))
S.append(tbl([
    ["AI blade", "Plan against it"],
    ["Defender", "Long, defensive. Do not Attack into Guard. Use Special when it guards, keep the centre and a spin lead to win on points, and push it out on the Ice Rink."],
    ["Attacker", "Fragile (90 stability) and burns spin. Guard or Dodge its hits, let it spin itself down, and hit it when it Charges. About 8 clean Attacks burst it."],
    ["Stamina", "Hard to spin out, so go for Burst and Ring-out. Attack whenever it Charges (it charges a lot); save Special for when it guards."],
    ["Balanced", "No weakness. Win with the counter table and by keeping more spin than it."],
], [2.8 * cm, W - 2.8 * cm], head_col=BLUE))
S.append(Spacer(1, 4))
S.append(tbl([
    ["AI agent", "Plan against it"],
    ["Ironclad", "Aggressive and predictable: it rarely Dodges, so your Attack lands whenever it Charges, and its attacks are easy to Guard. Special is rarely used against you, so Guard is safe."],
    ["Cyclone", "Mixed and evasive: about one round in six it Dodges, so do not chase with Attack. Play Guard and Charge, punish its Charge, and Dodge when it uses Special."],
], [2.8 * cm, W - 2.8 * cm], head_col=BLUE))
S.append(Spacer(1, 4))
S.append(tbl([
    ["Stadium", "Plan"],
    ["Classic Dish", "Standard. Win by spin and stability; keep to the centre as the arena shrinks (radius 10 to 6)."],
    ["Ice Rink", "Pushes are 25% stronger: stay central, Guard near the rim (halves the push) and use Special near the rim to knock the AI out."],
    ["Steep Bowl", "Everyone is pulled to the middle, so Ring-outs almost never happen. Conserve spin (Charge when safe) and win by Spin-out or Burst."],
], [2.8 * cm, W - 2.8 * cm], head_col=BLUE))

S += [p("Always", H1)]
for t in ["Keep spin above 35 if you want Special, and above 12 to stay safe; Charge when the rival is far.",
          "Watch DANGER: HIGH means you are close to the rim with low spin, so steer to the centre. The arena shrinks after rounds 6, 12, 18 and 24.",
          "Press H for the Screen Guide and hover an action to read its details."]:
    S.append(Paragraph(t, BUL, bulletText="•"))
S.append(Spacer(1, 3))
S.append(p("Method: AI behaviour measured by headless matches (report/measure_ai_behaviour.py, 168 matches, 6 per case); blade and stadium results from report/run_experiments.py. "
           "Results are against AI opponents, so a human may do better by using the counters.", NOTE))

doc = SimpleDocTemplate(OUT, pagesize=A4, leftMargin=1.6 * cm, rightMargin=1.6 * cm, topMargin=1.3 * cm, bottomMargin=1.5 * cm,
                        title="BABY BLADE 2.0 - Choices and How to Beat the AI", author="Suaib Ahmed Safi, Ashrafur Rahman Nihad")
doc.build(S, onFirstPage=footer, onLaterPages=footer)
print("wrote", OUT)
