"""Manager-facing drive advice.

The learning policies are unchanged. This module scores every eligible drive
against the inventory the user entered, then explains that score in plain language.

Each estimated donation is one unit. The total is split across blood types,
so "donors" and "units" are the same count and are not shown as two results.

The ranking uses the current gap between stock and target. It does not wait
until a long simulation has emptied the shelf, because that would make every
blood type look equally urgent.
"""

from __future__ import annotations

import math
from datetime import date

import numpy as np

from app.config import ARMS, BLOOD_TYPES, DEFAULT_WASTAGE, DEMAND_SHARE, PRIORITY
from app.environment import (
    N_TYPES,
    PotentialOutcomes,
    expected_turnout,
    expected_units,
    objective_reward,
    shortage_vector,
    step_stock,
)
from app.experiment import run_episode
from app.policies import POLICY_ORDER, make_policy

LABELS = {
    "O-": "O-negative",
    "O+": "O-positive",
    "A-": "A-negative",
    "A+": "A-positive",
    "B-": "B-negative",
    "B+": "B-positive",
    "AB-": "AB-negative",
    "AB+": "AB-positive",
}

SLOTS = {
    "campus_weekday": "Weekday, on a campus",
    "campus_weekend": "Weekend, on a campus",
    "corporate_lunch": "Lunchtime, at a workplace",
    "corporate_weekend": "Weekend, at a workplace",
    "community_centre": "Community centre",
    "mall_weekend": "Weekend, at a mall",
    "hospital_camp": "Hospital camp",
    "tech_park_evening": "Evening, at a tech park",
}

DISPLAY_ORDER = ("O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-")

OBJECTIVE_NOTES = {
    "shortage": "Drives are ordered by how well their estimated collections match blood types that are below target. Types you already have enough of do not raise the score. O-negative counts more than common types.",
    "weighted": "Drives are ordered with the research score. Every estimated unit counts a little, and units of blood you are short of count more.",
    "o_negative": "Drives are ordered only by estimated O-negative units, with a higher score when O-negative is below target.",
}

# A second drive within 5% of the leader is described as similar.
TIE_RATIO = 0.05


def demo_levels(weekly_demand: float = 90) -> tuple[dict[str, float], dict[str, float]]:
    """Sample shelf and targets. Not a hospital record."""
    target = {
        name: float(round(2 * weekly_demand * DEMAND_SHARE[name]))
        for name in BLOOD_TYPES
    }
    stock = {name: float(round(0.6 * target[name])) for name in BLOOD_TYPES}
    return stock, target


def shortage_units(stock: np.ndarray, target: np.ndarray) -> np.ndarray:
    return np.maximum(target - stock, 0.0)


def shortage_percentage(stock: np.ndarray, target: np.ndarray) -> np.ndarray:
    units = shortage_units(stock, target)
    out = np.zeros(N_TYPES, dtype=np.float64)
    np.divide(units, target, out=out, where=target > 0)
    return out


def stock_status(stock: float, target: float) -> str:
    if target <= 0:
        return "No target"
    if stock >= target:
        return "Adequate"
    if stock >= 0.5 * target:
        return "Low"
    return "Critical"


def _vector(levels: dict[str, float]) -> np.ndarray:
    return np.array([float(levels[name]) for name in BLOOD_TYPES], dtype=np.float64)


def _typed(values: np.ndarray) -> dict[str, float]:
    return {BLOOD_TYPES[i]: float(values[i]) for i in range(N_TYPES)}


def _calendar_week(day: date | None) -> int:
    week = (day or date.today()).isocalendar().week
    return 52 if week > 52 else int(week)


def _check(levels: dict[str, float], label: str) -> dict[str, float]:
    missing = [name for name in BLOOD_TYPES if name not in levels]
    extra = [name for name in levels if name not in BLOOD_TYPES]
    if missing or extra:
        raise ValueError(f"{label} must include all eight blood types.")
    cleaned = {}
    for name in BLOOD_TYPES:
        try:
            amount = float(levels[name])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Enter a number for {LABELS[name]} {label.lower()}.") from exc
        if not math.isfinite(amount) or amount < 0:
            raise ValueError(f"{LABELS[name]} {label.lower()} cannot be negative.")
        if amount > 1_000_000:
            raise ValueError(f"{LABELS[name]} {label.lower()} must be 1,000,000 or less.")
        cleaned[name] = amount
    return cleaned


def _allow_mask(arm_ids: list[str]) -> np.ndarray:
    known = {arm["id"] for arm in ARMS}
    if not arm_ids:
        raise ValueError("Choose at least one drive.")
    unknown = [arm_id for arm_id in arm_ids if arm_id not in known]
    if unknown:
        raise ValueError("One of the selected drives is not recognised.")
    if len(set(arm_ids)) != len(arm_ids):
        raise ValueError("Each drive can be selected only once.")
    mask = np.zeros(len(ARMS), dtype=bool)
    index = {arm["id"]: i for i, arm in enumerate(ARMS)}
    for arm_id in arm_ids:
        mask[index[arm_id]] = True
    return mask


def inventory_rows(stock: dict[str, float], target: dict[str, float]) -> list[dict]:
    stock_vec = _vector(_check(stock, "Stock"))
    target_vec = _vector(_check(target, "Target"))
    gaps = shortage_units(stock_vec, target_vec)
    percents = shortage_percentage(stock_vec, target_vec)
    rows = []
    for name in DISPLAY_ORDER:
        index = BLOOD_TYPES.index(name)
        rows.append(
            {
                "id": name,
                "blood_type": LABELS[name],
                "current_stock": float(stock_vec[index]),
                "target_stock": float(target_vec[index]),
                "units_short": float(gaps[index]),
                "shortage_percentage": float(percents[index]),
                "status": stock_status(float(stock_vec[index]), float(target_vec[index])),
            }
        )
    return rows


def parse_inventory_csv(text: str) -> dict:
    """Read a stock file. Nothing is applied until the caller accepts it."""
    aliases = {}
    for name, label in LABELS.items():
        keys = {
            name.lower(),
            label.lower(),
            label.lower().replace(" ", ""),
            label.lower().replace("-", "").replace(" ", ""),
            name.lower().replace("+", "positive").replace("-", "negative"),
        }
        for key in keys:
            aliases[key] = name
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    preview: dict = {"stock": {}, "target": {}, "errors": [], "notes": []}
    if not lines:
        preview["errors"].append("The file is empty.")
        return preview
    header = [cell.strip().lower() for cell in lines[0].split(",")]
    type_at = next((i for i, cell in enumerate(header) if cell in {"blood type", "blood_type", "type", "blood"}), -1)
    stock_at = next((i for i, cell in enumerate(header) if cell in {"stock", "current stock", "current_stock", "current"}), -1)
    target_at = next((i for i, cell in enumerate(header) if cell in {"target", "target stock", "target_stock"}), -1)
    has_header = type_at >= 0 and (stock_at >= 0 or target_at >= 0)
    start = 1 if has_header else 0
    if not has_header:
        preview["notes"].append("No header was found. Columns are read as blood type, current stock, target stock.")
    seen: set[str] = set()
    for line in lines[start:]:
        cells = [cell.strip() for cell in line.split(",")]
        raw = cells[type_at if has_header else 0] if cells else ""
        blood = aliases.get(raw.lower().replace(" ", "").replace("_", ""))
        if blood is None:
            preview["errors"].append(f"“{raw or 'blank'}” is not one of the eight blood types.")
            continue
        if blood in seen:
            preview["errors"].append(f"{LABELS[blood]} appears more than once.")
            continue
        seen.add(blood)
        stock_cell = cells[stock_at] if has_header and stock_at >= 0 and stock_at < len(cells) else (cells[1] if not has_header and len(cells) > 1 else "")
        target_cell = cells[target_at] if has_header and target_at >= 0 and target_at < len(cells) else (cells[2] if not has_header and len(cells) > 2 else "")
        if stock_cell != "":
            try:
                amount = float(stock_cell)
            except ValueError:
                preview["errors"].append(f"{LABELS[blood]} stock must be a number.")
                continue
            if amount < 0:
                preview["errors"].append(f"{LABELS[blood]} stock cannot be negative.")
            else:
                preview["stock"][blood] = amount
        if target_cell != "":
            try:
                amount = float(target_cell)
            except ValueError:
                preview["errors"].append(f"{LABELS[blood]} target must be a number.")
                continue
            if amount < 0:
                preview["errors"].append(f"{LABELS[blood]} target cannot be negative.")
            else:
                preview["target"][blood] = amount
    return preview


def _score_options(
    opening: np.ndarray,
    targets: np.ndarray,
    allowed: np.ndarray,
    objective: str,
    origin_week: int,
) -> list[dict]:
    """Score the coming week from the user's current gaps. Deterministic."""
    fraction = shortage_vector(opening, targets)
    gaps = shortage_units(opening, targets)
    rows = []
    for index, arm in enumerate(ARMS):
        if not allowed[index]:
            continue
        units = expected_units(index, 0, origin_week)
        donations = expected_turnout(index, 0, origin_week)
        gap_units = float(np.minimum(units, gaps).sum())
        short_mask = gaps > 0
        priority_units = float(units[short_mask].sum()) if np.any(short_mask) else 0.0
        helped = int(np.sum((gaps > 0) & (units > 0.05)))
        rows.append(
            {
                "id": arm["id"],
                "name": arm["name"],
                "slot": SLOTS[arm["id"]],
                "estimated_donations": float(donations),
                "estimated_units": float(units.sum()),
                "units_by_type": _typed(units),
                "gap_units": gap_units,
                "priority_units": priority_units,
                "shortages_helped": helped,
                "score": objective_reward(units, fraction, objective),
            }
        )
    rows.sort(key=lambda row: (-row["score"], -row["gap_units"], row["name"]))
    best = rows[0]["score"] if rows else 0.0
    for rank, row in enumerate(rows, start=1):
        row["rank"] = rank
        close = rank > 1 and (
            best == row["score"] or (best > 0 and (best - row["score"]) / best <= TIE_RATIO)
        )
        row["close"] = close
        if rank == 1:
            row["label"] = "Recommended"
        elif close:
            row["label"] = "Similar estimate"
        else:
            row["label"] = ""
    return rows


def _reasons(rows: list[dict], gaps: np.ndarray, objective: str) -> list[str]:
    best = rows[0]
    urgent = sorted(
        ((gaps[i], BLOOD_TYPES[i]) for i in range(N_TYPES) if gaps[i] > 0),
        reverse=True,
    )
    reasons = []
    if urgent:
        parts = [
            f"{LABELS[name]} is {gap:.0f} units below target"
            for gap, name in urgent[:3]
        ]
        reasons.append("Right now, " + ", and ".join(parts) + ".")
    else:
        reasons.append("Every blood type is at or above the target you entered.")
    if len(rows) > 1 and rows[0]["score"] == rows[1]["score"]:
        reasons.append(
            f"{best['name']} and {rows[1]['name']} have the same estimated score. Their performance looks the same under this model, so local knowledge should decide."
        )
    elif len(rows) > 1 and rows[1]["close"]:
        reasons.append(
            f"{best['name']} and {rows[1]['name']} are close. Their estimated performance is similar, so local knowledge should decide between them."
        )
    else:
        reasons.append(
            f"{best['name']} has the strongest estimated match to those needs among the {len(rows)} drives you allowed."
        )
    mix = best["units_by_type"]
    top = sorted(mix.items(), key=lambda item: -item[1])[:3]
    mix_text = ", ".join(f"{amount:.0f} {LABELS[name]}" for name, amount in top if amount >= 0.5)
    reasons.append(
        f"About {best['estimated_donations']:.0f} donations are estimated for this drive. Each donation is one unit, then split by blood type"
        + (f" ({mix_text})." if mix_text else ".")
    )
    if objective == "o_negative":
        reasons.append("The ordering uses O-negative only. Other blood types do not change which drive is recommended.")
    elif objective == "weighted":
        reasons.append("Units of blood you already have enough of still count a little in this setting.")
    else:
        if np.all(gaps > 0):
            reasons.append(
                "Every blood type is below target, so the score follows how many of those missing units this drive is estimated to collect."
            )
        else:
            reasons.append(
                "Units of blood types already at target do not raise the score. The ordering follows the types that are still short."
            )
    return reasons


def _depletion_note(
    opening: np.ndarray,
    collected: np.ndarray,
    demand: np.ndarray,
    wasted: np.ndarray,
    final: np.ndarray,
    horizon: int,
    weekly_demand: float,
    wastage: float,
) -> str:
    emptied = [
        LABELS[BLOOD_TYPES[i]]
        for i in range(N_TYPES)
        if final[i] < 0.5 and (opening[i] + collected[i]) > 0
    ]
    if not emptied:
        return (
            f"After {horizon} simulated weeks, every blood type is still above zero in this path. "
            "That is a projection, not the stock you entered."
        )
    listed = ", ".join(emptied[:4])
    extra = f" and {len(emptied) - 4} more" if len(emptied) > 4 else ""
    return (
        f"In this {horizon}-week path, {listed}{extra} reach zero. "
        f"Weekly patient need is set to {weekly_demand:.0f} units, split across blood types, "
        f"and about {wastage:.0%} of stock already on the shelf is treated as unusable each week. "
        f"Over the path the simulator used about {float(demand.sum()):.0f} units for patients, "
        f"collected about {float(collected.sum()):.0f}, and counted about {float(wasted.sum()):.0f} as unusable. "
        "Need is larger than supply, so the projection hits the bottom. This is not your current stock."
    )


def advise(
    facility_name: str,
    horizon: int,
    weekly_demand: float,
    stock: dict[str, float],
    target: dict[str, float],
    arm_ids: list[str],
    policy_id: str = "discounted_ucb",
    objective: str = "shortage",
    discount: float = 0.95,
    ucb_c: float = 0.1,
    seed: int = 0,
    wastage: float = DEFAULT_WASTAGE,
    on_date: date | None = None,
) -> dict:
    if not 1 <= int(horizon) <= 104:
        raise ValueError("Use a planning length from 1 to 104 weeks.")
    if not 0 <= float(weekly_demand) <= 5000:
        raise ValueError("Weekly demand must be between 0 and 5000.")
    if policy_id not in POLICY_ORDER:
        raise ValueError("Choose one of the six planning methods.")
    if objective not in OBJECTIVE_NOTES:
        raise ValueError("Choose a supported planning goal.")
    opening_map = _check(stock, "Stock")
    target_map = _check(target, "Target")
    allowed = _allow_mask(arm_ids)
    opening = _vector(opening_map)
    targets = _vector(target_map)
    origin = _calendar_week(on_date)
    options = _score_options(opening, targets, allowed, objective, origin)
    if not options:
        raise ValueError("Choose at least one drive.")
    best = options[0]
    gaps = shortage_units(opening, targets)
    demand_mean = float(weekly_demand) * np.array([DEMAND_SHARE[name] for name in BLOOD_TYPES])
    for row in options:
        row["after_one_drive"] = _typed(step_stock(opening, _vector(row["units_by_type"]), demand_mean, wastage=wastage))
    after_drive = _vector(best["after_one_drive"])

    outcomes = PotentialOutcomes(
        seed=int(seed),
        horizon=int(horizon),
        weekly_demand=float(weekly_demand),
        origin_week=origin,
    )
    policy = make_policy(policy_id, gamma=float(discount), ucb_c=float(ucb_c))
    policy.allowed = allowed
    episode = run_episode(
        policy,
        outcomes,
        np.random.default_rng((int(seed), POLICY_ORDER.index(policy_id), 17)),
        initial_fraction=0.6,
        wastage=float(wastage),
        objective=objective,
        opening_stock=opening,
        opening_target=targets,
    )
    learned_index = int(policy.select(int(horizon), np.random.default_rng((int(seed), 91))))
    learned = ARMS[learned_index]
    final = episode["final_stock"]
    collected = episode["units"]
    demand = episode["demand_total"]
    wasted = episode["wasted_total"]
    helped = best["shortages_helped"]
    short_count = int(np.sum(gaps > 0))
    return {
        "facility_name": " ".join(facility_name.split())[:120],
        "objective": objective,
        "objective_note": OBJECTIVE_NOTES[objective],
        "policy_id": policy_id,
        "policy_name": policy.name,
        "calendar_week": origin,
        "recommended": {
            "id": best["id"],
            "name": best["name"],
            "slot": best["slot"],
            "estimated_donations": best["estimated_donations"],
            "estimated_units": best["estimated_units"],
            "priority_units": best["priority_units"],
            "gap_units": best["gap_units"],
            "shortages_helped": helped,
            "shortages_open": short_count,
            "units_by_type": best["units_by_type"],
            "score": best["score"],
        },
        "reasons": _reasons(options, gaps, objective),
        "after_one_drive": _typed(after_drive),
        "options": options,
        "similar": bool(len(options) > 1 and options[1]["close"]),
        "inventory": inventory_rows(opening_map, target_map),
        "projection": {
            "weeks": int(horizon),
            "weekly_demand": float(weekly_demand),
            "wastage": float(wastage),
            "opening_stock": _typed(opening),
            "collected": _typed(collected),
            "patient_use": _typed(demand),
            "unusable": _typed(wasted),
            "final_stock": _typed(final),
            "final_total": float(final.sum()),
            "note": _depletion_note(
                opening, collected, demand, wasted, final, int(horizon), float(weekly_demand), float(wastage)
            ),
        },
        "learning": {
            "next_drive_id": learned["id"],
            "next_drive_name": learned["name"],
            "same_as_recommendation": learned["id"] == best["id"],
            "note": (
                f"{policy.name} would try {learned['name']} next after practicing on your stock. "
                + (
                    "That matches the drive with the best estimated fit for today's gaps."
                    if learned["id"] == best["id"]
                    else "That can differ from the recommendation above, because the learning rule also tries drives it has seen less often. The recommendation itself is the best estimated fit for the gaps you entered."
                )
            ),
        },
        "priorities": {name: PRIORITY[name] for name in BLOOD_TYPES},
    }
