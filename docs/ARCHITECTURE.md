# Architecture

```
main.py ── App (game/app.py): window, scene stack, 60 fps loop, async loop for the browser
            │
            ├─ scenes/title      live AI demo + main menu
            ├─ scenes/setup      Human vs AI / AI vs AI options
            ├─ scenes/battle     launch → fight → finish; HUD, controls, pause
            │     └─ ArenaView (game/arena_view.py): draws a Battle, turns its events into
            │        sparks, shockwaves, hit-stop, banners and sound
            ├─ scenes/results, championship, tournament (AI Benchmark), customize, howto, settings
            ├─ coach.py   plain-language tips for the Coach panel
            │
            └─ sim/battle.py  Battle: 120 Hz physics + 3 s rounds + rules + finishes
                  ├─ controllers: ai/agents.py (Ironclad, Cyclone, Human)
                  │     └─ search over sim/model.py (ACTIONS / RESULT / TERMINAL / UTILITY)
                  └─ sim/fuzzy.py (Mamdani danger), sim/actions.py, sim/blades.py, config.py
```

## Rules vs presentation
`sim/` never imports pygame. The battle exposes positions, resources and an `events` list;
the presentation reads them and never writes back (except the human's queued action and
steering input). This keeps the rules testable headless and identical for every mode.

## Real-time rounds
* Physics: bowl pull toward the centre, a steeper rim wall, orbit drift (spinning tops circle the
  bowl), damping, mass-weighted collisions with restitution, and a hard minimum distance
  between centres (tops never overlap).
* Every 3 s both controllers lock in an action. The action shapes movement for the round
  (dash, drift to centre, heavy guard stance, sideways dodge) and decides what happens on
  contact: at most one hit per attacker per round, both can land simultaneously.
* Costs are paid at round start; passive spin loss and Charge/Guard recovery flow continuously
  across the round so the gauges move smoothly. Totals per round equal the proposal's numbers.

## AI thinking without frame hitches
Agents are resumable generators. 1.2 s before each boundary the battle snapshots the state
and starts both searches; each frame advances them by a few milliseconds. At the boundary any
unfinished search is completed. Headless runs simply finish the search immediately.

## Rendering
Stage and stadium are pre-rendered once. Each frame: stage → bowl → light pass (LED rim,
under-glows, trails) → tops (cached rotation frames + spin-blur disc + fixed specular) → light
pass (auras, sparks, shockwaves) → floating text → camera (shake, zoom) → HUD. Light passes
use an opaque black layer the size of the stadium, added with BLEND_ADD.
