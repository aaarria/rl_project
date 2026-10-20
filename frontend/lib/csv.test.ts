import assert from "node:assert/strict";
import test from "node:test";

import { comparisonToCsv } from "./csv";
import type { Comparison } from "./types";

const result = {
  parameters: {
    horizon: 4,
    seeds: [0],
    n_seeds: 1,
    discount: 0.95,
    ucb_c: 0.1,
    initial_stock_fraction: 0.6,
    weekly_demand: 90,
    wastage: 0.02,
    reward_scale: 100,
    preset: "custom",
    policies: ["fixed_rotation"],
  },
  runtime_ms: 1,
  limitations: "",
  reward_note: "",
  policies: [
    {
      id: "fixed_rotation",
      name: "Fixed Rotation",
      mean_cumulative_reward: 12.5,
      std_cumulative_reward: 0,
      min_cumulative_reward: 12.5,
      max_cumulative_reward: 12.5,
      improvement_vs_fixed: 0,
      mean_total_units: 40,
      std_total_units: 0,
      mean_o_negative_units: 3,
      blood_type_units: {},
      arm_frequency: { campus_weekday: 0.25 },
      arm_counts_mean: {},
      seed_cumulative_rewards: [12.5],
      seed_total_units: [40],
      seed_o_negative_units: [3],
      curve: { week: [], reward_mean: [], reward_std: [], stock: {}, shortage: {} },
      final_stock_mean: {},
      final_shortage_mean: {},
      target_stock: {},
      mean_weekly_demand: {},
      mean_weekly_collected: {},
    },
  ],
} as Comparison;

test("csv export uses the computed reward", () => {
  const csv = comparisonToCsv(result);
  const [header, row] = csv.trim().split("\n");
  assert.ok(header.startsWith("policy,policy_name,mean_cumulative_reward"));
  assert.ok(header.includes("arm_frequency_campus_weekday"));
  assert.equal(row.split(",")[0], "fixed_rotation");
  assert.equal(row.split(",")[2], "12.5");
  assert.equal(row.split(",")[4], "0");
});
