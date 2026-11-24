# BABY BLADE 2.0

An AI-powered spinning-top battle game (KUET AI Lab project), rebuilt from scratch. Two blades
fight in a shrinking stadium with **real-time physics**. Every rule from the proposal is kept:
5 simultaneous actions, Energy/Stability, Ring-out / Burst / Spin-out / Draw / Points, a
Minimax AI (Ironclad), an MCTS AI (Cyclone), and a Mamdani fuzzy danger meter.

Runs on desktop (Python + pygame-ce) and in the browser (WebAssembly via pygbag).

## Play

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe main.py
```

Browser build:

```powershell
.\build_web.ps1
.venv\Scripts\python.exe -m pygbag --port 8000 build\stage
```

Then open http://localhost:8000 (the first load downloads the Python runtime, so it needs
internet). Upload `build\web` to a static host such as itch.io to share it.

## Controls

| | Keyboard | Gamepad | Touch / mouse |
|---|---|---|---|
| Actions | 1 Charge · 2 Attack · 3 Guard · 4 Special · Space Dodge | X · A · Y · RB · B | action buttons |
| Steer (free x/y movement) | WASD / arrows | left stick / D-pad | on-screen joystick |
| Launch | Space in the green zone (before the fight) | A | tap |
| Pause | P / Esc | Start | pause button |
| Screen guide (explains every number on screen) | H / F1 | | `? GUIDE` button |
| Mute | M | | |

Your chosen action locks in when the gold round bar fills (every 3 seconds). AI vs AI has
play/pause, single-step, 1x/2x/4x speed, swap sides and restart.

## Modes
* **Play** — Human vs AI. Choose Ironclad or Cyclone and Easy / Medium / Hard. A Coach panel explains what is happening and what to do; hover an action for details.
* **AI vs AI** — the mandatory mode: watch the two agents duel with their decisions on screen.
* **Championship** — you and seven AIs in an 8-player knockout bracket (quarter-final, semi-final,
  best-of-three final) played on three different stadiums. AI-only matches are simulated; your
  matches are real battles. Titles and records are saved.
* **AI Benchmark** — run 5 to 50 matches; wins, draws, win %, average duration, average decision
  time and finish types; export JSON/CSV (desktop).
* **Customize** — ring colour, blade shape, ratchet claws, weight disk and bit (cosmetic), plus the
  archetype that sets the rules.

## Headless tools

```powershell
.venv\Scripts\python.exe main.py --tournament 20 --diff Medium --out tournament_results
.venv\Scripts\python.exe main.py --smoke 120 --shot shot.png
.venv\Scripts\python.exe -m pytest -q
```

## How it is built

| Folder | What lives there |
|---|---|
| `babyblade/sim` | Rules and physics, no graphics: blades, actions, real-time battle, fuzzy logic, the abstract round model the AI searches |
| `babyblade/ai` | Ironclad (Minimax, alpha-beta, iterative deepening) and Cyclone (MCTS, UCB1) |
| `babyblade/game` | Rendering, effects, audio, input, UI, scenes |
| `babyblade/tournament.py` | Headless benchmark |
| `docs/GDD.md` | Design document: proposal rules mapped to the real-time game, research notes |
| `docs/ARCHITECTURE.md` | Module map and frame loop |

All art and sound are generated in code; the only bundled asset is the Oswald font (SIL Open
Font License, `babyblade/assets/fonts/OFL.txt`).
