"""User planning inputs must change the recommendation, not sit unused."""

from datetime import date

import numpy as np
from fastapi.testclient import TestClient

from app.config import BLOOD_TYPES
from app.environment import (
    initial_stock,
    objective_reward,
    raw_reward,
    shortage_vector,
    step_stock,
    target_stock,
)
from app.experiment import plan_drive
from app.main import app
from app.policies import make_policy
from app.environment import PotentialOutcomes
from app.experiment import run_episode


def _levels(amount: float) -> dict[str, float]:
    return {name: amount for name in BLOOD_TYPES}


def _payload(**overrides):
    body = {
        "facility_name": "Example City Blood Bank",
        "planning_date": "2026-03-16",
        "horizon": 4,
        "weekly_demand": 90,
        "stock": _levels(40),
        "target": _levels(100),
        "arms": ["campus_weekday", "mall_weekend", "hospital_camp"],
        "policy": "discounted_ucb",
        "objective": "weighted",
    }
    body.update(overrides)
    return body


def test_objective_scores_are_different_formulas():
    units = np.array([5, 10, 0, 0, 0, 0, 0, 0], dtype=np.float64)
    shortage = np.zeros(8, dtype=np.float64)
    shortage[0] = 1
    weighted = objective_reward(units, shortage, "weighted")
    gaps = objective_reward(units, shortage, "shortage")
    o_negative = objective_reward(units, shortage, "o_negative")
    assert gaps == float(5 * 2.0 * 1)
    assert o_negative == float(5 * 2.0 * 2)
    assert weighted != gaps
    assert weighted != o_negative


def test_episode_learns_the_selected_objective():
    outcomes = PotentialOutcomes(seed=3, horizon=6, weekly_demand=90)
    policy = make_policy("fixed_rotation", gamma=1, ucb_c=0.1)
    episode = run_episode(
        policy,
        outcomes,
        np.random.default_rng(3),
        initial_fraction=0.6,
        wastage=0.02,
        objective="o_negative",
    )
    stock = initial_stock(90, 0.6)
    target = target_stock(90)
    learned = 0.0
    standard = 0.0
    for week, arm in enumerate(episode["choices"]):
        shortage = shortage_vector(stock, target)
        collected = outcomes.collected[week, arm]
        learned += objective_reward(collected, shortage, "o_negative")
        standard += raw_reward(collected, shortage)
        stock = step_stock(stock, collected, outcomes.demand[week], wastage=0.02)
    assert abs(learned - episode["cumulative_reward"]) < 1e-6
    assert abs(standard - episode["cumulative_weighted"]) < 1e-6
    assert episode["cumulative_reward"] != episode["cumulative_weighted"]


def test_plan_uses_stock_targets_arms_and_date():
    low = plan_drive(
        facility_name="North Bank",
        planning_date="2026-01-05",
        horizon=4,
        weekly_demand=80,
        stock=_levels(0),
        target=_levels(50),
        arm_ids=["mall_weekend"],
        policy_id="fixed_rotation",
        objective="shortage",
        discount=0.95,
        ucb_c=0.1,
        seed=0,
        wastage=0.02,
    )
    high = plan_drive(
        facility_name="North Bank",
        planning_date="2026-01-05",
        horizon=4,
        weekly_demand=80,
        stock=_levels(500),
        target=_levels(50),
        arm_ids=["mall_weekend"],
        policy_id="fixed_rotation",
        objective="shortage",
        discount=0.95,
        ucb_c=0.1,
        seed=0,
        wastage=0.02,
    )
    assert low["recommended"]["id"] == "mall_weekend"
    assert len(low["alternatives"]) == 1
    assert low["inventory"]["opening_stock"]["O-"] == 0
    assert high["inventory"]["opening_stock"]["O-"] == 500
    assert low["inventory"]["final_stock"] != high["inventory"]["final_stock"]
    assert low["estimates"]["objective_score"] != high["estimates"]["objective_score"]
    assert low["calendar_week"] == date.fromisoformat("2026-01-05").isocalendar().week
    assert "community-centre" in low["date_effect"]
    summer = plan_drive(
        facility_name="",
        planning_date="2026-07-06",
        horizon=1,
        weekly_demand=90,
        stock=_levels(20),
        target=_levels(40),
        arm_ids=["campus_weekday"],
        policy_id="greedy",
        objective="weighted",
        discount=0.95,
        ucb_c=0.1,
        seed=0,
        wastage=0.02,
    )
    winter = plan_drive(
        facility_name="",
        planning_date="2026-01-05",
        horizon=1,
        weekly_demand=90,
        stock=_levels(20),
        target=_levels(40),
        arm_ids=["campus_weekday"],
        policy_id="greedy",
        objective="weighted",
        discount=0.95,
        ucb_c=0.1,
        seed=0,
        wastage=0.02,
    )
    assert summer["calendar_week"] != winter["calendar_week"]
    assert summer["estimates"]["donors"] != winter["estimates"]["donors"]


def test_restricted_rotation_stays_inside_the_allowed_drives():
    policy = make_policy("fixed_rotation", gamma=1, ucb_c=0.1)
    policy.allowed[:] = False
    policy.allowed[1] = True
    policy.allowed[3] = True
    rng = np.random.default_rng(0)
    assert [policy.select(t, rng) for t in range(4)] == [1, 3, 1, 3]


def test_plan_api_rejects_bad_inventory_and_accepts_a_real_plan():
    client = TestClient(app)
    negative = _payload()
    negative["stock"] = {**negative["stock"], "O-": -1}
    bad = client.post("/api/v1/plan", json=negative)
    assert bad.status_code == 422
    assert "0 or higher" in bad.text

    unknown = _payload(arms=["not_a_drive"])
    rejected = client.post("/api/v1/plan", json=unknown)
    assert rejected.status_code == 422

    created = client.post("/api/v1/plan", json=_payload(objective="o_negative"))
    assert created.status_code == 200
    body = created.json()
    assert body["objective"] == "o_negative"
    assert body["inputs"]["weekly_demand"] == 90
    assert body["inputs"]["stock"]["A+"] == 40
    assert body["recommended"]["id"] in {"campus_weekday", "mall_weekend", "hospital_camp"}
    assert body["estimates"]["label"]
    assert "not a count of real donors" in body["estimates"]["label"].lower()

    compared = client.post("/api/v1/plan/compare", json=_payload())
    assert compared.status_code == 200
    rows = compared.json()["rows"]
    assert len(rows) == 6
    assert any(row["selected_by_user"] and row["id"] == "discounted_ucb" for row in rows)
