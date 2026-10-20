import type { PolicyId } from "./labels";

export type PolicySummary = {
  id: PolicyId | string;
  name: string;
  mean_cumulative_reward: number;
  std_cumulative_reward: number;
  min_cumulative_reward: number;
  max_cumulative_reward: number;
  improvement_vs_fixed: number | null;
  mean_total_units: number;
  std_total_units: number;
  mean_o_negative_units: number;
  blood_type_units: Record<string, number>;
  arm_frequency: Record<string, number>;
  arm_counts_mean: Record<string, number>;
  seed_cumulative_rewards: number[];
  seed_total_units: number[];
  seed_o_negative_units: number[];
  curve: {
    week: number[];
    reward_mean: number[];
    reward_std: number[];
    stock: Record<string, number[]>;
    shortage: Record<string, number[]>;
  };
  final_stock_mean: Record<string, number>;
  final_shortage_mean: Record<string, number>;
  target_stock: Record<string, number>;
  mean_weekly_demand: Record<string, number>;
  mean_weekly_collected: Record<string, number>;
};

export type Comparison = {
  parameters: {
    horizon: number;
    seeds: number[];
    n_seeds: number;
    discount: number;
    ucb_c: number;
    initial_stock_fraction: number;
    weekly_demand: number;
    wastage: number;
    reward_scale: number;
    preset: string;
    policies: string[];
  };
  runtime_ms: number;
  policies: PolicySummary[];
  limitations: string;
  reward_note: string;
};

export type ArmEstimate = {
  id: string;
  name: string;
  tier: number;
  pool: number;
  pattern: string;
  loyalty_rate?: number;
  report_table_mean_donors?: number;
  selected?: boolean;
  seasonal_multiplier: number;
  turnout_probability: number;
  expected_turnout: number;
  expected_reward?: number;
  expected_reward_at_initial_stock?: number;
  expected_reward_note?: string;
  selection_frequency?: number;
  scaled_mean?: number | null;
  count?: number;
  boosted_o_negative?: boolean;
  bonus?: number | null;
  index?: number | null;
  uncertainty?: number | null;
  posterior_mean?: number;
  posterior_std?: number;
  sample?: number;
};

export type Recommendation = {
  policy: string;
  policy_name: string;
  seed: number;
  history_weeks: number;
  decision_week: number;
  recommended_arm_id: string;
  explanation: string;
  arms: ArmEstimate[];
  stock: Record<string, number>;
  shortage: Record<string, number>;
  target_stock: Record<string, number>;
  reward_scale: number;
  note: string;
};

export type ArmCatalog = {
  week: number;
  n_arms: number;
  arms: ArmEstimate[];
};

export type AppConfig = {
  blood_types: string[];
  priority: Record<string, number>;
  population_mix: Record<string, number>;
  demand_share: Record<string, number>;
  loyalty_rate: Record<string, number>;
  reward: { formula: string; scale_used_by_learners: number; displayed_reward: string };
  defaults: Record<string, number>;
  presets: {
    quick: { horizon: number; n_seeds: number; preset: string };
    full: { horizon: number; n_seeds: number; preset: string };
  };
  policies: { id: string; name: string }[];
  week_order: string[];
  assumptions: string[];
  arms: string[];
};

export type StatRow = {
  count: number;
  missing: number;
  min: number | null;
  max: number | null;
  mean: number | null;
  std_sample: number | null;
  median: number | null;
};

export type DataQuality = {
  dataset: {
    name: string;
    origin: string;
    citation: string;
    paper: string;
    geography: string;
    target_definition: string;
    features: string[];
  };
  parsing: {
    path: string;
    sha256: string;
    header: string;
    physical_lines_including_header: number;
    file_ends_with_newline: boolean;
    rows_read: number;
  };
  shape: {
    rows: number;
    columns: number;
    column_names: string[];
    expected_rows: number;
    row_count_matches_uci: boolean;
    column_names_match: boolean;
  };
  missing_and_malformed: {
    missing_by_column: Record<string, number>;
    malformed_or_non_numeric_cells: number;
    passes: boolean;
  };
  target: {
    observed_values: number[];
    encoding_is_binary_0_1: boolean;
    donated_march_2007: number;
    did_not_donate: number;
    positive_rate: number;
    negative_rate: number;
    names_file_claims_positive_rate: number;
    imbalance: string;
  };
  duplicates: {
    extra_copies_of_repeated_rows: number;
    rows_that_belong_to_a_duplicate_group: number;
    unique_rows: number;
    action: string;
  };
  ranges_and_descriptive_statistics: Record<string, StatRow>;
  consistency: {
    monetary_not_equal_to_frequency_times_250: number | null;
    time_less_than_recency: number | null;
    note: string;
  };
  names_file_comparison: Array<{
    variable: string;
    published_min: number | null;
    actual_min: number | null;
    published_max: number | null;
    actual_max: number | null;
    published_mean: number | null;
    actual_mean: number | null;
    published_std: number | null;
    actual_std_sample: number | null;
  }>;
  calibration: {
    method: string;
    equal_count_quartiles: Array<{
      quartile: string;
      n: number;
      frequency_min: number;
      frequency_max: number;
      donated_rate: number;
    }>;
    natural_frequency_bins: Array<{ bin: string; n: number; donated_rate: number }>;
    natural_bin_note: string;
    lowest_rate: number;
    highest_rate: number;
    natural_lowest_rate: number;
    natural_highest_rate: number;
    report_lowest: number;
    report_highest: number;
    lowest_gap: number;
    highest_gap: number;
    natural_lowest_gap: number;
    natural_highest_gap: number;
    middle_tier_note: string;
  };
  calibration_note: string;
  checks: Record<string, boolean>;
  limitations: string[];
  not_in_this_file: string[];
};

export type Sensitivity = {
  horizon: number;
  seeds: number[];
  discount_grid: number[];
  ucb_c: number;
  rows: Array<{
    discount: number | null;
    policy: string;
    name: string;
    mean_cumulative_reward: number;
    std_cumulative_reward: number;
    improvement_vs_fixed: number | null;
    mean_o_negative_units: number;
    mean_total_units: number;
  }>;
  runtime_ms: number;
  note: string;
};

export type DemoSnapshot = {
  label: string;
  notice: string;
  result: Comparison;
  recommendation: Recommendation;
  data_quality: DataQuality;
};

export type SimulateBody = {
  preset?: "quick" | "full" | "custom";
  horizon?: number;
  n_seeds?: number;
  initial_stock_fraction?: number;
  weekly_demand?: number;
  discount?: number;
  ucb_c?: number;
  policies?: string[];
};
