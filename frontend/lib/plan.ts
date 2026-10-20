import { ARMS, BLOOD_TYPES, type PolicyId } from "./labels";

export const BLOOD_LABELS: Record<(typeof BLOOD_TYPES)[number], string> = {
  "O-": "O-negative",
  "O+": "O-positive",
  "A-": "A-negative",
  "A+": "A-positive",
  "B-": "B-negative",
  "B+": "B-positive",
  "AB-": "AB-negative",
  "AB+": "AB-positive",
};

export const OBJECTIVES = [
  {
    id: "shortage",
    label: "Fill the biggest gaps",
    help: "Units count only when that blood type is still below its target.",
  },
  {
    id: "o_negative",
    label: "Collect more O-negative",
    help: "The score follows O-negative units, especially when O-negative is low.",
  },
  {
    id: "weighted",
    label: "Balance volume and shortages",
    help: "Every unit counts. Scarce types, and O-negative, count more.",
  },
] as const;

export type ObjectiveId = (typeof OBJECTIVES)[number]["id"];

export const POLICY_HELP: Record<PolicyId, string> = {
  fixed_rotation: "Cycles through the drives you allow. It ignores results.",
  random: "Picks one of the allowed drives at random.",
  greedy: "Tries each allowed drive once, then stays with the best average.",
  ucb1: "Balances the best average with drives that have not been tried much.",
  discounted_ucb: "Like UCB1, but recent weeks matter more than old ones. A good default.",
  discounted_thompson: "Draws from what it has learned, so it keeps testing other drives.",
};

const DEMAND_SHARE: Record<(typeof BLOOD_TYPES)[number], number> = {
  "O-": 0.11,
  "O+": 0.34,
  "A-": 0.06,
  "A+": 0.34,
  "B-": 0.02,
  "B+": 0.09,
  "AB-": 0.01,
  "AB+": 0.03,
};

export type LevelMap = Record<(typeof BLOOD_TYPES)[number], string>;

export type PlanForm = {
  facilityName: string;
  planningDate: string;
  horizon: string;
  weeklyDemand: string;
  stock: LevelMap;
  target: LevelMap;
  arms: string[];
  policy: PolicyId;
  objective: ObjectiveId;
  discount: string;
  ucbC: string;
  usingDemo: boolean;
};

export type PlanLevels = Record<string, number>;

export type PlanAlternative = {
  id: string;
  name: string;
  slot: string;
  selected: boolean;
  rank: number;
  expected_donors: number;
  expected_units: number;
  collection_by_type: PlanLevels;
  objective_score: number;
  shortage_weighted_reward: number;
  times_chosen_in_simulation: number;
  share_of_simulated_weeks: number;
};

export type PlanResult = {
  facility_name: string;
  planning_date: string;
  calendar_week: number;
  decision_week_index: number;
  date_effect: string;
  horizon_weeks: number;
  weekly_demand: number;
  policy: string;
  policy_name: string;
  objective: ObjectiveId;
  objective_label: string;
  objective_note: string;
  recommended: { id: string; name: string; slot: string };
  plain_reason: string;
  technical_explanation: string;
  estimates: {
    donors: number;
    collection_units: number;
    by_type: PlanLevels;
    objective_score: number;
    shortage_weighted_reward: number;
    label: string;
  };
  simulated_history: {
    weeks: number;
    total_units: number;
    o_negative_units: number;
    objective_score: number;
    shortage_weighted_reward: number;
    units_by_type: PlanLevels;
    label: string;
  };
  inventory: {
    opening_stock: PlanLevels;
    target_stock: PlanLevels;
    final_stock: PlanLevels;
    shortage_after: PlanLevels;
  };
  alternatives: PlanAlternative[];
  assumptions: string[];
  settings: {
    seed: number;
    discount: number;
    discount_used: boolean;
    ucb_c: number;
    ucb_c_used: boolean;
    wastage: number;
  };
  limitations: string[];
  inputs: {
    facility_name: string;
    planning_date: string;
    horizon_weeks: number;
    weekly_demand: number;
    stock: PlanLevels;
    target: PlanLevels;
    arms: string[];
    policy: string;
    objective: string;
  };
};

export type PlanCompare = {
  objective: string;
  objective_label: string;
  note: string;
  rows: Array<{
    id: string;
    name: string;
    selected_by_user: boolean;
    recommended_arm_id: string;
    recommended_name: string;
    recommended_slot: string;
    simulated_objective_score: number;
    simulated_shortage_weighted_reward: number;
    simulated_units: number;
    simulated_o_negative_units: number;
  }>;
};

export type CsvPreview = {
  stock: Partial<LevelMap>;
  target: Partial<LevelMap>;
  errors: string[];
  notes: string[];
};

function blankLevels(): LevelMap {
  return {
    "O-": "",
    "O+": "",
    "A-": "",
    "A+": "",
    "B-": "",
    "B+": "",
    "AB-": "",
    "AB+": "",
  };
}

export function emptyForm(): PlanForm {
  return {
    facilityName: "",
    planningDate: "",
    horizon: "12",
    weeklyDemand: "",
    stock: blankLevels(),
    target: blankLevels(),
    arms: ARMS.map((arm) => arm.id),
    policy: "discounted_ucb",
    objective: "weighted",
    discount: "0.95",
    ucbC: "0.1",
    usingDemo: false,
  };
}

export function demoForm(planningDate: string): PlanForm {
  const stock = blankLevels();
  const target = blankLevels();
  for (const type of BLOOD_TYPES) {
    const weekly = 90 * DEMAND_SHARE[type];
    target[type] = String(Math.round(weekly * 2));
    stock[type] = String(Math.round(weekly * 2 * 0.6));
  }
  return {
    ...emptyForm(),
    facilityName: "Example City Blood Bank",
    planningDate,
    horizon: "12",
    weeklyDemand: "90",
    stock,
    target,
    usingDemo: true,
  };
}

function parseNumber(value: string) {
  const trimmed = value.trim();
  if (!trimmed) return null;
  const amount = Number(trimmed);
  if (!Number.isFinite(amount)) return Number.NaN;
  return amount;
}

export function validatePlan(form: PlanForm) {
  const errors: Record<string, string> = {};
  if (!form.planningDate) {
    errors.planningDate = "Choose the date this plan should start.";
  }
  const horizon = parseNumber(form.horizon);
  if (horizon == null || Number.isNaN(horizon)) {
    errors.horizon = "Enter how many weeks to plan.";
  } else if (!Number.isInteger(horizon) || horizon < 1 || horizon > 104) {
    errors.horizon = "Use a whole number from 1 to 104 weeks.";
  }
  const demand = parseNumber(form.weeklyDemand);
  if (demand == null || Number.isNaN(demand)) {
    errors.weeklyDemand = "Enter the units you expect to need each week.";
  } else if (demand < 0 || demand > 5000) {
    errors.weeklyDemand = "Weekly demand must be between 0 and 5000.";
  }
  for (const type of BLOOD_TYPES) {
    const stock = parseNumber(form.stock[type]);
    const target = parseNumber(form.target[type]);
    if (stock == null || Number.isNaN(stock)) {
      errors[`stock.${type}`] = `Enter current ${BLOOD_LABELS[type]} stock. Use 0 if you have none.`;
    } else if (stock < 0 || stock > 1_000_000) {
      errors[`stock.${type}`] = `${BLOOD_LABELS[type]} stock must be between 0 and 1,000,000.`;
    }
    if (target == null || Number.isNaN(target)) {
      errors[`target.${type}`] = `Enter a target for ${BLOOD_LABELS[type]}. Use 0 if you have no target.`;
    } else if (target < 0 || target > 1_000_000) {
      errors[`target.${type}`] = `${BLOOD_LABELS[type]} target must be between 0 and 1,000,000.`;
    }
  }
  if (form.arms.length === 0) {
    errors.arms = "Choose at least one drive you can run.";
  }
  const discount = parseNumber(form.discount);
  if (discount == null || Number.isNaN(discount) || discount <= 0 || discount > 1) {
    errors.discount = "Use a number above 0 and up to 1.";
  }
  const ucbC = parseNumber(form.ucbC);
  if (ucbC == null || Number.isNaN(ucbC) || ucbC <= 0 || ucbC > 5) {
    errors.ucbC = "Use a number above 0 and up to 5.";
  }
  if (form.facilityName.trim().length > 120) {
    errors.facilityName = "Use 120 characters or fewer.";
  }
  return errors;
}

export function toPlanRequest(form: PlanForm) {
  const stock: PlanLevels = {};
  const target: PlanLevels = {};
  for (const type of BLOOD_TYPES) {
    stock[type] = Number(form.stock[type]);
    target[type] = Number(form.target[type]);
  }
  return {
    facility_name: form.facilityName.trim(),
    planning_date: form.planningDate,
    horizon: Number(form.horizon),
    weekly_demand: Number(form.weeklyDemand),
    stock,
    target,
    arms: form.arms,
    policy: form.policy,
    objective: form.objective,
    discount: Number(form.discount),
    ucb_c: Number(form.ucbC),
    seed: 0,
  };
}

export type PlanRequestBody = ReturnType<typeof toPlanRequest> & { wastage?: number };

export function requestFromResult(result: PlanResult): PlanRequestBody {
  return {
    facility_name: result.inputs.facility_name,
    planning_date: result.inputs.planning_date,
    horizon: result.inputs.horizon_weeks,
    weekly_demand: result.inputs.weekly_demand,
    stock: result.inputs.stock,
    target: result.inputs.target,
    arms: result.inputs.arms,
    policy: result.inputs.policy as PlanForm["policy"],
    objective: result.inputs.objective as PlanForm["objective"],
    discount: result.settings.discount,
    ucb_c: result.settings.ucb_c,
    seed: result.settings.seed,
    wastage: result.settings.wastage,
  };
}

const TYPE_ALIASES: Record<string, (typeof BLOOD_TYPES)[number]> = {
  "o-": "O-",
  ominus: "O-",
  onegative: "O-",
  "o-negative": "O-",
  "o+": "O+",
  oplus: "O+",
  opositive: "O+",
  "o-positive": "O+",
  "a-": "A-",
  aminus: "A-",
  anegative: "A-",
  "a-negative": "A-",
  "a+": "A+",
  aplus: "A+",
  apositive: "A+",
  "a-positive": "A+",
  "b-": "B-",
  bminus: "B-",
  bnegative: "B-",
  "b-negative": "B-",
  "b+": "B+",
  bplus: "B+",
  bpositive: "B+",
  "b-positive": "B+",
  "ab-": "AB-",
  abminus: "AB-",
  abnegative: "AB-",
  "ab-negative": "AB-",
  "ab+": "AB+",
  abplus: "AB+",
  abpositive: "AB+",
  "ab-positive": "AB+",
};

function canonicalType(value: string) {
  const key = value.toLowerCase().replace(/[\s_]/g, "");
  return TYPE_ALIASES[key] ?? null;
}

function splitCsvLine(line: string) {
  return line.split(",").map((cell) => cell.trim().replace(/^"|"$/g, ""));
}

export function parseInventoryCsv(text: string): CsvPreview {
  const lines = text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
  const preview: CsvPreview = { stock: {}, target: {}, errors: [], notes: [] };
  if (lines.length === 0) {
    preview.errors.push("The file is empty.");
    return preview;
  }
  const header = splitCsvLine(lines[0]).map((cell) => cell.toLowerCase());
  const typeIndex = header.findIndex((cell) =>
    ["blood_type", "blood type", "type", "blood"].includes(cell),
  );
  const stockIndex = header.findIndex((cell) =>
    ["stock", "current_stock", "current stock", "units", "current"].includes(cell),
  );
  const targetIndex = header.findIndex((cell) =>
    ["target", "target_stock", "target stock"].includes(cell),
  );
  const hasHeader = typeIndex >= 0 && (stockIndex >= 0 || targetIndex >= 0);
  const start = hasHeader ? 1 : 0;
  const seen = new Set<string>();
  if (!hasHeader) {
    preview.notes.push("No header was found. Columns are read as blood type, current stock, target stock.");
  }
  for (const line of lines.slice(start)) {
    const cells = splitCsvLine(line);
    const typeCell = cells[hasHeader ? typeIndex : 0] ?? "";
    const blood = canonicalType(typeCell);
    if (!blood) {
      preview.errors.push(`“${typeCell || "blank"}” is not one of the eight blood types.`);
      continue;
    }
    if (seen.has(blood)) {
      preview.errors.push(`${BLOOD_LABELS[blood]} appears more than once.`);
      continue;
    }
    seen.add(blood);
    const stockCell = cells[hasHeader ? stockIndex : 1];
    const targetCell = cells[hasHeader ? targetIndex : 2];
    if (stockIndex >= 0 || !hasHeader) {
      if (stockCell == null || stockCell === "") {
        preview.errors.push(`Add a current stock number for ${BLOOD_LABELS[blood]}.`);
      } else if (!Number.isFinite(Number(stockCell)) || Number(stockCell) < 0) {
        preview.errors.push(`${BLOOD_LABELS[blood]} stock must be 0 or higher.`);
      } else {
        preview.stock[blood] = String(Number(stockCell));
      }
    }
    if (targetIndex >= 0 || (!hasHeader && targetCell != null && targetCell !== "")) {
      if (!Number.isFinite(Number(targetCell)) || Number(targetCell) < 0) {
        preview.errors.push(`${BLOOD_LABELS[blood]} target must be 0 or higher.`);
      } else if (targetCell != null && targetCell !== "") {
        preview.target[blood] = String(Number(targetCell));
      }
    }
  }
  const missing = BLOOD_TYPES.filter((type) => preview.stock[type] == null && preview.target[type] == null);
  if (missing.length && preview.errors.length === 0) {
    preview.notes.push(
      `${missing.map((type) => BLOOD_LABELS[type]).join(", ")} ${missing.length === 1 ? "is" : "are"} not in the file and will stay as entered.`,
    );
  }
  return preview;
}

function csvCell(value: string | number) {
  const text = String(value);
  return /[",\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}

export function planToCsv(result: PlanResult) {
  const lines = [
    ["field", "value"].join(","),
    ["facility", result.facility_name || ""].map(csvCell).join(","),
    ["planning_date", result.planning_date].join(","),
    ["algorithm", result.policy_name].map(csvCell).join(","),
    ["objective", result.objective_label].map(csvCell).join(","),
    ["recommended_drive", result.recommended.name].map(csvCell).join(","),
    ["time_and_place", result.recommended.slot].map(csvCell).join(","),
    ["estimated_donors", result.estimates.donors.toFixed(1)].join(","),
    ["estimated_units", result.estimates.collection_units.toFixed(1)].join(","),
    ["estimated_objective_score", result.estimates.objective_score.toFixed(2)].join(","),
    ["estimated_shortage_weighted_reward", result.estimates.shortage_weighted_reward.toFixed(2)].join(","),
    ["reason", result.plain_reason].map(csvCell).join(","),
    ["estimate_note", result.estimates.label].map(csvCell).join(","),
    [],
    ["blood_type", "your_stock", "your_target", "simulated_stock_after_plan", "estimated_units_next_drive"].join(","),
  ];
  for (const type of BLOOD_TYPES) {
    lines.push(
      [
        BLOOD_LABELS[type],
        result.inventory.opening_stock[type] ?? "",
        result.inventory.target_stock[type] ?? "",
        result.inventory.final_stock[type]?.toFixed(1) ?? "",
        result.estimates.by_type[type]?.toFixed(2) ?? "",
      ].join(","),
    );
  }
  lines.push([]);
  lines.push(["rank", "drive", "slot", "estimated_donors", "objective_score", "recommended"].join(","));
  for (const row of result.alternatives) {
    lines.push(
      [
        row.rank,
        csvCell(row.name),
        csvCell(row.slot),
        row.expected_donors.toFixed(1),
        row.objective_score.toFixed(2),
        row.selected ? "yes" : "no",
      ].join(","),
    );
  }
  return `${lines.join("\n")}\n`;
}

export function downloadText(filename: string, contents: string, type = "text/csv") {
  const blob = new Blob([contents], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
