"""Tournament mode: repeated AI vs AI matches with the statistics the proposal asks for.

Wins, losses, draws, win %, average match duration, average decision time and finish types.
Sides alternate every match so neither agent keeps the starting position. Runs headless; the
UI calls `step()` in small slices, the CLI runs it to the end.
"""

from __future__ import annotations

import csv
import json
import os
from collections import Counter
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional

from babyblade.ai.agents import make_agent
from babyblade.sim.battle import Battle
from babyblade.sim.blades import BladeType, StadiumType


@dataclass
class TournamentConfig:
    agent_a: str = "Ironclad"
    agent_b: str = "Cyclone"
    diff_a: str = "Medium"
    diff_b: str = "Medium"
    blade_a: str = BladeType.BALANCED.value
    blade_b: str = BladeType.BALANCED.value
    stadium: str = StadiumType.CLASSIC.value
    matches: int = 10
    seed: int = 1000


@dataclass
class MatchRecord:
    index: int
    a_side: int
    winner: str  # "A", "B" or "DRAW"
    finish: str
    rounds: int
    seconds: float
    a_hits: int
    b_hits: int
    a_think_ms: float
    b_think_ms: float


@dataclass
class Summary:
    config: TournamentConfig
    records: List[MatchRecord] = field(default_factory=list)

    @property
    def played(self) -> int:
        return len(self.records)

    def wins(self, who: str) -> int:
        return sum(1 for r in self.records if r.winner == who)

    @property
    def draws(self) -> int:
        return self.wins("DRAW")

    def win_rate(self, who: str) -> float:
        return self.wins(who) / self.played if self.played else 0.0

    def finishes(self) -> Dict[str, int]:
        c = Counter(r.finish for r in self.records)
        return {k: c.get(k, 0) for k in ("RING_OUT", "BURST", "SPIN_OUT", "POINTS", "DRAW")}

    @property
    def avg_seconds(self) -> float:
        return sum(r.seconds for r in self.records) / self.played if self.played else 0.0

    @property
    def avg_rounds(self) -> float:
        return sum(r.rounds for r in self.records) / self.played if self.played else 0.0

    def avg_think_ms(self, who: str) -> float:
        if not self.played:
            return 0.0
        vals = [r.a_think_ms if who == "A" else r.b_think_ms for r in self.records]
        return sum(vals) / len(vals)

    def to_dict(self) -> dict:
        return {
            "config": asdict(self.config),
            "played": self.played,
            "wins_a": self.wins("A"), "wins_b": self.wins("B"), "draws": self.draws,
            "win_rate_a": self.win_rate("A"), "win_rate_b": self.win_rate("B"),
            "finishes": self.finishes(),
            "avg_seconds": self.avg_seconds, "avg_rounds": self.avg_rounds,
            "avg_decision_ms_a": self.avg_think_ms("A"), "avg_decision_ms_b": self.avg_think_ms("B"),
            "records": [asdict(r) for r in self.records],
        }

    def export(self, folder: str) -> str:
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, "summary.json"), "w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, indent=2)
        with open(os.path.join(folder, "matches.csv"), "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(asdict(self.records[0]).keys()) if self.records else ["index"])
            w.writeheader()
            for r in self.records:
                w.writerow(asdict(r))
        return folder


class Tournament:
    def __init__(self, config: TournamentConfig) -> None:
        self.config = config
        self.summary = Summary(config)
        self.current: Optional[Battle] = None
        self._a_side = 1
        self.cancelled = False

    @property
    def done(self) -> bool:
        return self.cancelled or self.summary.played >= self.config.matches

    def _start_match(self) -> None:
        cfg = self.config
        i = self.summary.played
        self._a_side = 1 if i % 2 == 0 else 2  # alternate starting sides
        seed = cfg.seed + i * 7
        a = make_agent(cfg.agent_a, cfg.diff_a, seed)
        b = make_agent(cfg.agent_b, cfg.diff_b, seed + 3)
        ka, kb = BladeType(cfg.blade_a), BladeType(cfg.blade_b)
        if self._a_side == 1:
            self.current = Battle(ka, kb, StadiumType(cfg.stadium), controllers=(a, b), seed=seed)
        else:
            self.current = Battle(kb, ka, StadiumType(cfg.stadium), controllers=(b, a), seed=seed)

    def step(self, game_seconds: float = 6.0) -> None:
        """Advance the running match by `game_seconds` (or start/finish a match)."""
        if self.done:
            return
        if self.current is None:
            self._start_match()
        b = self.current
        assert b is not None
        step = 1.0 / 120
        n = int(game_seconds / step)
        for _ in range(n):
            b.update(step, think_budget=10.0)
            if b.over:
                break
        b.events.clear()
        if b.over:
            self._record(b)
            self.current = None

    def run(self) -> Summary:
        while not self.done:
            self.step(400.0)
        return self.summary

    def _record(self, b: Battle) -> None:
        a_top = b.t1 if self._a_side == 1 else b.t2
        b_top = b.t2 if self._a_side == 1 else b.t1
        if b.winner == 0:
            winner = "DRAW"
        else:
            winner = "A" if b.winner == self._a_side else "B"
        ms = lambda t: (t.stats.think_seconds / max(1, t.stats.decisions)) * 1000.0
        self.summary.records.append(MatchRecord(
            index=self.summary.played + 1, a_side=self._a_side, winner=winner,
            finish="DRAW" if b.finish == "DRAW" else (b.finish or "POINTS"), rounds=b.round, seconds=round(b.time, 2),
            a_hits=a_top.stats.hits, b_hits=b_top.stats.hits, a_think_ms=round(ms(a_top), 3), b_think_ms=round(ms(b_top), 3)))
