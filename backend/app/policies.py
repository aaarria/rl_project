"""Six bandit policies.

Each policy selects an arm, then observes only that arm's scaled reward.
Unvisited arms are handled explicitly: UCB-style rules try them first,
Thompson Sampling uses the report's Gaussian prior, and greedy tries each
arm once before exploiting.
"""

from __future__ import annotations

import math

import numpy as np

from app.config import TS_PRIOR_MEAN, TS_PRIOR_STRENGTH, TS_SIGMA0
from app.environment import N_ARMS


def _argmax(values: np.ndarray) -> int:
    return int(np.argmax(values))


class Policy:
    kind = "base"
    name = "Policy"

    def __init__(self, gamma: float = 1.0, ucb_c: float = 0.1):
        self.gamma = float(gamma)
        self.ucb_c = float(ucb_c)
        self.count = np.zeros(N_ARMS, dtype=np.float64)
        self.reward_sum = np.zeros(N_ARMS, dtype=np.float64)
        self.allowed = np.ones(N_ARMS, dtype=bool)
        self.last_decision: dict = {}

    def _eligible(self) -> np.ndarray:
        eligible = np.flatnonzero(self.allowed)
        if len(eligible) == 0:
            raise ValueError("at least one drive must be allowed")
        return eligible

    def q_values(self) -> np.ndarray:
        q = np.zeros(N_ARMS, dtype=np.float64)
        visited = self.count > 0
        q[visited] = self.reward_sum[visited] / self.count[visited]
        return q

    def select(self, t: int, rng: np.random.Generator) -> int:
        raise NotImplementedError

    def update(self, arm: int, scaled_reward: float) -> None:
        self.count *= self.gamma
        self.reward_sum *= self.gamma
        self.count[arm] += 1.0
        self.reward_sum[arm] += float(scaled_reward)

    def stats(self) -> dict:
        q = self.q_values()
        return {
            "count": self.count.copy(),
            "reward_sum": self.reward_sum.copy(),
            "q": q,
        }


class FixedRotation(Policy):
    kind = "fixed_rotation"
    name = "Fixed Rotation"

    def select(self, t: int, rng: np.random.Generator) -> int:
        eligible = self._eligible()
        arm = int(eligible[int(t) % len(eligible)])
        self.last_decision = {"arm": arm, "t": t, "phase": "cycle", "cycle": int(len(eligible))}
        return arm


class RandomPolicy(Policy):
    kind = "random"
    name = "Random"

    def select(self, t: int, rng: np.random.Generator) -> int:
        eligible = self._eligible()
        arm = int(rng.choice(eligible))
        self.last_decision = {"arm": arm, "t": t, "phase": "draw", "n_allowed": int(len(eligible))}
        return arm


class Greedy(Policy):
    kind = "greedy"
    name = "Greedy"

    def select(self, t: int, rng: np.random.Generator) -> int:
        self._eligible()
        unvisited = np.flatnonzero((self.count <= 0) & self.allowed)
        q = self.q_values()
        if len(unvisited):
            arm = int(unvisited[0])
            phase = "explore"
        else:
            masked = q.copy()
            masked[~self.allowed] = -np.inf
            arm = _argmax(masked)
            phase = "exploit"
        self.last_decision = {
            "arm": arm,
            "t": t,
            "phase": phase,
            "q": q.copy(),
        }
        return arm


class UCB1(Policy):
    kind = "ucb1"
    name = "UCB1"

    def index(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        q = self.q_values()
        bonus = np.full(N_ARMS, np.inf)
        total = float(self.count.sum())
        visited = self.count > 0
        if total > 0 and np.any(visited):
            bonus[visited] = self.ucb_c * np.sqrt(
                (2.0 * math.log(max(total, 1.0))) / self.count[visited]
            )
        score = q + bonus
        # Unvisited arms stay at +inf so they are tried before exploitation.
        score[~visited] = np.inf
        return score, q, bonus

    def select(self, t: int, rng: np.random.Generator) -> int:
        self._eligible()
        score, q, bonus = self.index()
        visible = score.copy()
        visible[~self.allowed] = -np.inf
        arm = _argmax(visible)
        phase = "explore" if not np.isfinite(visible[arm]) else "ucb"
        self.last_decision = {
            "arm": arm,
            "t": t,
            "phase": phase,
            "q": q.copy(),
            "bonus": np.where(np.isfinite(bonus), bonus, np.nan),
            "score": np.where(np.isfinite(visible), visible, np.nan),
        }
        return arm


class DiscountedUCB(UCB1):
    kind = "discounted_ucb"
    name = "Discounted UCB"

    def __init__(self, gamma: float, ucb_c: float = 0.1):
        super().__init__(gamma=gamma, ucb_c=ucb_c)


class DiscountedThompson(Policy):
    kind = "discounted_thompson"
    name = "Discounted Thompson Sampling"

    def select(self, t: int, rng: np.random.Generator) -> int:
        self._eligible()
        strength = TS_PRIOR_STRENGTH
        mu = (self.reward_sum + TS_PRIOR_MEAN * strength) / (self.count + strength)
        sigma = TS_SIGMA0 / np.sqrt(self.count + strength)
        samples = rng.normal(mu, sigma)
        samples = samples.copy()
        samples[~self.allowed] = -np.inf
        arm = _argmax(samples)
        self.last_decision = {
            "arm": arm,
            "t": t,
            "phase": "sample",
            "mu": mu.copy(),
            "sigma": sigma.copy(),
            "samples": samples.copy(),
            "q": self.q_values(),
        }
        return arm


POLICIES: dict[str, type[Policy]] = {
    "fixed_rotation": FixedRotation,
    "random": RandomPolicy,
    "greedy": Greedy,
    "ucb1": UCB1,
    "discounted_ucb": DiscountedUCB,
    "discounted_thompson": DiscountedThompson,
}

POLICY_ORDER = (
    "fixed_rotation",
    "random",
    "greedy",
    "ucb1",
    "discounted_ucb",
    "discounted_thompson",
)


def make_policy(policy_id: str, gamma: float, ucb_c: float) -> Policy:
    cls = POLICIES[policy_id]
    if policy_id in {"discounted_ucb", "discounted_thompson"}:
        return cls(gamma=gamma, ucb_c=ucb_c)
    return cls(gamma=1.0, ucb_c=ucb_c)
