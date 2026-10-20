import { ARMS } from "./labels";
import type { Comparison } from "./types";

export function comparisonToCsv(result: Comparison) {
  const armIds = ARMS.map((arm) => arm.id);
  const header = [
    "policy",
    "policy_name",
    "mean_cumulative_reward",
    "std_cumulative_reward",
    "improvement_vs_fixed_percent",
    "mean_total_units",
    "mean_o_negative_units",
    "min_cumulative_reward",
    "max_cumulative_reward",
    ...armIds.map((id) => `arm_frequency_${id}`),
    "horizon",
    "n_seeds",
    "discount",
    "ucb_c",
    "weekly_demand",
    "initial_stock_fraction",
  ];
  const lines = [header.join(",")];
  for (const row of result.policies) {
    const values = [
      row.id,
      csvCell(row.name),
      row.mean_cumulative_reward,
      row.std_cumulative_reward,
      row.improvement_vs_fixed ?? "",
      row.mean_total_units,
      row.mean_o_negative_units,
      row.min_cumulative_reward,
      row.max_cumulative_reward,
      ...armIds.map((id) => row.arm_frequency[id] ?? ""),
      result.parameters.horizon,
      result.parameters.n_seeds,
      result.parameters.discount,
      result.parameters.ucb_c,
      result.parameters.weekly_demand,
      result.parameters.initial_stock_fraction,
    ];
    lines.push(values.join(","));
  }
  return lines.join("\n") + "\n";
}

function csvCell(value: string) {
  if (/[",\n]/.test(value)) return `"${value.replaceAll('"', '""')}"`;
  return value;
}

export function downloadCsv(filename: string, contents: string) {
  const blob = new Blob([contents], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}
