"""Engine, audit, and API tests. These run the simulator; they do not reuse report tables."""

from __future__ import annotations

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.data_audit import run_audit
from app.environment import raw_reward, step_stock
from app.experiment import run_comparison, run_episode
from app.export import comparison_to_csv
from app.environment import PotentialOutcomes
from app.main import app
from app.policies import UCB1, make_policy


def test_reward_matches_report_formula():
    units = np.zeros(8)
    units[0] = 10  # O-
    units[2] = 4  # A-
    shortage = np.zeros(8)
    shortage[0] = 0.5
    shortage[2] = 0.0
    # 10 * 2.0 * (0.1 + 0.5) + 4 * 1.3 * (0.1 + 0.0)
    assert raw_reward(units, shortage) == pytest.approx(12.0 + 0.52)


def test_stock_update_applies_wastage_then_floors_at_zero():
    stock = np.full(8, 100.0)
    collected = np.full(8, 5.0)
    demand = np.full(8, 3.0)
    updated = step_stock(stock, collected, demand, wastage=0.02)
    assert np.allclose(updated, (1 - 0.02) * 100 + 5 - 3)

    drained = step_stock(np.full(8, 1.0), np.zeros(8), np.full(8, 50.0), wastage=0.02)
    assert np.all(drained == 0)


def test_policy_updates_only_the_selected_arm():
    policy = UCB1(gamma=1.0, ucb_c=0.1)
    rng = np.random.default_rng(0)
    first = policy.select(0, rng)
    policy.update(first, 0.25)
    assert first == 0
    assert policy.count[0] == pytest.approx(1)
    assert np.all(policy.count[1:] == 0)
    assert policy.reward_sum[0] == pytest.approx(0.25)
    assert np.all(policy.reward_sum[1:] == 0)


def test_greedy_tries_each_arm_once_then_exploits():
    policy = make_policy("greedy", gamma=0.95, ucb_c=0.1)
    rng = np.random.default_rng(1)
    chosen = []
    for t in range(8):
        arm = policy.select(t, rng)
        chosen.append(arm)
        policy.update(arm, 0.9 if arm == 3 else 0.1)
    assert chosen == list(range(8))
    assert policy.select(8, rng) == 3
    # The discounted policies are the only ones that fade history. Greedy keeps gamma = 1.
    assert policy.gamma == 1.0
    assert policy.count[3] == pytest.approx(1)


def test_fixed_rotation_cycles_and_ignores_rewards():
    policy = make_policy("fixed_rotation", gamma=0.5, ucb_c=0.1)
    rng = np.random.default_rng(2)
    choices = [policy.select(t, rng) for t in range(16)]
    assert choices == [t % 8 for t in range(16)]


def test_discounted_ucb_matches_ucb1_when_gamma_is_one():
    outcomes = PotentialOutcomes(seed=7, horizon=36, weekly_demand=90)
    ucb = run_episode(
        make_policy("ucb1", gamma=1.0, ucb_c=0.1),
        outcomes,
        np.random.default_rng(1),
        0.6,
        0.02,
    )
    discounted = run_episode(
        make_policy("discounted_ucb", gamma=1.0, ucb_c=0.1),
        outcomes,
        np.random.default_rng(1),
        0.6,
        0.02,
    )
    assert ucb["choices"] == discounted["choices"]
    assert ucb["cumulative_reward"] == pytest.approx(discounted["cumulative_reward"])


def test_seed_reproducibility_and_non_negative_stock():
    first = run_comparison(
        horizon=24,
        seeds=[0, 1],
        policies=["fixed_rotation", "random", "greedy", "ucb1", "discounted_ucb", "discounted_thompson"],
        initial_stock_fraction=0.6,
        weekly_demand=90,
        discount=0.95,
        ucb_c=0.1,
        wastage=0.02,
        preset="custom",
    )
    second = run_comparison(
        horizon=24,
        seeds=[0, 1],
        policies=["fixed_rotation", "random", "greedy", "ucb1", "discounted_ucb", "discounted_thompson"],
        initial_stock_fraction=0.6,
        weekly_demand=90,
        discount=0.95,
        ucb_c=0.1,
        wastage=0.02,
        preset="custom",
    )
    assert first["policies"][0]["seed_cumulative_rewards"] == second["policies"][0]["seed_cumulative_rewards"]
    fixed = next(row for row in first["policies"] if row["id"] == "fixed_rotation")
    assert fixed["improvement_vs_fixed"] == 0
    for row in first["policies"]:
        for series in row["curve"]["stock"].values():
            assert min(series) >= -1e-9
        assert abs(sum(row["arm_frequency"].values()) - 1) < 1e-9


def test_dataset_audit_shape_and_target():
    report = run_audit()
    assert report["shape"]["rows"] == 748
    assert report["shape"]["column_names"] == ["Recency", "Frequency", "Monetary", "Time", "Donated"]
    assert report["missing_and_malformed"]["malformed_or_non_numeric_cells"] == 0
    assert report["target"]["encoding_is_binary_0_1"] is True
    assert report["target"]["donated_march_2007"] + report["target"]["did_not_donate"] == 748
    assert "blood types" in " ".join(report["not_in_this_file"]).lower() or any(
        "blood" in item.lower() for item in report["not_in_this_file"]
    )
    assert report["duplicates"]["action"].startswith("Duplicates were counted")


def test_csv_export_uses_computed_rows():
    result = run_comparison(
        horizon=8,
        seeds=[3],
        policies=["fixed_rotation", "greedy"],
        initial_stock_fraction=0.6,
        weekly_demand=90,
        discount=0.95,
        ucb_c=0.1,
        wastage=0.02,
        preset="custom",
    )
    csv_text = comparison_to_csv(result)
    assert csv_text.splitlines()[0].startswith("policy,policy_name,mean_cumulative_reward")
    assert "fixed_rotation" in csv_text
    assert "greedy" in csv_text
    reward = f"{result['policies'][0]['mean_cumulative_reward']}"
    assert reward in csv_text


def test_api_health_config_and_invalid_parameters():
    client = TestClient(app)
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    config = client.get("/api/v1/config")
    assert config.status_code == 200
    assert len(config.json()["policies"]) == 6
    bad = client.post("/api/v1/simulate", json={"horizon": 0, "preset": "custom"})
    assert bad.status_code == 422
    body = bad.json()["error"]
    assert body["code"] == "validation_error"
    unknown = client.post("/api/v1/simulate", json={"preset": "custom", "policies": ["not_a_policy"], "horizon": 4, "n_seeds": 1})
    assert unknown.status_code == 422


def test_api_quick_compare_recommend_and_csv():
    client = TestClient(app)
    response = client.post(
        "/api/v1/compare",
        json={"preset": "custom", "horizon": 12, "n_seeds": 2, "discount": 0.95, "ucb_c": 0.1},
    )
    assert response.status_code == 200
    payload = response.json()
    assert [row["id"] for row in payload["policies"]] == [
        "fixed_rotation",
        "random",
        "greedy",
        "ucb1",
        "discounted_ucb",
        "discounted_thompson",
    ]
    assert payload["parameters"]["seeds"] == [0, 1]
    csv_response = client.post(
        "/api/v1/compare?format=csv",
        json={"preset": "custom", "horizon": 8, "n_seeds": 1},
    )
    assert csv_response.status_code == 200
    assert "text/csv" in csv_response.headers["content-type"]
    assert "discounted_thompson" in csv_response.text
    recommendation = client.post(
        "/api/v1/recommend",
        json={"policy": "discounted_ucb", "horizon": 16, "seed": 0, "discount": 0.95, "ucb_c": 0.1},
    )
    assert recommendation.status_code == 200
    rec = recommendation.json()
    assert rec["recommended_arm_id"]
    assert rec["explanation"]
    assert rec["policy_name"] in rec["explanation"] or rec["recommended_arm_id"]
    assert any(arm["name"] in rec["explanation"] for arm in rec["arms"])
