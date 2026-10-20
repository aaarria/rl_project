"""Request models. Presets overwrite horizon and seed count after the body is read."""

from __future__ import annotations

import math
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.config import ARMS, BLOOD_TYPES
from app.policies import POLICY_ORDER

PolicyId = Literal[
    "fixed_rotation",
    "random",
    "greedy",
    "ucb1",
    "discounted_ucb",
    "discounted_thompson",
]


class SimulateRequest(BaseModel):
    preset: Literal["quick", "full", "custom"] = "custom"
    horizon: int = 52
    n_seeds: int = 3
    seeds: list[int] | None = None
    initial_stock_fraction: float = 0.6
    weekly_demand: float = 90
    discount: float = 0.95
    ucb_c: float = 0.1
    wastage: float = 0.02
    policies: list[PolicyId] | None = None

    @model_validator(mode="after")
    def check(self) -> "SimulateRequest":
        if self.preset == "quick":
            self.horizon = 52
            self.n_seeds = 3
            self.seeds = None
        elif self.preset == "full":
            self.horizon = 104
            self.n_seeds = 10
            self.seeds = None
        if self.seeds:
            self.n_seeds = len(self.seeds)
        if not 1 <= self.horizon <= 520:
            raise ValueError("horizon must be between 1 and 520 weeks")
        if not 1 <= self.n_seeds <= 30:
            raise ValueError("n_seeds must be between 1 and 30")
        if self.seeds is not None:
            if any(seed < 0 or seed > 1_000_000 for seed in self.seeds):
                raise ValueError("each seed must be between 0 and 1000000")
        if not 0 <= self.initial_stock_fraction <= 1.5:
            raise ValueError("initial_stock_fraction must be between 0 and 1.5")
        if not 1 <= self.weekly_demand <= 5000:
            raise ValueError("weekly_demand must be between 1 and 5000")
        if not 0 < self.discount <= 1:
            raise ValueError("discount must be in (0, 1]")
        if not 0 < self.ucb_c <= 5:
            raise ValueError("ucb_c must be in (0, 5]")
        if not 0 <= self.wastage < 0.5:
            raise ValueError("wastage must be in [0, 0.5)")
        if self.policies is not None and len(self.policies) == 0:
            raise ValueError("select at least one policy")
        return self

    def resolved_seeds(self) -> list[int]:
        if self.seeds:
            return list(self.seeds)
        return list(range(self.n_seeds))

    def resolved_policies(self) -> list[str]:
        if self.policies:
            return list(dict.fromkeys(self.policies))
        return list(POLICY_ORDER)


class SensitivityRequest(BaseModel):
    preset: Literal["quick", "full", "custom"] = "quick"
    horizon: int = 40
    n_seeds: int = 3
    discount_grid: list[float] = Field(default_factory=lambda: [0.8, 0.9, 0.95, 0.98, 1.0])
    ucb_c: float = 0.1
    initial_stock_fraction: float = 0.6
    weekly_demand: float = 90
    wastage: float = 0.02

    @model_validator(mode="after")
    def check(self) -> "SensitivityRequest":
        if self.preset == "quick":
            self.horizon = 40
            self.n_seeds = 2
            self.discount_grid = [0.8, 0.95, 1.0]
        elif self.preset == "full":
            self.horizon = 104
            self.n_seeds = 10
            self.discount_grid = [0.8, 0.9, 0.95, 0.98, 1.0]
        if not 1 <= self.horizon <= 520:
            raise ValueError("horizon must be between 1 and 520 weeks")
        if not 1 <= self.n_seeds <= 30:
            raise ValueError("n_seeds must be between 1 and 30")
        if not self.discount_grid or len(self.discount_grid) > 8:
            raise ValueError("discount_grid must contain 1 to 8 values")
        if any(not 0 < gamma <= 1 for gamma in self.discount_grid):
            raise ValueError("each discount must be in (0, 1]")
        if not 0 < self.ucb_c <= 5:
            raise ValueError("ucb_c must be in (0, 5]")
        if not 0 <= self.initial_stock_fraction <= 1.5:
            raise ValueError("initial_stock_fraction must be between 0 and 1.5")
        if not 1 <= self.weekly_demand <= 5000:
            raise ValueError("weekly_demand must be between 1 and 5000")
        return self


class RecommendRequest(BaseModel):
    policy: PolicyId
    horizon: int = 52
    seed: int = 0
    initial_stock_fraction: float = 0.6
    weekly_demand: float = 90
    discount: float = 0.95
    ucb_c: float = 0.1
    wastage: float = 0.02

    @model_validator(mode="after")
    def check(self) -> "RecommendRequest":
        if not 1 <= self.horizon <= 520:
            raise ValueError("horizon must be between 1 and 520 weeks")
        if not 0 <= self.seed <= 1_000_000:
            raise ValueError("seed must be between 0 and 1000000")
        if not 0 <= self.initial_stock_fraction <= 1.5:
            raise ValueError("initial_stock_fraction must be between 0 and 1.5")
        if not 1 <= self.weekly_demand <= 5000:
            raise ValueError("weekly_demand must be between 1 and 5000")
        if not 0 < self.discount <= 1:
            raise ValueError("discount must be in (0, 1]")
        if not 0 < self.ucb_c <= 5:
            raise ValueError("ucb_c must be in (0, 5]")
        if not 0 <= self.wastage < 0.5:
            raise ValueError("wastage must be in [0, 0.5)")
        return self


ObjectiveId = Literal["weighted", "shortage", "o_negative"]

_ARM_IDS = {arm["id"] for arm in ARMS}


def _check_levels(value: dict[str, float], label: str) -> dict[str, float]:
    missing = [name for name in BLOOD_TYPES if name not in value]
    extra = [name for name in value if name not in BLOOD_TYPES]
    if missing or extra:
        raise ValueError(
            f"{label} must use exactly these blood types: {', '.join(BLOOD_TYPES)}"
        )
    cleaned: dict[str, float] = {}
    for name in BLOOD_TYPES:
        number = value[name]
        try:
            amount = float(number)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{name} {label.lower()} must be a number") from exc
        if not math.isfinite(amount) or amount < 0:
            raise ValueError(f"{name} {label.lower()} must be 0 or higher")
        if amount > 1_000_000:
            raise ValueError(f"{name} {label.lower()} must be 1000000 or less")
        cleaned[name] = amount
    return cleaned


class PlanRequest(BaseModel):
    facility_name: str = ""
    planning_date: str
    horizon: int = 12
    weekly_demand: float = 90
    stock: dict[str, float]
    target: dict[str, float]
    arms: list[str]
    policy: PolicyId = "discounted_ucb"
    objective: ObjectiveId = "weighted"
    discount: float = 0.95
    ucb_c: float = 0.1
    seed: int = 0
    wastage: float = 0.02

    @model_validator(mode="after")
    def check(self) -> "PlanRequest":
        self.facility_name = " ".join(self.facility_name.split())
        if len(self.facility_name) > 120:
            raise ValueError("facility name must be 120 characters or fewer")
        try:
            parsed = date.fromisoformat(self.planning_date)
        except ValueError as exc:
            raise ValueError("planning date must be a real date in YYYY-MM-DD form") from exc
        if parsed.year < 2000 or parsed.year > 2100:
            raise ValueError("planning date must fall between 2000 and 2100")
        self.planning_date = parsed.isoformat()
        if not 1 <= self.horizon <= 520:
            raise ValueError("horizon must be between 1 and 520 weeks")
        if not 0 <= self.weekly_demand <= 5000:
            raise ValueError("weekly demand must be between 0 and 5000")
        self.stock = _check_levels(self.stock, "Stock")
        self.target = _check_levels(self.target, "Target")
        if not self.arms:
            raise ValueError("choose at least one drive")
        unknown = [arm_id for arm_id in self.arms if arm_id not in _ARM_IDS]
        if unknown:
            raise ValueError(f"unknown drive: {', '.join(unknown)}")
        if len(set(self.arms)) != len(self.arms):
            raise ValueError("each drive can be selected only once")
        if not 0 <= self.seed <= 1_000_000:
            raise ValueError("seed must be between 0 and 1000000")
        if not 0 < self.discount <= 1:
            raise ValueError("discount must be in (0, 1]")
        if not 0 < self.ucb_c <= 5:
            raise ValueError("ucb_c must be in (0, 5]")
        if not 0 <= self.wastage < 0.5:
            raise ValueError("wastage must be in [0, 0.5)")
        return self
