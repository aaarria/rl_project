export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const BLOOD_TYPES = ["O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"] as const;
export const NEGATIVE_TYPES = ["O-", "A-", "B-", "AB-"] as const;

export const ARMS = [
  { id: "campus_weekday", name: "Campus Weekday" },
  { id: "campus_weekend", name: "Campus Weekend" },
  { id: "corporate_lunch", name: "Corporate Lunch" },
  { id: "corporate_weekend", name: "Corporate Weekend" },
  { id: "community_centre", name: "Community Centre" },
  { id: "mall_weekend", name: "Mall Weekend" },
  { id: "hospital_camp", name: "Hospital Camp" },
  { id: "tech_park_evening", name: "Tech-Park Evening" },
] as const;

export const POLICIES = [
  { id: "fixed_rotation", name: "Fixed Rotation" },
  { id: "random", name: "Random" },
  { id: "greedy", name: "Greedy" },
  { id: "ucb1", name: "UCB1" },
  { id: "discounted_ucb", name: "Discounted UCB" },
  { id: "discounted_thompson", name: "Discounted Thompson Sampling" },
] as const;

export type PolicyId = (typeof POLICIES)[number]["id"];

export const POLICY_COLORS: Record<string, string> = {
  fixed_rotation: "#8a8178",
  random: "#b08968",
  greedy: "#3e5c78",
  ucb1: "#2f6a56",
  discounted_ucb: "#8d3b3b",
  discounted_thompson: "#1c2834",
};

export const BLOOD_COLORS: Record<string, string> = {
  "O-": "#8d3b3b",
  "O+": "#c47c7c",
  "A-": "#1c2834",
  "A+": "#5e7388",
  "B-": "#8a5a2a",
  "B+": "#c4a574",
  "AB-": "#2f6a56",
  "AB+": "#7aa394",
};

export function armName(id: string) {
  return ARMS.find((arm) => arm.id === id)?.name ?? id;
}
