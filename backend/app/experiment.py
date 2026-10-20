"""Experiment runner. Results are computed; nothing is copied from the report tables."""

from __future__ import annotations

import time
from datetime import date

import numpy as np

from app.config import (
    ARMS,
    BLOOD_TYPES,
    LIMITATIONS,
    O_NEGATIVE_BOOSTED_ARMS,
    REWARD_SCALE,
    TS_PRIOR_MEAN,
)
from app.environment import (
    N_ARMS,
    N_TYPES,
    PotentialOutcomes,
    expected_objective,
    expected_reward,
    expected_turnout,
    expected_units,
    initial_stock,
    objective_reward,
    raw_reward,
    scale_reward,
    seasonal_multiplier,
    shortage_vector,
    step_stock,
    target_stock,
    turnout_probability,
)
from app.policies import POLICY_ORDER, Policy, make_policy


def _std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    return float(np.std(np.asarray(values, dtype=np.float64), ddof=1))


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return float(np.mean(np.asarray(values, dtype=np.float64)))


def run_episode(
    policy: Policy,
    outcomes: PotentialOutcomes,
    rng: np.random.Generator,
    initial_fraction: float,
    wastage: float,
    objective: str = "weighted",
    opening_stock: np.ndarray | None = None,
    opening_target: np.ndarray | None = None,
) -> dict:
    target = (
        target_stock(outcomes.weekly_demand)
        if opening_target is None
        else np.asarray(opening_target, dtype=np.float64).copy()
    )
    stock = (
        initial_stock(outcomes.weekly_demand, initial_fraction)
        if opening_stock is None
        else np.asarray(opening_stock, dtype=np.float64).copy()
    )
    cumulative = 0.0
    weighted = 0.0
    units = np.zeros(N_TYPES, dtype=np.float64)
    demand_total = np.zeros(N_TYPES, dtype=np.float64)
    arm_counts = np.zeros(N_ARMS, dtype=np.int64)
    reward_curve = np.zeros(outcomes.horizon, dtype=np.float64)
    stock_curve = np.zeros((outcomes.horizon, N_TYPES), dtype=np.float64)
    shortage_curve = np.zeros((outcomes.horizon, N_TYPES), dtype=np.float64)
    choices: list[int] = []
    wasted_total = np.zeros(N_TYPES, dtype=np.float64)

    for t in range(outcomes.horizon):
        shortage = shortage_vector(stock, target)
        arm = policy.select(t, rng)
        collected = outcomes.collected[t, arm]
        reward = objective_reward(collected, shortage, objective)
        standard = raw_reward(collected, shortage)
        policy.update(arm, scale_reward(reward))
        demand = outcomes.demand[t]
        wasted_total += wastage * stock
        stock = step_stock(stock, collected, demand, wastage=wastage)
        cumulative += reward
        weighted += standard
        units += collected
        demand_total += demand
        arm_counts[arm] += 1
        choices.append(arm)
        reward_curve[t] = cumulative
        stock_curve[t] = stock
        shortage_curve[t] = shortage_vector(stock, target)

    return {
        "cumulative_reward": cumulative,
        "cumulative_weighted": weighted,
        "total_units": float(units.sum()),
        "o_negative_units": float(units[0]),
        "units": units,
        "demand_total": demand_total,
        "wasted_total": wasted_total,
        "arm_counts": arm_counts,
        "reward_curve": reward_curve,
        "stock_curve": stock_curve,
        "shortage_curve": shortage_curve,
        "final_stock": stock.copy(),
        "final_shortage": shortage_vector(stock, target),
        "target": target,
        "choices": choices,
        "policy_state": policy,
    }


def _series(curve: np.ndarray) -> dict[str, list[float]]:
    return {
        BLOOD_TYPES[k]: [float(v) for v in curve[:, k]]
        for k in range(N_TYPES)
    }


def _arm_map(values: np.ndarray) -> dict[str, float]:
    return {ARMS[i]["id"]: float(values[i]) for i in range(N_ARMS)}


def summarise_policy(policy_id: str, episodes: list[dict], horizon: int) -> dict:
    rewards = [ep["cumulative_reward"] for ep in episodes]
    totals = [ep["total_units"] for ep in episodes]
    o_neg = [ep["o_negative_units"] for ep in episodes]
    unit_stack = np.stack([ep["units"] for ep in episodes])
    arm_stack = np.stack([ep["arm_counts"] for ep in episodes]).astype(np.float64)
    reward_curves = np.stack([ep["reward_curve"] for ep in episodes])
    stock_curves = np.stack([ep["stock_curve"] for ep in episodes])
    shortage_curves = np.stack([ep["shortage_curve"] for ep in episodes])
    final_stock = np.mean(np.stack([ep["final_stock"] for ep in episodes]), axis=0)
    final_shortage = np.mean(np.stack([ep["final_shortage"] for ep in episodes]), axis=0)
    demand_mean = np.mean(np.stack([ep["demand_total"] for ep in episodes]), axis=0) / horizon
    target = episodes[0]["target"]
    mean_arm_counts = arm_stack.mean(axis=0)

    return {
        "id": policy_id,
        "name": episodes[0]["policy_state"].name,
        "mean_cumulative_reward": _mean(rewards),
        "std_cumulative_reward": _std(rewards),
        "min_cumulative_reward": float(min(rewards)),
        "max_cumulative_reward": float(max(rewards)),
        "improvement_vs_fixed": None,
        "mean_total_units": _mean(totals),
        "std_total_units": _std(totals),
        "mean_o_negative_units": _mean(o_neg),
        "blood_type_units": {
            BLOOD_TYPES[k]: float(unit_stack[:, k].mean()) for k in range(N_TYPES)
        },
        "arm_frequency": _arm_map(mean_arm_counts / horizon),
        "arm_counts_mean": _arm_map(mean_arm_counts),
        "seed_cumulative_rewards": [float(v) for v in rewards],
        "seed_total_units": [float(v) for v in totals],
        "seed_o_negative_units": [float(v) for v in o_neg],
        "curve": {
            "week": list(range(1, horizon + 1)),
            "reward_mean": [float(v) for v in reward_curves.mean(axis=0)],
            "reward_std": [
                float(v)
                for v in (
                    reward_curves.std(axis=0, ddof=1)
                    if len(episodes) > 1
                    else np.zeros(horizon)
                )
            ],
            "stock": _series(stock_curves.mean(axis=0)),
            "shortage": _series(shortage_curves.mean(axis=0)),
        },
        "final_stock_mean": {
            BLOOD_TYPES[k]: float(final_stock[k]) for k in range(N_TYPES)
        },
        "final_shortage_mean": {
            BLOOD_TYPES[k]: float(final_shortage[k]) for k in range(N_TYPES)
        },
        "target_stock": {BLOOD_TYPES[k]: float(target[k]) for k in range(N_TYPES)},
        "mean_weekly_demand": {
            BLOOD_TYPES[k]: float(demand_mean[k]) for k in range(N_TYPES)
        },
        "mean_weekly_collected": {
            BLOOD_TYPES[k]: float(unit_stack[:, k].mean() / horizon) for k in range(N_TYPES)
        },
    }


def run_comparison(
    horizon: int,
    seeds: list[int],
    policies: list[str],
    initial_stock_fraction: float,
    weekly_demand: float,
    discount: float,
    ucb_c: float,
    wastage: float,
    preset: str,
) -> dict:
    started = time.perf_counter()
    by_policy: dict[str, list[dict]] = {pid: [] for pid in policies}
    for seed in seeds:
        outcomes = PotentialOutcomes(seed=seed, horizon=horizon, weekly_demand=weekly_demand)
        for index, policy_id in enumerate(policies):
            policy = make_policy(policy_id, gamma=discount, ucb_c=ucb_c)
            rng = np.random.default_rng((int(seed), index, 17))
            episode = run_episode(
                policy,
                outcomes,
                rng,
                initial_fraction=initial_stock_fraction,
                wastage=wastage,
            )
            by_policy[policy_id].append(episode)

    summaries = [summarise_policy(pid, by_policy[pid], horizon) for pid in policies]
    fixed = next((row for row in summaries if row["id"] == "fixed_rotation"), None)
    baseline = fixed["mean_cumulative_reward"] if fixed else None
    for row in summaries:
        if baseline is None or abs(baseline) < 1e-9:
            row["improvement_vs_fixed"] = None if row["id"] != "fixed_rotation" else 0.0
        else:
            row["improvement_vs_fixed"] = (
                (row["mean_cumulative_reward"] - baseline) / baseline * 100.0
            )
        if row["id"] == "fixed_rotation":
            row["improvement_vs_fixed"] = 0.0

    runtime_ms = (time.perf_counter() - started) * 1000.0
    return {
        "parameters": {
            "horizon": horizon,
            "seeds": list(seeds),
            "n_seeds": len(seeds),
            "discount": discount,
            "ucb_c": ucb_c,
            "initial_stock_fraction": initial_stock_fraction,
            "weekly_demand": weekly_demand,
            "wastage": wastage,
            "reward_scale": REWARD_SCALE,
            "preset": preset,
            "policies": list(policies),
        },
        "runtime_ms": runtime_ms,
        "policies": summaries,
        "limitations": LIMITATIONS,
        "reward_note": (
            "mean_cumulative_reward is the raw shortage-weighted sum. "
            f"Policies learn on that reward divided by {REWARD_SCALE:g}."
        ),
    }


def run_sensitivity(
    horizon: int,
    seeds: list[int],
    discount_grid: list[float],
    ucb_c: float,
    initial_stock_fraction: float,
    weekly_demand: float,
    wastage: float,
) -> dict:
    started = time.perf_counter()
    rows = []
    tracked = ("discounted_ucb", "discounted_thompson")
    for gamma in discount_grid:
        comparison = run_comparison(
            horizon=horizon,
            seeds=seeds,
            policies=["fixed_rotation", *tracked],
            initial_stock_fraction=initial_stock_fraction,
            weekly_demand=weekly_demand,
            discount=gamma,
            ucb_c=ucb_c,
            wastage=wastage,
            preset="sensitivity",
        )
        for row in comparison["policies"]:
            if row["id"] == "fixed_rotation" and gamma != discount_grid[0]:
                continue
            rows.append(
                {
                    "discount": None if row["id"] == "fixed_rotation" else gamma,
                    "policy": row["id"],
                    "name": row["name"],
                    "mean_cumulative_reward": row["mean_cumulative_reward"],
                    "std_cumulative_reward": row["std_cumulative_reward"],
                    "improvement_vs_fixed": row["improvement_vs_fixed"],
                    "mean_o_negative_units": row["mean_o_negative_units"],
                    "mean_total_units": row["mean_total_units"],
                }
            )
    return {
        "horizon": horizon,
        "seeds": list(seeds),
        "discount_grid": list(discount_grid),
        "ucb_c": ucb_c,
        "rows": rows,
        "runtime_ms": (time.perf_counter() - started) * 1000.0,
        "note": (
            "Fixed rotation ignores the discount. At gamma = 1, discounted UCB "
            "uses the same index as UCB1. Improvement is against fixed rotation "
            "on the same seeds and potential outcomes."
        ),
    }


def _other(values: np.ndarray, chosen: int, allowed: np.ndarray) -> int | None:
    masked = np.asarray(values, dtype=np.float64).copy()
    masked = np.where(np.isnan(masked), -np.inf, masked)
    masked[~np.asarray(allowed, dtype=bool)] = -np.inf
    masked[int(chosen)] = -np.inf
    if not np.any(np.isfinite(masked)):
        return None
    return int(np.argmax(masked))


def explain_decision(policy: Policy, names: list[str]) -> str:
    decision = policy.last_decision
    arm = int(decision["arm"])
    name = names[arm]
    scale = REWARD_SCALE
    allowed_count = int(np.count_nonzero(policy.allowed))
    if policy.kind == "fixed_rotation":
        cycle = int(decision.get("cycle", allowed_count or N_ARMS))
        position = int(decision["t"]) % cycle
        return (
            f"Fixed rotation selects {name} because week index {decision['t']} falls at position {position} "
            f"in a list of {cycle} allowed drives. Observed rewards are ignored. This is a schedule rule, not a prediction of turnout."
        )
    if policy.kind == "random":
        n_allowed = int(decision.get("n_allowed", allowed_count))
        return (
            f"Random selected {name} from a uniform draw over the {n_allowed} allowed drives. "
            "The draw is seeded. It is not an estimate of which drive will collect more blood."
        )
    if policy.kind == "greedy":
        q = decision["q"]
        if decision["phase"] == "explore":
            return (
                f"Greedy selected {name} because that drive has not been tried yet. "
                "Greedy plays every allowed drive once, then stays with the highest mean."
            )
        second = _other(q, arm, policy.allowed)
        follow = (
            f" Next best is {names[second]} at {q[second]:.4f}."
            if second is not None
            else " No other allowed drive is available."
        )
        return (
            f"Greedy selected {name} because its undiscounted mean scaled reward is {q[arm]:.4f}, "
            f"the highest after every allowed drive was tried.{follow} "
            f"Means use the learning score / {scale:g}. This is a historical average, not a guarantee for the next drive."
        )
    if policy.kind in {"ucb1", "discounted_ucb"}:
        label = "Discounted UCB" if policy.kind == "discounted_ucb" else "UCB1"
        if decision["phase"] == "explore":
            return (
                f"{label} selected {name} because the drive has not been observed. "
                "Unvisited allowed drives are tried before the confidence bonus is used."
            )
        score = decision["score"]
        q = decision["q"]
        bonus = decision["bonus"]
        second = _other(score, arm, policy.allowed)
        follow = (
            f" Next best is {names[second]} at index {score[second]:.4f}."
            if second is not None
            else " No other allowed drive is available."
        )
        memory = (
            f" Counts and reward sums are discounted by gamma = {policy.gamma:g}."
            if policy.kind == "discounted_ucb"
            else " Counts are undiscounted, so early weeks keep full weight."
        )
        return (
            f"{label} selected {name}. Index {score[arm]:.4f} = scaled mean {q[arm]:.4f} "
            f"+ bonus {bonus[arm]:.4f} (c = {policy.ucb_c:g}, count = {policy.count[arm]:.3f})."
            f"{follow}"
            f"{memory} The index uses the learning score / {scale:g}. It is not a promised collection."
        )
    mu = decision["mu"]
    sigma = decision["sigma"]
    samples = decision["samples"]
    second = _other(samples, arm, policy.allowed)
    follow = (
        f" Next sample was {names[second]} at {samples[second]:.4f}."
        if second is not None
        else " No other allowed drive was drawn."
    )
    return (
        f"Discounted Thompson Sampling selected {name} because a draw from "
        f"N({mu[arm]:.4f}, {sigma[arm]:.4f}²) equalled {samples[arm]:.4f}, "
        f"the largest draw among the allowed drives.{follow} "
        f"The posterior mean is (discounted reward sum + {TS_PRIOR_MEAN:g}) / (discounted count + 1), "
        f"with prior mean 0.5 and sigma0 = 0.1, on the learning score / {scale:g}, gamma = {policy.gamma:g}. "
        "A different seed can select a different arm. This is not a guaranteed turnout."
    )


def recommend(
    policy_id: str,
    horizon: int,
    seed: int,
    initial_stock_fraction: float,
    weekly_demand: float,
    discount: float,
    ucb_c: float,
    wastage: float,
) -> dict:
    """Learn for `horizon` weeks, then choose the next arm without updating."""
    if horizon < 1:
        raise ValueError("horizon must be at least 1")
    outcomes = PotentialOutcomes(seed=seed, horizon=horizon, weekly_demand=weekly_demand)
    policy = make_policy(policy_id, gamma=discount, ucb_c=ucb_c)
    rng = np.random.default_rng((int(seed), 0, 17))
    episode = run_episode(
        policy,
        outcomes,
        rng,
        initial_fraction=initial_stock_fraction,
        wastage=wastage,
    )
    decision_index = horizon  # next week, 0-based
    decision_rng = np.random.default_rng((int(seed), 1, 91))
    chosen = policy.select(decision_index, decision_rng)
    names = [arm["name"] for arm in ARMS]
    counts = episode["arm_counts"]
    frequency = counts / horizon
    shortage = episode["final_shortage"]
    stock = episode["final_stock"]
    target = episode["target"]
    q = policy.q_values()
    rows = []
    for i, arm in enumerate(ARMS):
        probability = turnout_probability(i, decision_index)
        rows.append(
            {
                "id": arm["id"],
                "name": arm["name"],
                "tier": arm["tier"],
                "pool": arm["pool"],
                "pattern": arm["pattern"],
                "selected": i == chosen,
                "seasonal_multiplier": seasonal_multiplier(i, decision_index),
                "turnout_probability": probability,
                "expected_turnout": expected_turnout(i, decision_index),
                "expected_reward": expected_reward(i, decision_index, shortage),
                "selection_frequency": float(frequency[i]),
                "scaled_mean": float(q[i]) if policy.count[i] > 0 else None,
                "count": float(policy.count[i]),
                "boosted_o_negative": arm["id"] in O_NEGATIVE_BOOSTED_ARMS,
            }
        )
    decision = policy.last_decision
    if policy.kind in {"ucb1", "discounted_ucb"}:
        bonus = decision.get("bonus")
        score = decision.get("score")
        for i, row in enumerate(rows):
            row["bonus"] = None if bonus is None or not np.isfinite(bonus[i]) else float(bonus[i])
            row["index"] = None if score is None or not np.isfinite(score[i]) else float(score[i])
            row["uncertainty"] = row["bonus"]
    elif policy.kind == "discounted_thompson":
        for i, row in enumerate(rows):
            row["posterior_mean"] = float(decision["mu"][i])
            row["posterior_std"] = float(decision["sigma"][i])
            row["sample"] = float(decision["samples"][i])
            row["uncertainty"] = float(decision["sigma"][i])
    else:
        for row in rows:
            row["uncertainty"] = None if row["count"] <= 0 else float(1.0 / np.sqrt(row["count"]))

    return {
        "policy": policy_id,
        "policy_name": policy.name,
        "seed": seed,
        "history_weeks": horizon,
        "decision_week": decision_index + 1,
        "recommended_arm_id": ARMS[chosen]["id"],
        "explanation": explain_decision(policy, names),
        "arms": rows,
        "stock": {BLOOD_TYPES[k]: float(stock[k]) for k in range(N_TYPES)},
        "shortage": {BLOOD_TYPES[k]: float(shortage[k]) for k in range(N_TYPES)},
        "target_stock": {BLOOD_TYPES[k]: float(target[k]) for k in range(N_TYPES)},
        "reward_scale": REWARD_SCALE,
        "note": (
            "Expected turnout and expected reward are mean-field calculations from the current "
            "shortage and the seasonal probability. They are not the random outcome of the next drive."
        ),
    }


def default_policy_ids() -> list[str]:
    return list(POLICY_ORDER)


_SLOTS = {
    "campus_weekday": "Weekday, on campus",
    "campus_weekend": "Weekend, on campus",
    "corporate_lunch": "Lunchtime, at a workplace",
    "corporate_weekend": "Weekend, at a workplace",
    "community_centre": "Community centre",
    "mall_weekend": "Weekend, at a mall",
    "hospital_camp": "Hospital camp",
    "tech_park_evening": "Evening, at a tech park",
}

_OBJECTIVES = {
    "weighted": (
        "Balance volume and shortages",
        "Every collected unit counts. Scarce types, and O-negative, count more. This is the standard score.",
    ),
    "shortage": (
        "Fill the biggest gaps",
        "A unit counts only when that blood type is still below its target. Types already at target add nothing.",
    ),
    "o_negative": (
        "Collect more O-negative",
        "The algorithm learns only from O-negative units. Those units count more when O-negative is below target.",
    ),
}


def _typed(values: np.ndarray) -> dict[str, float]:
    return {BLOOD_TYPES[k]: float(values[k]) for k in range(N_TYPES)}


def _vector(levels: dict[str, float]) -> np.ndarray:
    return np.array([float(levels[name]) for name in BLOOD_TYPES], dtype=np.float64)


def _allow(policy: Policy, arm_ids: list[str]) -> np.ndarray:
    ids = [arm["id"] for arm in ARMS]
    mask = np.zeros(N_ARMS, dtype=bool)
    for arm_id in arm_ids:
        mask[ids.index(arm_id)] = True
    policy.allowed = mask
    return mask


def _plain_reason(policy: Policy, names: list[str]) -> str:
    decision = policy.last_decision
    name = names[int(decision["arm"])]
    kind = policy.kind
    if kind == "fixed_rotation":
        return (
            f"{name} is next in the repeating list of drives you allowed. "
            "This rule does not look at how the earlier weeks turned out."
        )
    if kind == "random":
        return (
            f"{name} was drawn at random from the drives you allowed. "
            "A random pick is not a judgment about which site will collect more blood."
        )
    if kind == "greedy" and decision.get("phase") == "explore":
        return (
            f"{name} has not been tried yet in the simulation. "
            "Greedy tries each allowed drive once, then stays with the best average."
        )
    if kind == "greedy":
        return f"{name} had the best average score among the drives you allowed."
    if kind in {"ucb1", "discounted_ucb"} and decision.get("phase") == "explore":
        return (
            f"{name} has not been tried enough yet, so the algorithm tries it before trusting the averages."
        )
    if kind in {"ucb1", "discounted_ucb"}:
        return (
            f"{name} has the highest score among the drives you allowed. "
            "The score mixes how well a drive did with how little it has been tried."
        )
    return (
        f"{name} won a draw based on what the simulation has learned. "
        "Another run can pick a different drive. This is not a promise of turnout."
    )


def _settings_note(policy_id: str, discount: float, ucb_c: float) -> list[str]:
    notes = [
        "Seed 0 is fixed, so the same inputs produce the same simulated run.",
        "About 2% of stock already on the shelf is treated as wasted each week. That rate is a configured assumption.",
        "Weekly demand is split across blood types with a fixed synthetic share. Your targets are separate from that split.",
    ]
    if policy_id in {"discounted_ucb", "discounted_thompson"}:
        notes.append(
            f"Older weeks fade by {discount:g}. A value of 1 would keep every week at full weight."
        )
    else:
        notes.append("This algorithm does not fade older weeks. The fade setting was received and not used.")
    if policy_id in {"ucb1", "discounted_ucb"}:
        notes.append(
            f"Less-used drives get an extra push of {ucb_c:g}. A higher number means more tries of drives with little history."
        )
    else:
        notes.append("This algorithm does not use the extra push for less-used drives. That setting was received and not used.")
    return notes


def _run_plan_episode(
    policy_id: str,
    outcomes: PotentialOutcomes,
    arm_ids: list[str],
    stock: np.ndarray,
    target: np.ndarray,
    objective: str,
    discount: float,
    ucb_c: float,
    wastage: float,
    seed: int,
) -> tuple[Policy, dict, int]:
    policy = make_policy(policy_id, gamma=discount, ucb_c=ucb_c)
    _allow(policy, arm_ids)
    rng = np.random.default_rng((int(seed), POLICY_ORDER.index(policy_id), 17))
    episode = run_episode(
        policy,
        outcomes,
        rng,
        initial_fraction=0.6,
        wastage=wastage,
        objective=objective,
        opening_stock=stock,
        opening_target=target,
    )
    decision_rng = np.random.default_rng((int(seed), POLICY_ORDER.index(policy_id), 91))
    chosen = policy.select(outcomes.horizon, decision_rng)
    return policy, episode, chosen


def _decision_rows(
    policy: Policy,
    chosen: int,
    decision_index: int,
    origin_week: int,
    shortage: np.ndarray,
    objective: str,
    counts: np.ndarray,
    horizon: int,
) -> list[dict]:
    rows = []
    for index, arm in enumerate(ARMS):
        if not policy.allowed[index]:
            continue
        units = expected_units(index, decision_index, origin_week)
        rows.append(
            {
                "id": arm["id"],
                "name": arm["name"],
                "slot": _SLOTS[arm["id"]],
                "selected": index == chosen,
                "expected_donors": expected_turnout(index, decision_index, origin_week),
                "expected_units": float(units.sum()),
                "collection_by_type": _typed(units),
                "objective_score": expected_objective(
                    index, decision_index, shortage, objective, origin_week
                ),
                "shortage_weighted_reward": expected_reward(
                    index, decision_index, shortage, origin_week
                ),
                "times_chosen_in_simulation": int(counts[index]),
                "share_of_simulated_weeks": float(counts[index] / horizon) if horizon else 0.0,
            }
        )
    rows.sort(key=lambda row: (-row["objective_score"], row["name"]))
    for rank, row in enumerate(rows, start=1):
        row["rank"] = rank
    return rows


def plan_drive(
    facility_name: str,
    planning_date: str,
    horizon: int,
    weekly_demand: float,
    stock: dict[str, float],
    target: dict[str, float],
    arm_ids: list[str],
    policy_id: str,
    objective: str,
    discount: float,
    ucb_c: float,
    seed: int,
    wastage: float,
) -> dict:
    """Learn on the user's stock and targets, then score the next allowed drive."""
    origin = date.fromisoformat(planning_date).isocalendar().week
    if origin > 52:
        origin = 52
    opening = _vector(stock)
    targets = _vector(target)
    outcomes = PotentialOutcomes(
        seed=seed,
        horizon=horizon,
        weekly_demand=weekly_demand,
        origin_week=origin,
    )
    policy, episode, chosen = _run_plan_episode(
        policy_id,
        outcomes,
        arm_ids,
        opening,
        targets,
        objective,
        discount,
        ucb_c,
        wastage,
        seed,
    )
    names = [arm["name"] for arm in ARMS]
    shortage = episode["final_shortage"]
    decision_index = horizon
    rows = _decision_rows(
        policy,
        chosen,
        decision_index,
        origin,
        shortage,
        objective,
        episode["arm_counts"],
        horizon,
    )
    recommended = next(row for row in rows if row["selected"])
    label, note = _OBJECTIVES[objective]
    uses_discount = policy_id in {"discounted_ucb", "discounted_thompson"}
    uses_bonus = policy_id in {"ucb1", "discounted_ucb"}
    return {
        "facility_name": facility_name.strip(),
        "planning_date": planning_date,
        "calendar_week": origin,
        "decision_week_index": decision_index + 1,
        "date_effect": (
            "Your date sets the time of year for the first simulated week: campus breaks, "
            "festivals, and corporate campaigns. The recommendation is for the week after "
            "this plan. The community-centre slowdown and the tech-park opening follow the "
            "number of weeks in the plan, not the calendar date."
        ),
        "horizon_weeks": horizon,
        "weekly_demand": float(weekly_demand),
        "policy": policy_id,
        "policy_name": policy.name,
        "objective": objective,
        "objective_label": label,
        "objective_note": note,
        "recommended": {
            "id": recommended["id"],
            "name": recommended["name"],
            "slot": recommended["slot"],
        },
        "plain_reason": _plain_reason(policy, names),
        "technical_explanation": explain_decision(policy, names),
        "estimates": {
            "donors": recommended["expected_donors"],
            "collection_units": recommended["expected_units"],
            "by_type": recommended["collection_by_type"],
            "objective_score": recommended["objective_score"],
            "shortage_weighted_reward": recommended["shortage_weighted_reward"],
            "label": "Simulated estimate for the recommended drive. Not a count of real donors and not a clinical forecast.",
        },
        "simulated_history": {
            "weeks": horizon,
            "total_units": float(episode["total_units"]),
            "o_negative_units": float(episode["o_negative_units"]),
            "objective_score": float(episode["cumulative_reward"]),
            "shortage_weighted_reward": float(episode["cumulative_weighted"]),
            "units_by_type": _typed(episode["units"]),
            "label": "What the simulator collected during the planning weeks. Not a record of drives that already happened.",
        },
        "inventory": {
            "opening_stock": _typed(opening),
            "target_stock": _typed(targets),
            "final_stock": _typed(episode["final_stock"]),
            "shortage_after": _typed(shortage),
        },
        "alternatives": rows,
        "assumptions": _settings_note(policy_id, discount, ucb_c),
        "settings": {
            "seed": seed,
            "discount": discount,
            "discount_used": uses_discount,
            "ucb_c": ucb_c,
            "ucb_c_used": uses_bonus,
            "wastage": wastage,
        },
        "limitations": [
            "These figures come from a simulator. They are not observed donor turnout.",
            "The same inputs always use seed 0 here, so this is one simulated path, not a range of possible turnouts.",
            "Blood-type mix and seasonal swings are configured assumptions, not measurements from your donors.",
            "The historical donor file used for loyalty rates has no blood types, sites, or hospital stock.",
            "This tool is not clinically validated. Use it beside local knowledge, not instead of it.",
            *LIMITATIONS,
        ],
        "inputs": {
            "facility_name": facility_name.strip(),
            "planning_date": planning_date,
            "horizon_weeks": horizon,
            "weekly_demand": float(weekly_demand),
            "stock": _typed(opening),
            "target": _typed(targets),
            "arms": list(arm_ids),
            "policy": policy_id,
            "objective": objective,
        },
    }


def compare_plan(
    planning_date: str,
    horizon: int,
    weekly_demand: float,
    stock: dict[str, float],
    target: dict[str, float],
    arm_ids: list[str],
    objective: str,
    discount: float,
    ucb_c: float,
    seed: int,
    wastage: float,
    selected_policy: str,
) -> dict:
    """Run all six algorithms on the same simulated weeks and the user's inventory."""
    origin = date.fromisoformat(planning_date).isocalendar().week
    if origin > 52:
        origin = 52
    opening = _vector(stock)
    targets = _vector(target)
    outcomes = PotentialOutcomes(
        seed=seed,
        horizon=horizon,
        weekly_demand=weekly_demand,
        origin_week=origin,
    )
    rows = []
    for policy_id in POLICY_ORDER:
        policy, episode, chosen = _run_plan_episode(
            policy_id,
            outcomes,
            arm_ids,
            opening,
            targets,
            objective,
            discount,
            ucb_c,
            wastage,
            seed,
        )
        rows.append(
            {
                "id": policy_id,
                "name": policy.name,
                "selected_by_user": policy_id == selected_policy,
                "recommended_arm_id": ARMS[chosen]["id"],
                "recommended_name": ARMS[chosen]["name"],
                "recommended_slot": _SLOTS[ARMS[chosen]["id"]],
                "simulated_objective_score": float(episode["cumulative_reward"]),
                "simulated_shortage_weighted_reward": float(episode["cumulative_weighted"]),
                "simulated_units": float(episode["total_units"]),
                "simulated_o_negative_units": float(episode["o_negative_units"]),
            }
        )
    rows.sort(key=lambda row: -row["simulated_objective_score"])
    return {
        "objective": objective,
        "objective_label": _OBJECTIVES[objective][0],
        "rows": rows,
        "note": (
            "Each algorithm saw the same simulated weeks, the same stock, and the same targets. "
            "Scores are simulated totals, not a forecast of real collections."
        ),
    }
