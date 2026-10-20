"""Advice must follow the inventory the user entered."""

import numpy as np
import pytest

from datetime import date

from app.advice import advise, demo_levels, inventory_rows, parse_inventory_csv, shortage_units
from app.config import BLOOD_TYPES
from app.environment import step_stock


def _even(amount: float) -> dict[str, float]:
    return {name: amount for name in BLOOD_TYPES}


def _advise(**overrides):
    stock, target = demo_levels(90)
    body = dict(
        facility_name="Example City Blood Bank",
        horizon=4,
        weekly_demand=90,
        stock=stock,
        target=target,
        arm_ids=[
            "campus_weekday",
            "campus_weekend",
            "corporate_lunch",
            "corporate_weekend",
            "community_centre",
            "mall_weekend",
            "hospital_camp",
            "tech_park_evening",
        ],
        objective="shortage",
        seed=0,
        on_date=date(2026, 10, 21),
    )
    body.update(overrides)
    return advise(**body)


def test_one_donation_is_one_unit():
    result = _advise()
    drive = result["recommended"]
    assert drive["estimated_donations"] == pytest.approx(drive["estimated_units"])
    assert sum(drive["units_by_type"].values()) == pytest.approx(drive["estimated_units"])
    assert any("one unit" in line for line in result["reasons"])


def test_shortage_math_and_status_labels():
    gaps = shortage_units(np.array([10, 0, 5], dtype=float), np.array([10, 8, 0], dtype=float))
    assert gaps.tolist() == [0, 8, 0]
    rows = inventory_rows(
        {**_even(10), "O-": 1, "A+": 10},
        {**_even(10), "O-": 10, "A+": 4},
    )
    by_name = {row["blood_type"]: row for row in rows}
    assert by_name["O-negative"]["status"] == "Critical"
    assert by_name["O-negative"]["units_short"] == 9
    assert by_name["A-positive"]["status"] == "Adequate"
    assert by_name["O-positive"]["status"] == "Adequate"


def test_stock_transition_wastes_then_floors_at_zero():
    stock = np.array([10, 1, 0, 0, 0, 0, 0, 0], dtype=float)
    collected = np.array([2, 0, 0, 0, 0, 0, 0, 0], dtype=float)
    demand = np.array([5, 10, 0, 0, 0, 0, 0, 0], dtype=float)
    updated = step_stock(stock, collected, demand, wastage=0.02)
    assert updated[0] == pytest.approx(0.98 * 10 + 2 - 5)
    assert updated[1] == 0


def test_current_gaps_change_which_drive_is_recommended():
    def only(blood_type: str):
        stock = _even(80)
        target = _even(80)
        stock[blood_type] = 0
        target[blood_type] = 40
        return _advise(stock=stock, target=target, weekly_demand=20, horizon=2)

    o_negative = only("O-")
    ab_negative = only("AB-")
    assert o_negative["recommended"]["id"] != ab_negative["recommended"]["id"]
    assert o_negative["recommended"]["priority_units"] > 0
    assert "O-negative" in o_negative["reasons"][0]


def test_excluded_drives_cannot_be_recommended():
    result = _advise(arm_ids=["hospital_camp", "corporate_weekend"])
    assert result["recommended"]["id"] in {"hospital_camp", "corporate_weekend"}
    assert {row["id"] for row in result["options"]} == {"hospital_camp", "corporate_weekend"}


def test_same_seed_repeats_and_inputs_are_not_decorative():
    first = _advise(seed=3)
    second = _advise(seed=3)
    assert first["recommended"]["id"] == second["recommended"]["id"]
    assert first["projection"]["final_stock"] == second["projection"]["final_stock"]
    other = _advise(seed=4)
    assert first["options"][0]["score"] == other["options"][0]["score"]
    assert first["projection"]["final_stock"] != other["projection"]["final_stock"]


def test_projection_explains_a_zero_shelf_without_calling_it_current_stock():
    result = _advise(stock=_even(5), target=_even(40), weekly_demand=90, horizon=8)
    emptied = [
        amount
        for amount in result["projection"]["final_stock"].values()
        if amount < 0.5
    ]
    assert len(emptied) >= 4
    note = result["projection"]["note"].lower()
    assert "not your current stock" in note
    assert "unusable" in note
    assert result["projection"]["opening_stock"]["O-"] == 5


def test_validation_and_csv_upload():
    with pytest.raises(ValueError, match="at least one"):
        _advise(arm_ids=[])
    with pytest.raises(ValueError, match="cannot be negative"):
        _advise(stock={**demo_levels()[0], "O-": -1})
    with pytest.raises(ValueError, match="1 to 104"):
        _advise(horizon=0)

    bad = parse_inventory_csv("blood type,current stock,target stock\nO-negative,-2,10\n")
    assert any("cannot be negative" in error for error in bad["errors"])
    good = parse_inventory_csv(
        "blood type,current stock,target stock\nO-negative,12,20\nAB positive,4,8\n"
    )
    assert good["errors"] == []
    assert good["stock"]["O-"] == 12
    assert good["target"]["AB+"] == 8
