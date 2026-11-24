"""Every tunable number in one place.

Values marked (spec) come straight from the project proposal and must not change without
updating docs/GDD.md. The rest are presentation or physics-feel constants.
"""

from __future__ import annotations

# ---- Match timing (spec: 40 rounds, 120 seconds) -------------------------------------------
ROUNDS: int = 40
ROUND_SECONDS: float = 3.0  # 40 x 3 s = 120 s match limit (spec)

# ---- Stadium (spec) ---------------------------------------------------------------------------
STADIUM_START_RADIUS: float = 10.0
STADIUM_MIN_RADIUS: float = 6.0
SHRINK_EVERY_ROUNDS: int = 6
SHRINK_STEP: float = 1.0
SHRINK_ANIM_SECONDS: float = 1.2

# ---- Blades -------------------------------------------------------------------------------------
START_ENERGY: float = 100.0  # spec
BLADE_RADIUS: float = 1.2  # physical radius; tops never overlap closer than 2x this

# ---- Actions (spec) -----------------------------------------------------------------------------
COST_CHARGE: float = 0.0
COST_ATTACK: float = 8.0
COST_GUARD: float = 4.0
COST_DODGE: float = 8.0
COST_SPECIAL: float = 35.0
SPECIAL_COOLDOWN: float = 3.0
SPECIAL_SELF_RECOIL: float = 10.0
CHARGE_ENERGY: float = 20.0
GUARD_STABILITY: float = 5.0

# ---- Combat (proposal leaves numbers open; tuned) -----------------------------------------------
ATTACK_DAMAGE: float = 12.0
SPECIAL_DAMAGE: float = 25.0
ATTACK_PUSH: float = 1.6  # arena units of knockback
SPECIAL_PUSH: float = 2.8
CHARGING_DAMAGE_MULT: float = 1.25  # "a charging blade takes additional damage" (spec)
CHARGING_PUSH_MULT: float = 1.25
GUARD_NORMAL_MULT: float = 0.50
GUARD_SPECIAL_MULT: float = 0.70  # "guard is partially overcome" (spec)
GUARD_ATTACKER_RECOIL: float = 3.0
HIT_RANGE: float = 2.0 * BLADE_RADIUS + 0.2  # touching tops connect
DODGE_EDGE_MARGIN: float = 0.5  # dodge fails if it ends closer than this to the edge (spec)

# Abstract-model movement per round (used by the AI search model)
MOVE_ATTACK: float = 1.6
MOVE_SPECIAL: float = 2.0
MOVE_CHARGE: float = 1.0
MOVE_DODGE: float = 1.4

# ---- Points decision (spec: energy, stability, position) ---------------------------------------
POINTS_W_ENERGY: float = 0.40
POINTS_W_STABILITY: float = 0.40
POINTS_W_POSITION: float = 0.20
POINTS_EPSILON: float = 1e-6

# ---- Real-time physics feel ---------------------------------------------------------------------
PHYSICS_HZ: int = 120
LINEAR_DAMPING: float = 1.6  # 1/s; displacement of an impulse v0 is v0 / damping
BOWL_PULL: float = 0.55  # centre-ward acceleration per unit of distance (bowl slope)
STEEP_BOWL_PULL: float = 1.05
ORBIT_DRIFT: float = 0.9  # tangential drift that makes spinning tops circle the bowl
RESTITUTION: float = 0.75
DRIVE_SPEED: float = 7.0  # full-stick movement speed (units / s) for human and AI alike
DRIVE_RESPONSE: float = 22.0  # how fast movement follows the stick (1/s): ~45 ms to reach 63%
MAX_SPEED: float = 14.0
EDGE_WALL: float = 12.0  # extra centre-ward accel on the steep rim wall (outer 12% of the bowl)
EDGE_WALL_START: float = 0.88

DASH_ATTACK: float = 7.5  # units / s impulse at round start
DASH_SPECIAL: float = 10.5
DASH_DODGE: float = 8.0
CHARGE_PULL: float = 3.0
HOMING_SECONDS: float = 0.9
EVADE_SECONDS: float = 0.7
GUARD_MASS: float = 1.8

# Stadium modifiers
ICE_MOVE_MULT: float = 1.25
ICE_PUSH_MULT: float = 1.25
ICE_DAMPING_MULT: float = 0.6
