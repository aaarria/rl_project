"""Turn a comparison payload into CSV. Values are the computed experiment rows."""

from __future__ import annotations

import csv
import io

from app.config import ARMS


def comparison_to_csv(result: dict) -> str:
    arm_ids = [arm["id"] for arm in ARMS]
    header = [
        "policy",
        "policy_name",
        "mean_cumulative_reward",
        "std_cumulative_reward",
        "improvement_vs_fixed_percent",
        "mean_total_units",
        "mean_o_negative_units",
        "min_cumulative_reward",
        "max_cumulative_reward",
        *[f"arm_frequency_{arm_id}" for arm_id in arm_ids],
        "horizon",
        "n_seeds",
        "discount",
        "ucb_c",
        "weekly_demand",
        "initial_stock_fraction",
    ]
    params = result.get("parameters", {})
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=header, lineterminator="\n")
    writer.writeheader()
    for row in result.get("policies", []):
        frequency = row.get("arm_frequency", {})
        record = {
            "policy": row.get("id"),
            "policy_name": row.get("name"),
            "mean_cumulative_reward": row.get("mean_cumulative_reward"),
            "std_cumulative_reward": row.get("std_cumulative_reward"),
            "improvement_vs_fixed_percent": row.get("improvement_vs_fixed"),
            "mean_total_units": row.get("mean_total_units"),
            "mean_o_negative_units": row.get("mean_o_negative_units"),
            "min_cumulative_reward": row.get("min_cumulative_reward"),
            "max_cumulative_reward": row.get("max_cumulative_reward"),
            "horizon": params.get("horizon"),
            "n_seeds": params.get("n_seeds"),
            "discount": params.get("discount"),
            "ucb_c": params.get("ucb_c"),
            "weekly_demand": params.get("weekly_demand"),
            "initial_stock_fraction": params.get("initial_stock_fraction"),
        }
        for arm_id in arm_ids:
            record[f"arm_frequency_{arm_id}"] = frequency.get(arm_id)
        writer.writerow(record)
    return buffer.getvalue()
