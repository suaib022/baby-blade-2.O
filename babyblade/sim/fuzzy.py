"""Mamdani fuzzy inference for blade danger (AI Lab 6).

Inputs:
  * edge margin: (radius - distance from centre) / radius, 0 = on the rim, 1 = at the centre
  * energy: remaining spin energy, 0..100
Output:
  * danger 0..100, labelled LOW / MEDIUM / HIGH

Steps: triangular/trapezoidal fuzzification, rule evaluation with AND = min, aggregation of
rules that share an output set with OR = max, clipping (Mamdani implication), and centroid
defuzzification over a sampled universe. A precomputed grid makes the value cheap enough for
the AI search, which queries it thousands of times per decision.
"""

from __future__ import annotations

from typing import Dict, List, Tuple


def tri(x: float, a: float, b: float, c: float) -> float:
    """Triangular membership with feet a, c and peak b (a == b or b == c gives a shoulder)."""
    if x < a or x > c:
        return 0.0
    if x == b:
        return 1.0
    if x < b:
        return (x - a) / (b - a) if b > a else 1.0
    return (c - x) / (c - b) if c > b else 1.0


def trap(x: float, a: float, b: float, c: float, d: float) -> float:
    if x < a or x > d:
        return 0.0
    if b <= x <= c:
        return 1.0
    if x < b:
        return (x - a) / (b - a) if b > a else 1.0
    return (d - x) / (d - c) if d > c else 1.0


# Input fuzzy sets
def margin_sets(m: float) -> Dict[str, float]:
    return {
        "near": trap(m, -1.0, -1.0, 0.08, 0.35),
        "mid": tri(m, 0.15, 0.40, 0.65),
        "far": trap(m, 0.45, 0.75, 2.0, 2.0),
    }


def energy_sets(e: float) -> Dict[str, float]:
    return {
        "low": trap(e, -1.0, -1.0, 10.0, 40.0),
        "mid": tri(e, 20.0, 50.0, 80.0),
        "high": trap(e, 60.0, 90.0, 101.0, 101.0),
    }


# Output fuzzy sets over the danger universe 0..100
def danger_set(name: str, x: float) -> float:
    if name == "low":
        return trap(x, -1.0, -1.0, 15.0, 40.0)
    if name == "medium":
        return tri(x, 25.0, 50.0, 75.0)
    return trap(x, 60.0, 85.0, 101.0, 101.0)


# Rule base: (margin set, energy set) -> danger set. Rules with the same consequent are
# combined with OR = max during aggregation.
RULES: List[Tuple[str, str, str]] = [
    ("near", "low", "high"),
    ("near", "mid", "high"),
    ("near", "high", "medium"),
    ("mid", "low", "high"),
    ("mid", "mid", "medium"),
    ("mid", "high", "low"),
    ("far", "low", "medium"),
    ("far", "mid", "low"),
    ("far", "high", "low"),
]

_UNIVERSE = [float(x) for x in range(0, 101)]


def infer(margin: float, energy: float) -> Tuple[float, Dict[str, float]]:
    """Full Mamdani inference. Returns (crisp danger 0..100, firing strength per output set)."""
    ms = margin_sets(margin)
    es = energy_sets(energy)
    strength = {"low": 0.0, "medium": 0.0, "high": 0.0}
    for m_name, e_name, out in RULES:
        fire = min(ms[m_name], es[e_name])  # AND = min
        strength[out] = max(strength[out], fire)  # OR = max over rules with the same output
    num = 0.0
    den = 0.0
    for x in _UNIVERSE:
        mu = max(min(strength[name], danger_set(name, x)) for name in strength)  # clip + max
        num += x * mu
        den += mu
    crisp = num / den if den > 1e-12 else 50.0  # centroid
    return crisp, strength


def label(danger: float) -> str:
    if danger < 34.0:
        return "LOW"
    if danger < 67.0:
        return "MEDIUM"
    return "HIGH"


# ---- Fast lookup grid for the AI search ---------------------------------------------------------
_GM = 41  # margin samples over [0, 1]
_GE = 41  # energy samples over [0, 100]
_GRID: List[List[float]] = []


def _grid() -> List[List[float]]:
    if not _GRID:  # built on first use, not at import time
        _GRID.extend([infer(i / (_GM - 1), 100.0 * j / (_GE - 1))[0] for j in range(_GE)] for i in range(_GM))
    return _GRID


def danger_fast(margin: float, energy: float) -> float:
    """Bilinear lookup in the precomputed inference grid (within ~1 point of infer())."""
    m = min(1.0, max(0.0, margin)) * (_GM - 1)
    e = min(100.0, max(0.0, energy)) / 100.0 * (_GE - 1)
    i0, j0 = int(m), int(e)
    i1, j1 = min(i0 + 1, _GM - 1), min(j0 + 1, _GE - 1)
    fm, fe = m - i0, e - j0
    g = _grid()
    top = g[i0][j0] * (1 - fe) + g[i0][j1] * fe
    bot = g[i1][j0] * (1 - fe) + g[i1][j1] * fe
    return top * (1 - fm) + bot * fm


def blade_danger(x: float, y: float, radius: float, energy: float) -> float:
    dist = (x * x + y * y) ** 0.5
    margin = (radius - dist) / radius if radius > 0 else 0.0
    return danger_fast(margin, energy)
