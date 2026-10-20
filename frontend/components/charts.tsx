"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  ErrorBar,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { BLOOD_COLORS, BLOOD_TYPES, POLICY_COLORS, armName } from "@/lib/labels";
import type { PolicySummary } from "@/lib/types";

const axis = { fontSize: 11, fill: "#6d645c" };
const tooltipStyle = {
  background: "#fff",
  border: "1px solid #e3dcd2",
  borderRadius: 8,
  fontSize: 12,
};

export function rewardChartRows(policies: PolicySummary[]) {
  const weeks = policies[0]?.curve.week ?? [];
  return weeks.map((week, index) => {
    const row: Record<string, number> = { week };
    for (const policy of policies) row[policy.id] = policy.curve.reward_mean[index];
    return row;
  });
}

export function RewardLines({ policies }: { policies: PolicySummary[] }) {
  const data = rewardChartRows(policies);
  return (
    <div className="h-72">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid stroke="#efeae4" vertical={false} />
          <XAxis dataKey="week" tick={axis} tickLine={false} axisLine={false} />
          <YAxis tick={axis} tickLine={false} axisLine={false} width={48} />
          <Tooltip contentStyle={tooltipStyle} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          {policies.map((policy) => (
            <Line
              key={policy.id}
              type="monotone"
              dataKey={policy.id}
              name={policy.name}
              stroke={POLICY_COLORS[policy.id]}
              strokeWidth={policy.id === "discounted_ucb" || policy.id === "discounted_thompson" ? 2.2 : 1.4}
              dot={false}
              isAnimationActive={false}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export function coloredRewardBars(policies: PolicySummary[]) {
  return policies.map((policy) => ({
    name: policy.name.replace("Discounted Thompson Sampling", "D-Thompson").replace("Discounted UCB", "D-UCB"),
    reward: Number(policy.mean_cumulative_reward.toFixed(1)),
    std: Number(policy.std_cumulative_reward.toFixed(1)),
    id: policy.id,
  }));
}

export function PolicyRewardBars({ policies }: { policies: PolicySummary[] }) {
  const data = coloredRewardBars(policies);
  return (
    <div className="h-72">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 12, right: 8, left: 0, bottom: 8 }}>
          <CartesianGrid stroke="#efeae4" vertical={false} />
          <XAxis dataKey="name" tick={axis} interval={0} tickLine={false} axisLine={false} />
          <YAxis tick={axis} tickLine={false} axisLine={false} width={48} />
          <Tooltip contentStyle={tooltipStyle} />
          <Bar dataKey="reward" name="Mean raw reward" fill="#1c2834" radius={[3, 3, 0, 0]} isAnimationActive={false}>
            <ErrorBar dataKey="std" width={4} stroke="#8d3b3b" />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function StockLines({
  policy,
  types,
}: {
  policy: PolicySummary;
  types: readonly string[];
}) {
  const data = policy.curve.week.map((week, index) => {
    const row: Record<string, number> = { week };
    for (const type of types) {
      const stock = policy.curve.stock[type]?.[index] ?? 0;
      const target = policy.target_stock[type] || 1;
      row[type] = (stock / target) * 100;
    }
    return row;
  });
  return (
    <div className="h-72">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid stroke="#efeae4" vertical={false} />
          <XAxis dataKey="week" tick={axis} tickLine={false} axisLine={false} />
          <YAxis tick={axis} tickLine={false} axisLine={false} width={40} unit="%" />
          <Tooltip contentStyle={tooltipStyle} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          {types.map((type) => (
            <Line
              key={type}
              type="monotone"
              dataKey={type}
              stroke={BLOOD_COLORS[type]}
              strokeWidth={1.8}
              dot={false}
              isAnimationActive={false}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export function ShortageLines({ policy, types }: { policy: PolicySummary; types: readonly string[] }) {
  const data = policy.curve.week.map((week, index) => {
    const row: Record<string, number> = { week };
    for (const type of types) row[type] = (policy.curve.shortage[type]?.[index] ?? 0) * 100;
    return row;
  });
  return (
    <div className="h-72">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid stroke="#efeae4" vertical={false} />
          <XAxis dataKey="week" tick={axis} tickLine={false} axisLine={false} />
          <YAxis tick={axis} tickLine={false} axisLine={false} width={40} unit="%" />
          <Tooltip contentStyle={tooltipStyle} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          {types.map((type) => (
            <Line
              key={type}
              type="monotone"
              dataKey={type}
              stroke={BLOOD_COLORS[type]}
              strokeWidth={1.8}
              dot={false}
              isAnimationActive={false}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export function StockTargetBars({ policy }: { policy: PolicySummary }) {
  const data = BLOOD_TYPES.map((type) => ({
    type,
    stock: Number(policy.final_stock_mean[type]?.toFixed(1) ?? 0),
    target: Number(policy.target_stock[type]?.toFixed(1) ?? 0),
  }));
  return (
    <div className="h-72">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid stroke="#efeae4" vertical={false} />
          <XAxis dataKey="type" tick={axis} tickLine={false} axisLine={false} />
          <YAxis tick={axis} tickLine={false} axisLine={false} width={40} />
          <Tooltip contentStyle={tooltipStyle} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Bar dataKey="stock" name="Stock" fill="#1c2834" radius={[3, 3, 0, 0]} isAnimationActive={false} />
          <Bar dataKey="target" name="Target" fill="#c4a574" radius={[3, 3, 0, 0]} isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function ArmFrequencyChart({ policies }: { policies: PolicySummary[] }) {
  const data = policies.map((policy) => {
    const row: Record<string, string | number> = {
      name: policy.name.replace("Discounted Thompson Sampling", "D-Thompson").replace("Discounted UCB", "D-UCB"),
    };
    for (const [id, value] of Object.entries(policy.arm_frequency)) {
      row[armName(id)] = Number((value * 100).toFixed(1));
    }
    return row;
  });
  const names = Object.keys(data[0] || {}).filter((key) => key !== "name");
  const palette = ["#1c2834", "#8d3b3b", "#3e5c78", "#2f6a56", "#b08968", "#8a8178", "#5e7388", "#c4a574"];
  return (
    <div className="h-80">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 8 }}>
          <CartesianGrid stroke="#efeae4" vertical={false} />
          <XAxis dataKey="name" tick={axis} tickLine={false} axisLine={false} />
          <YAxis tick={axis} tickLine={false} axisLine={false} width={36} unit="%" />
          <Tooltip contentStyle={tooltipStyle} />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          {names.map((name, index) => (
            <Bar key={name} dataKey={name} stackId="arms" fill={palette[index % palette.length]} isAnimationActive={false} />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
