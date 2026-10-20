"""Reproducible blood-drive environment.

Week order (also listed in config.WEEK_ORDER):
1. Shortage from current stock.
2. Policy selects an arm.
3. Collection is the pre-drawn binomial / multinomial outcome for that arm.
4. Raw reward from collected units and current shortage.
5. Policy update uses reward / REWARD_SCALE and only the selected arm.
6. Demand is the pre-drawn Poisson vector.
7. Wastage applies to pre-existing stock.
8. Stock = max(0, (1 - wastage) * stock + collected - demand).
"""

from __future__ import annotations

import numpy as np

from app.config import (
    ARMS,
    BLOOD_TYPES,
    DEFAULT_WASTAGE,
    DEMAND_SHARE,
    LOYALTY_RATE,
    O_NEGATIVE_BOOST,
    O_NEGATIVE_BOOSTED_ARMS,
    POPULATION_MIX,
    PRIORITY,
    REWARD_SCALE,
    TARGET_WEEKS,
    TURNOUT_CAP,
)

N_TYPES = len(BLOOD_TYPES)
N_ARMS = len(ARMS)
ARM_INDEX = {arm["id"]: i for i, arm in enumerate(ARMS)}
PRIORITY_VEC = np.array([PRIORITY[k] for k in BLOOD_TYPES], dtype=np.float64)
POPULATION_VEC = np.array([POPULATION_MIX[k] for k in BLOOD_TYPES], dtype=np.float64)
DEMAND_VEC = np.array([DEMAND_SHARE[k] for k in BLOOD_TYPES], dtype=np.float64)


def _mix_for(arm_id: str) -> np.ndarray:
    mix = POPULATION_VEC.copy()
    if arm_id in O_NEGATIVE_BOOSTED_ARMS:
        mix[0] *= O_NEGATIVE_BOOST
        mix /= mix.sum()
    return mix


ARM_MIX = np.stack([_mix_for(arm["id"]) for arm in ARMS])
ARM_POOL = np.array([arm["pool"] for arm in ARMS], dtype=np.int64)
ARM_TAU = np.array([LOYALTY_RATE[arm["tier"]] for arm in ARMS], dtype=np.float64)


def seasonal_multiplier(arm_index: int, week_index: int, origin_week: int = 1) -> float:
    """Seasonal multiplier m_a(t).

    week_index is 0-based. Report week numbers are 1-based (week 40 is index 39).
    origin_week is the calendar week (1..52) of week_index 0. The default of 1
    keeps the original study calendar. Community-centre decay and the tech-park
    opening still follow the study week count, not the calendar date.
    """
    week = week_index + 1
    woy = ((int(origin_week) - 1 + int(week_index)) % 52) + 1
    arm_id = ARMS[arm_index]["id"]

    if arm_id == "campus_weekday":
        if 18 <= woy <= 30:
            return 0.30
        if woy <= 2 or woy >= 51:
            return 0.30
        if 10 <= woy <= 14 or 42 <= woy <= 46:
            return 1.35
        return 1.0
    if arm_id == "campus_weekend":
        return 0.6 if 18 <= woy <= 30 else 1.0
    if arm_id == "corporate_lunch":
        if 8 <= woy <= 13 or 32 <= woy <= 37:
            return 1.9
        return 0.75
    if arm_id == "corporate_weekend":
        return 1.0
    if arm_id == "community_centre":
        if week <= 30:
            return 1.0
        if week >= 104:
            return 0.55
        return 1.0 + (0.55 - 1.0) * ((week - 30) / (104 - 30))
    if arm_id == "mall_weekend":
        return 1.8 if 38 <= woy <= 49 else 0.85
    if arm_id == "hospital_camp":
        return 1.0
    if arm_id == "tech_park_evening":
        if week <= 40:
            return 0.3
        if week >= 104:
            return 2.6
        return 0.3 + (2.6 - 0.3) * ((week - 40) / (104 - 40))
    raise KeyError(arm_id)


def turnout_probability(arm_index: int, week_index: int, origin_week: int = 1) -> float:
    raw = float(ARM_TAU[arm_index] * seasonal_multiplier(arm_index, week_index, origin_week))
    return float(min(TURNOUT_CAP, raw))


def expected_turnout(arm_index: int, week_index: int, origin_week: int = 1) -> float:
    return float(ARM_POOL[arm_index] * turnout_probability(arm_index, week_index, origin_week))


def expected_units(arm_index: int, week_index: int, origin_week: int = 1) -> np.ndarray:
    return expected_turnout(arm_index, week_index, origin_week) * ARM_MIX[arm_index]


def target_stock(weekly_demand: float) -> np.ndarray:
    return TARGET_WEEKS * float(weekly_demand) * DEMAND_VEC


def shortage_vector(stock: np.ndarray, target: np.ndarray) -> np.ndarray:
    safe = np.divide(stock, target, out=np.zeros_like(stock, dtype=np.float64), where=target > 0)
    return np.clip(1.0 - safe, 0.0, 1.0)


def raw_reward(units: np.ndarray, shortage: np.ndarray) -> float:
    """Report reward: sum_k u_k * c_k * (0.1 + s_k). Not divided by 100."""
    return float(np.sum(units * PRIORITY_VEC * (0.1 + shortage)))


def objective_reward(units: np.ndarray, shortage: np.ndarray, objective: str) -> float:
    """Score the learner actually sees.

    weighted: the report formula. Every unit counts, scarce types more.
    shortage: units count only for types still below target.
    o_negative: only O-negative units, weighted more when O-negative is short.
    """
    if objective == "weighted":
        return raw_reward(units, shortage)
    if objective == "shortage":
        return float(np.sum(units * PRIORITY_VEC * shortage))
    if objective == "o_negative":
        return float(units[0] * PRIORITY_VEC[0] * (1.0 + shortage[0]))
    raise ValueError(f"unknown objective: {objective}")


def expected_reward(
    arm_index: int,
    week_index: int,
    shortage: np.ndarray,
    origin_week: int = 1,
) -> float:
    """Mean-field report reward. This is an expectation, not a sampled drive."""
    units = expected_units(arm_index, week_index, origin_week)
    return raw_reward(units, shortage)


def expected_objective(
    arm_index: int,
    week_index: int,
    shortage: np.ndarray,
    objective: str,
    origin_week: int = 1,
) -> float:
    units = expected_units(arm_index, week_index, origin_week)
    return objective_reward(units, shortage, objective)


def scale_reward(raw: float) -> float:
    return float(raw) / REWARD_SCALE


def step_stock(
    stock: np.ndarray,
    collected: np.ndarray,
    demand: np.ndarray,
    wastage: float = DEFAULT_WASTAGE,
) -> np.ndarray:
    """Apply wastage to stock on hand, add collection, subtract demand, floor at 0."""
    updated = (1.0 - wastage) * stock + collected - demand
    return np.maximum(0.0, updated)


class PotentialOutcomes:
    """Pre-drawn collections and demand so every policy sees the same weeks."""

    def __init__(
        self,
        seed: int,
        horizon: int,
        weekly_demand: float,
        rng: np.random.Generator | None = None,
        origin_week: int = 1,
    ):
        self.seed = int(seed)
        self.horizon = int(horizon)
        self.weekly_demand = float(weekly_demand)
        self.origin_week = int(origin_week)
        generator = rng if rng is not None else np.random.default_rng(self.seed)
        self.demand = np.zeros((horizon, N_TYPES), dtype=np.float64)
        self.collected = np.zeros((horizon, N_ARMS, N_TYPES), dtype=np.float64)
        self.turnout = np.zeros((horizon, N_ARMS), dtype=np.int64)
        means = self.weekly_demand * DEMAND_VEC
        for t in range(horizon):
            self.demand[t] = generator.poisson(means)
            for a in range(N_ARMS):
                probability = turnout_probability(a, t, self.origin_week)
                count = int(generator.binomial(int(ARM_POOL[a]), probability))
                self.turnout[t, a] = count
                if count > 0:
                    self.collected[t, a] = generator.multinomial(count, ARM_MIX[a])


def initial_stock(weekly_demand: float, fraction: float) -> np.ndarray:
    return fraction * target_stock(weekly_demand)
