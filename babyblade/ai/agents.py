"""AI agents and the human controller.

Both AIs are resumable: `begin()` creates a search generator and `step(budget)` advances it for
at most `budget` seconds of CPU, so the game can spread thinking across frames (no hitch at the
round boundary, which matters in the browser where there are no threads).

* Ironclad — Minimax with MAX-VALUE / MIN-VALUE, alpha-beta pruning, depth-limited search and
  iterative deepening (AI Lab 2 and 4).
* Cyclone — Monte Carlo Tree Search: selection with UCB1, expansion, simulation, backpropagation
  (Lecture 5). Simultaneous moves use decoupled UCT: each player keeps its own action stats
  at every node.
"""

from __future__ import annotations

import math
import random
import time
from typing import Dict, Generator, List, Optional, Tuple

from babyblade.sim import model
from babyblade.sim.actions import Action, ORDER
from babyblade.sim.model import State, actions, heuristic, result, terminal, utility

Search = Generator[None, None, None]

DIFFICULTIES = ("Easy", "Medium", "Hard")


class _Resumable:
    """Runs a search generator in time slices."""

    name = "Agent"
    is_human = False
    steer_skill = 1.0  # how well the agent steers its top (Easy < Medium < Hard)

    def __init__(self) -> None:
        self._gen: Optional[Search] = None
        self._choice: Action = Action.CHARGE
        self.info: Dict[str, object] = {}

    def begin(self, state: State, player: int) -> None:
        self._choice = actions(state, player)[0]
        self._gen = self._search(state, player)

    def step(self, budget_s: float) -> bool:
        if self._gen is None:
            return True
        deadline = time.perf_counter() + budget_s
        try:
            while time.perf_counter() < deadline:
                next(self._gen)
        except StopIteration:
            self._gen = None
            return True
        return False

    def choice(self) -> Action:
        return self._choice

    def decide(self, state: State, player: int) -> Action:
        """Synchronous convenience for tests and tools."""
        self.begin(state, player)
        while not self.step(1.0):
            pass
        return self._choice

    def _search(self, state: State, player: int) -> Search:  # pragma: no cover - abstract
        raise NotImplementedError
        yield


# ---- Ironclad: Minimax ------------------------------------------------------------------------------

class Ironclad(_Resumable):
    """Depth-limited Minimax with alpha-beta pruning and iterative deepening."""

    DEPTH = {"Easy": 1, "Medium": 2, "Hard": 3}
    CPU_CAP = {"Easy": 0.05, "Medium": 0.25, "Hard": 0.40}

    def __init__(self, difficulty: str = "Medium", seed: int = 1) -> None:
        super().__init__()
        self.difficulty = difficulty
        self.name = f"Ironclad ({difficulty})"
        self.steer_skill = {"Easy": 0.6, "Medium": 0.85, "Hard": 1.0}[difficulty]
        self.max_depth = self.DEPTH[difficulty]
        self.cpu_cap = self.CPU_CAP[difficulty]
        self.rng = random.Random(seed)
        self.nodes = 0

    def _search(self, state: State, player: int) -> Search:
        start = time.perf_counter()
        spent = 0.0
        opp = 2 if player == 1 else 1
        my_moves = self._ordered(state, player)
        best = my_moves[0]
        scores: Dict[Action, float] = {}
        depth_done = 0
        self.nodes = 0
        for depth in range(1, self.max_depth + 1):  # iterative deepening
            depth_scores: Dict[Action, float] = {}
            alpha = -math.inf
            depth_best = my_moves[0]
            aborted = False
            for a in my_moves:  # MAX-VALUE at the root
                v = math.inf
                for o in actions(state, opp):  # MIN-VALUE: opponent's best reply
                    child = result(state, a, o) if player == 1 else result(state, o, a)
                    cv = yield from self._value(child, depth - 1, player, alpha, v)
                    v = min(v, cv)
                    if v <= alpha:  # alpha cut: this move cannot beat the best so far
                        break
                depth_scores[a] = v
                if v > alpha:
                    alpha, depth_best = v, a
                if time.perf_counter() - start > self.cpu_cap * 6:  # wall-clock safety
                    aborted = True
                    break
            if aborted:
                break
            best, scores, depth_done = depth_best, depth_scores, depth
            my_moves.sort(key=lambda m: -depth_scores.get(m, -math.inf))  # better ordering
        spent = time.perf_counter() - start
        if self.difficulty == "Easy" and self.rng.random() < 0.15:
            best = self.rng.choice(actions(state, player))  # easy makes the odd mistake
        self._choice = best
        self.info = {"agent": "Ironclad", "action": best, "scores": scores, "depth": depth_done,
                     "nodes": self.nodes, "ms": spent * 1000.0}

    def _value(self, s: State, depth: int, player: int, alpha: float, beta: float):
        """Value of state s for `player` (MAX), opponent minimizes; alpha-beta bounds."""
        self.nodes += 1
        if self.nodes % 48 == 0:
            yield
        if terminal(s) or depth == 0:
            return utility(s, player)
        opp = 2 if player == 1 else 1
        best = -math.inf
        for a in self._ordered(s, player):
            v = math.inf
            for o in actions(s, opp):
                child = result(s, a, o) if player == 1 else result(s, o, a)
                cv = yield from self._value(child, depth - 1, player, max(alpha, best), v)
                v = min(v, cv)
                if v <= max(alpha, best):
                    break
            best = max(best, v)
            if best >= beta:  # beta cut
                return best
        return best

    @staticmethod
    def _ordered(s: State, player: int) -> List[Action]:
        moves = actions(s, player)
        return sorted(moves, key=lambda a: ORDER.index(a))


# ---- Cyclone: MCTS ------------------------------------------------------------------------------------

class _Node:
    __slots__ = ("state", "children", "n", "stats1", "stats2")

    def __init__(self, state: State) -> None:
        self.state = state
        self.children: Dict[Tuple[Action, Action], "_Node"] = {}
        self.n = 0
        self.stats1: Dict[Action, List[float]] = {a: [0, 0.0] for a in actions(state, 1)}
        self.stats2: Dict[Action, List[float]] = {a: [0, 0.0] for a in actions(state, 2)}


class Cyclone(_Resumable):
    """Monte Carlo Tree Search with UCB1 (decoupled UCT for simultaneous moves)."""

    ITERATIONS = {"Easy": 60, "Medium": 200, "Hard": 500}
    CPU_CAP = {"Easy": 0.06, "Medium": 0.25, "Hard": 0.45}
    C = 1.4
    ROLLOUT_DEPTH = 4

    def __init__(self, difficulty: str = "Medium", seed: int = 2) -> None:
        super().__init__()
        self.difficulty = difficulty
        self.name = f"Cyclone ({difficulty})"
        self.steer_skill = {"Easy": 0.6, "Medium": 0.85, "Hard": 1.0}[difficulty]
        self.iterations = self.ITERATIONS[difficulty]
        self.cpu_cap = self.CPU_CAP[difficulty]
        self.rng = random.Random(seed)

    def _ucb(self, stats: Dict[Action, List[float]], n: int) -> Action:
        best, best_v = None, -math.inf
        for a, (cnt, total) in stats.items():
            if cnt == 0:
                return a  # try every action once
            v = total / cnt + self.C * math.sqrt(math.log(max(1, n)) / cnt)
            if v > best_v:
                best, best_v = a, v
        assert best is not None
        return best

    def _rollout_policy(self, s: State, player: int) -> Action:
        moves = actions(s, player)
        if self.rng.random() < 0.5:
            return self.rng.choice(moves)
        # Greedy one-step look at the heuristic against a random reply.
        opp = 2 if player == 1 else 1
        reply = self.rng.choice(actions(s, opp))
        best, best_v = moves[0], -math.inf
        for a in moves:
            child = result(s, a, reply) if player == 1 else result(s, reply, a)
            v = utility(child, player)
            if v > best_v:
                best, best_v = a, v
        return best

    def _search(self, state: State, player: int) -> Search:
        start = time.perf_counter()
        root = _Node(state)
        it = 0
        while it < self.iterations and time.perf_counter() - start < self.cpu_cap * 6:
            it += 1
            node = root
            path: List[Tuple[_Node, Action, Action]] = []
            # 1. Selection (UCB1 for each player independently) and 2. Expansion
            while not terminal(node.state):
                a1 = self._ucb(node.stats1, node.n)
                a2 = self._ucb(node.stats2, node.n)
                path.append((node, a1, a2))
                child = node.children.get((a1, a2))
                if child is None:
                    child = _Node(result(node.state, a1, a2))
                    node.children[(a1, a2)] = child
                    node = child
                    break
                node = child
            # 3. Simulation
            s = node.state
            depth = 0
            while not terminal(s) and depth < self.ROLLOUT_DEPTH:
                s = result(s, self._rollout_policy(s, 1), self._rollout_policy(s, 2))
                depth += 1
            r1 = (utility(s, 1) + 1.0) / 2.0  # reward for player 1 in [0, 1]
            # 4. Backpropagation (zero-sum: player 2 gets 1 - r1)
            node.n += 1
            for n_, a1, a2 in path:
                n_.n += 1
                n_.stats1[a1][0] += 1
                n_.stats1[a1][1] += r1
                n_.stats2[a2][0] += 1
                n_.stats2[a2][1] += 1.0 - r1
            if it % 6 == 0:
                yield
        stats = root.stats1 if player == 1 else root.stats2
        best = max(stats, key=lambda a: (stats[a][0], stats[a][1]))
        if self.difficulty == "Easy" and self.rng.random() < 0.15:
            best = self.rng.choice(list(stats))
        self._choice = best
        visits = {a: int(v[0]) for a, v in stats.items()}
        value = stats[best][1] / stats[best][0] if stats[best][0] else 0.5
        self.info = {"agent": "Cyclone", "action": best, "visits": visits, "iterations": it,
                     "value": value, "ms": (time.perf_counter() - start) * 1000.0}


# ---- Human ------------------------------------------------------------------------------------------

class Human:
    """The player's queued action locks in at the next round boundary."""

    is_human = True

    def __init__(self, name: str = "You") -> None:
        self.name = name
        self.queued: Action = Action.CHARGE
        self.info: Dict[str, object] = {}
        self._legal: List[Action] = [Action.CHARGE]

    def begin(self, state: State, player: int) -> None:
        self._legal = actions(state, player)

    def step(self, budget_s: float) -> bool:
        return True

    def choice(self) -> Action:
        return self.queued if self.queued in self._legal else Action.CHARGE


def make_agent(kind: str, difficulty: str, seed: int = 0):
    if kind.lower().startswith("iron"):
        return Ironclad(difficulty, seed=seed + 11)
    return Cyclone(difficulty, seed=seed + 23)
