"""Championship: a single-elimination bracket where the player faces the AI agents.

Eight entrants (the player plus seven AIs) play quarter-finals, semi-finals and a final.
Quarter-finals and semi-finals are one battle each; the final is best of three. AI-versus-AI
matches are simulated headless with the same rules the player's battles use. A drawn battle is
simply replayed. The module has no graphics so it can be tested directly.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import List, Optional

from babyblade.ai.agents import make_agent
from babyblade.sim.battle import Battle
from babyblade.sim.blades import BladeType, StadiumType

ROUND_NAMES = ["Quarter-final", "Semi-final", "Final"]
ROUND_BEST_OF = [1, 1, 3]
ROUND_STADIUMS = [StadiumType.CLASSIC, StadiumType.ICE, StadiumType.STEEP]


@dataclass
class Entrant:
    name: str
    agent: str  # "Ironclad", "Cyclone" or "human"
    difficulty: str
    archetype: BladeType
    is_player: bool = False

    @property
    def label(self) -> str:
        return "YOU" if self.is_player else f"{self.agent} {self.difficulty}"


@dataclass
class Match:
    round: int
    index: int
    a: Optional[Entrant] = None
    b: Optional[Entrant] = None
    best_of: int = 1
    wins_a: int = 0
    wins_b: int = 0
    winner: Optional[Entrant] = None
    battles: List[str] = field(default_factory=list)  # one finish reason per decided battle

    @property
    def involves_player(self) -> bool:
        return bool((self.a and self.a.is_player) or (self.b and self.b.is_player))

    @property
    def needed(self) -> int:
        return self.best_of // 2 + 1

    @property
    def ready(self) -> bool:
        return self.a is not None and self.b is not None and self.winner is None

    @property
    def game_number(self) -> int:
        return self.wins_a + self.wins_b + 1

    def record(self, a_won: Optional[bool], reason: str = "") -> None:
        """Record one battle. `a_won` None means a draw, which is replayed."""
        if a_won is None or self.winner is not None:
            return
        if a_won:
            self.wins_a += 1
        else:
            self.wins_b += 1
        self.battles.append(reason)
        if self.wins_a >= self.needed:
            self.winner = self.a
        elif self.wins_b >= self.needed:
            self.winner = self.b


def default_field(player_blade: BladeType) -> List[Entrant]:
    """The player in slot 0 and seven AIs, weaker opponents first, a hard AI waiting in each half."""
    return [
        Entrant("You", "human", "", player_blade, True),
        Entrant("Rookie", "Cyclone", "Easy", BladeType.ATTACKER),
        Entrant("Iron Guard", "Ironclad", "Medium", BladeType.DEFENDER),
        Entrant("Storm Eye", "Cyclone", "Medium", BladeType.BALANCED),
        Entrant("Steel Wall", "Ironclad", "Easy", BladeType.STAMINA),
        Entrant("Blue Fang", "Cyclone", "Hard", BladeType.ATTACKER),
        Entrant("Grand Master", "Ironclad", "Hard", BladeType.DEFENDER),
        Entrant("Wild Spin", "Cyclone", "Medium", BladeType.STAMINA),
    ]


class Championship:
    def __init__(self, player_blade: BladeType = BladeType.BALANCED, seed: int = 1, field_: Optional[List[Entrant]] = None) -> None:
        self.seed = seed
        self.rng = random.Random(seed)
        self.entrants = field_ or default_field(player_blade)
        self.rounds: List[List[Match]] = []
        for r, n in enumerate((4, 2, 1)):
            self.rounds.append([Match(r, i, best_of=ROUND_BEST_OF[r]) for i in range(n)])
        for i, m in enumerate(self.rounds[0]):
            m.a, m.b = self.entrants[2 * i], self.entrants[2 * i + 1]
        self.player_out_round: Optional[int] = None

    # ---- state ------------------------------------------------------------------------------
    @property
    def player(self) -> Entrant:
        return next(e for e in self.entrants if e.is_player)

    @property
    def champion(self) -> Optional[Entrant]:
        return self.rounds[-1][0].winner

    @property
    def current_round(self) -> int:
        for r, ms in enumerate(self.rounds):
            if any(m.winner is None for m in ms):
                return r
        return len(self.rounds) - 1

    @property
    def over(self) -> bool:
        return self.champion is not None

    def next_player_match(self) -> Optional[Match]:
        for ms in self.rounds:
            for m in ms:
                if m.ready and m.involves_player:
                    return m
        return None

    @property
    def player_eliminated(self) -> bool:
        return self.player_out_round is not None

    def stadium_for(self, match: Match) -> StadiumType:
        return ROUND_STADIUMS[match.round]

    # ---- simulation of AI matches -----------------------------------------------------------
    def _advance(self, m: Match) -> None:
        """Put a decided match's winner into the next round."""
        if m.winner is None or m.round >= len(self.rounds) - 1:
            return
        nxt = self.rounds[m.round + 1][m.index // 2]
        if m.index % 2 == 0:
            nxt.a = m.winner
        else:
            nxt.b = m.winner
        if m.involves_player and not m.winner.is_player and self.player_out_round is None:
            self.player_out_round = m.round

    def record_player_battle(self, match: Match, battle: Battle, player_side: int = 1) -> None:
        """Record the result of a battle the player played (the player is `player_side`)."""
        if battle.winner in (1, 2):
            player_won = battle.winner == player_side
            a_won = player_won if match.a.is_player else not player_won
            match.record(a_won, battle.finish or "")
        if match.winner is not None:
            self._advance(match)

    def simulate(self, m: Match) -> None:
        """Play an AI-vs-AI match to completion headless."""
        assert m.a is not None and m.b is not None
        guard = 0
        while m.winner is None and guard < 12:
            guard += 1
            seed = self.rng.randint(0, 10 ** 6)
            ca = make_agent(m.a.agent, m.a.difficulty, seed)
            cb = make_agent(m.b.agent, m.b.difficulty, seed + 1)
            b = Battle(m.a.archetype, m.b.archetype, ROUND_STADIUMS[m.round], controllers=(ca, cb), seed=seed)
            b.run_to_end()
            if b.winner in (1, 2):
                m.record(b.winner == 1, b.finish or "")
        if m.winner is None:  # an endless run of draws: decide by seed
            m.record(self.rng.random() < 0.5, "POINTS")
            m.record(m.wins_a >= m.wins_b, "POINTS")
            if m.winner is None:
                m.winner = m.a if m.wins_a >= m.wins_b else m.b
        self._advance(m)

    def simulate_ai_matches(self) -> List[Match]:
        """Simulate every ready match that does not involve the player. Returns those played."""
        played: List[Match] = []
        for ms in self.rounds:
            for m in ms:
                if m.ready and not m.involves_player:
                    self.simulate(m)
                    played.append(m)
        return played

    def finish_without_player(self) -> None:
        """After the player is out, play every remaining match so a champion is decided."""
        guard = 0
        while not self.over and guard < 20:
            guard += 1
            if not self.simulate_ai_matches():
                break

    # ---- results ----------------------------------------------------------------------------
    def player_result(self) -> str:
        """Short text describing how far the player got."""
        if self.champion is not None and self.champion.is_player:
            return "Champion"
        if self.player_out_round is None:
            return "In progress"
        return f"Eliminated in the {ROUND_NAMES[self.player_out_round].lower()}"
