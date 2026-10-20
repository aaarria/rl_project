import assert from "node:assert/strict";
import test from "node:test";

import { demoForm, emptyForm, parseInventoryCsv, planToCsv, validatePlan, type PlanResult } from "./plan";

test("empty form asks for the fields a planner must enter", () => {
  const errors = validatePlan(emptyForm());
  assert.match(errors.planningDate, /date/i);
  assert.match(errors.weeklyDemand, /week/i);
  assert.match(errors["stock.O-"], /O-negative/i);
  assert.equal(errors.arms, undefined);
});

test("negative stock is rejected and demo data is accepted", () => {
  const demo = demoForm("2026-10-21");
  assert.equal(validatePlan(demo).planningDate, undefined);
  assert.equal(Object.keys(validatePlan(demo)).length, 0);
  assert.equal(demo.usingDemo, true);
  demo.stock["O-"] = "-3";
  assert.match(validatePlan(demo)["stock.O-"], /0 and 1,000,000/);
});

test("csv preview validates before the numbers can be used", () => {
  const bad = parseInventoryCsv("blood type,current stock,target stock\nO-negative,-1,10\n");
  assert.ok(bad.errors.some((error) => /0 or higher/.test(error)));

  const good = parseInventoryCsv(
    "blood type,current stock,target stock\nO-negative,12,20\nAB positive,4,8\n",
  );
  assert.equal(good.errors.length, 0);
  assert.equal(good.stock["O-"], "12");
  assert.equal(good.target["AB+"], "8");
  assert.match(good.notes.join(" "), /not in the file/i);
});

test("export includes the recommendation and a simulation warning", () => {
  const result = {
    facility_name: "Example",
    planning_date: "2026-10-21",
    policy_name: "Discounted UCB",
    objective_label: "Balance volume and shortages",
    recommended: { name: "Mall Weekend", slot: "Weekend, at a mall" },
    plain_reason: "Mall Weekend has the highest score.",
    estimates: {
      donors: 30.5,
      collection_units: 30.5,
      objective_score: 12,
      shortage_weighted_reward: 14,
      label: "Simulated estimate for the recommended drive.",
      by_type: { "O-": 2 },
    },
    inventory: {
      opening_stock: { "O-": 10 },
      target_stock: { "O-": 20 },
      final_stock: { "O-": 8 },
    },
    alternatives: [
      {
        rank: 1,
        name: "Mall Weekend",
        slot: "Weekend, at a mall",
        expected_donors: 30.5,
        objective_score: 12,
        selected: true,
      },
    ],
  } as PlanResult;
  const csv = planToCsv(result);
  assert.match(csv, /Mall Weekend/);
  assert.match(csv, /Simulated estimate/);
  assert.match(csv, /O-negative,10,20/);
});
