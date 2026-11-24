# BABY BLADE 2.0 — Game Design Document

Source of truth: the project proposal (*BLADE ARENA — AI-Powered Spinning-Top Battle Stadium*,
KUET AI Lab) and the presentation deck (*BABY BLADE*). Version 2.0 is a full rebuild. Version 1
resolved each round instantly and teleported the tops, so battles looked static. Version 2 keeps
every rule from the proposal but plays them out in **continuous real-time physics**, the way
real Beyblade games do.

## 1. Research summary (reverse-engineered from Beyblade games)

| Source | What we took |
|---|---|
| Beyblade X: XONE (FuRyu, 2024) | HUD gauges: a spin ("Survivor") gauge, a Burst gauge that worsens in stages, and an action gauge. Parts customization (Blade / Ratchet / Bit). Finish banners. |
| Beyblade X tabletop rules | Finish types (Spin, Burst, Knockout/Ring-out) shown as distinct, celebrated events. |
| Beyblade Burst app (Hasbro) | Launch moment ("Let it rip"), swipe/steer control during battle. |
| Top.io / Beyblade Simulator (jonbarber.games) | Top-down readable arena, rounded board, neon rim, name tags, motion trails. |
| Common game-feel practice | Hit-stop on impacts, screen shake, sparks, slow-motion finish, spin hum that drops in pitch as the top slows. |

## 2. Core loop

1. **Launch** — 3-2-1 countdown, then a power meter. Timing sets launch speed and angle (energy
   still starts at 100 as the proposal requires).
2. **Battle** — 40 rounds of 3 seconds each (= the proposal's 120-second limit). Physics runs
   continuously. At every round boundary both blades lock in one action **simultaneously**.
3. **Finish** — Ring-out, Burst, Spin-out, simultaneous-elimination Draw, or a Points decision
   after round 40. Each finish has its own banner, slow motion and sound.

The human picks the next action at any time during the round; it locks in at the boundary.
**Free movement.** Human and AI both steer their top continuously on an x/y plane whose
centre is (0, 0) (+x right, +y up; internal simulation coordinates that are not shown on screen). Steering is **direct drive**: the stick sets a target velocity (up to 7 u/s) that the top follows
within about 45 ms, so control feels instant. Dashes and knockback stay physical (they add to the
drive velocity), and you cannot steer yourself over the rim, so Ring-outs come from hits. The human steers with arrows/WASD, a stick or the touch joystick. AIs steer by the
action they chose: Attack/Special chase, Dodge slides sideways, Charge heads for the centre,
Guard holds, and every action retreats from the rim. Skill scales with difficulty.

## 3. Rules (from the proposal, exact values)

### Blades
| Archetype | Max stability | Energy loss / round | Power | Ability |
|---|---|---|---|---|
| Balanced | 100 | 3 | 1.00x | — |
| Attacker | 90 | 4 | 1.25x | higher attack power |
| Defender | 120 | 3 | 0.85x | Guard restores 10 stability |
| Stamina | 100 | 2 | 1.00x | Charge restores 25 energy |

Every blade starts with 100 energy and full stability. Energy reaching 0 → **Spin-out**.
Stability reaching 0 → **Burst**. Centre outside the stadium → **Ring-out**.

### Actions
| Action | Cost | Effect |
|---|---|---|
| Charge | 0 | +20 energy (Stamina +25), drifts toward the centre, takes extra damage (x1.25) |
| Attack | 8 | dashes at the opponent; one hit per round: 12 stability damage x power, push |
| Guard | 4 | +5 stability (Defender +10), heavy stance, halves normal damage and push, 3 recoil to a normal attacker |
| Dodge | 8 | sideways dash; evades Attack and Special; **fails** if it would end within 0.5 of the edge |
| Special Spin | 35 | needs a 3 s cooldown; big dash; 25 damage x power, bigger push; 10 self-recoil; Guard only reduces it to 70% |

Counter table: Attack beats Charge, Guard beats Attack, Special breaks through Guard, Dodge
avoids Attack and Special, Charge restores energy but is vulnerable. When both attack, both hits
land; nobody gets priority.

### Stadium
Initial radius 10, minimum 6, shrinks by 1 after every 6 rounds (rounds 6, 12, 18, 24). The
shrink animates smoothly and is announced one round ahead. Stadiums: **Classic Dish**
(standard), **Ice Rink** (x1.25 movement and push), **Steep Bowl** (stronger pull to centre).

### Points decision (after round 40)
`0.40 x energy share + 0.40 x stability share + 0.20 x centrality`; equal scores (within 1e-6)
are a draw.

## 4. AI (algorithms required by the AI Lab)

Both agents decide at every round boundary using the same **abstract round model**
(`sim/model.py`): `ACTIONS(s)`, `RESULT(s, a1, a2)`, `TERMINAL(s)`, `UTILITY(s)`.

* **Ironclad — Minimax.** MAX over its actions, MIN over the opponent's replies (simultaneous
  moves treated conservatively), alpha-beta pruning, depth-limited search with **iterative
  deepening** under a node/time budget. Easy: depth 1, Medium: 2, Hard: 3.
* **Cyclone — Monte Carlo Tree Search.** Selection with **UCB1**, expansion, simulation
  (heuristic-guided rollouts), backpropagation. Decoupled UCT for simultaneous moves. Easy: 60,
  Medium: 200, Hard: 500 iterations (time-capped).
* **Fuzzy danger — Mamdani FIS.** Inputs: distance to the boundary and remaining energy.
  Triangular fuzzification, 9 rules (AND = min, OR = max), centroid defuzzification. Output
  Low / Medium / High, shown live on the HUD and used by the heuristic.
* **Heuristic.** Energy, stability, position, Special availability and fuzzy danger, for both
  blades.

## 5. Modes
* **Human vs AI** — choose Ironclad or Cyclone and Easy / Medium / Hard.
* **AI vs AI** (mandatory) — start/pause, resume, restart, speed 1x/2x/4x, single step, swap sides.
* **Championship** — the player and seven AIs in a knockout bracket (quarter-final, semi-final, best-of-three final) on three stadiums.
* **AI Benchmark** — N headless AI matches; wins, losses, draws, win %, average duration, average
  decision time and finish types; export JSON/CSV on desktop.
* **Customize** — Blade (shape), Ratchet (claw count), Bit (tip) and colour are cosmetic; the
  archetype sets the rules and its real numbers are shown.

## 6. Presentation
Look follows the deck: dark navy stage, neon blue (P1) and red (P2), Oswald headings.
Stadium: rounded board, lit bowl floor, LED rim, danger zone outside the live boundary.
Tops: layered sprites rotated from a cache, fixed specular highlight, spin-blur that grows with
energy, glow, motion trails, wobble when stability is low. Teaching aids: Coach panel, counters chart, hover details, NOW/NEXT action for every blade, Screen Guide (H). Feedback: sparks, shockwaves,
hit-stop, screen shake, camera zoom, slow-motion finish, finish banners, synthesized audio
(spin hum pitched by energy, clashes, launch rip, burst, crowd).

## 7. Controls
| Input | Keyboard | Gamepad | Touch |
|---|---|---|---|
| Steer | WASD / arrows | left stick | left joystick |
| Actions | 1 Charge · 2 Attack · 3 Guard · 4 Special · Space Dodge | X, A, Y, RB, B | action buttons |
| Pause | P / Esc | Start | pause button |
| Launch | Space / click | A | tap |

## 8. Platforms
Desktop (Python 3.11+, pygame-ce) and browser (WebAssembly through pygbag).
