"use client";

import { useMemo, useState } from "react";

import { ArmFrequencyChart, PolicyRewardBars, RewardLines } from "@/components/charts";
import { useExperiment } from "@/components/experiment-context";
import { PageHeader, StatusBanner } from "@/components/feedback";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, Td, Th } from "@/components/ui/table";
import { comparisonToCsv, downloadCsv } from "@/lib/csv";
import { num, pct } from "@/lib/format";
import { armName } from "@/lib/labels";
import type { PolicySummary } from "@/lib/types";

type SortKey = "name" | "reward" | "std" | "improvement" | "units" | "oneg";

export default function ComparePage() {
  const { result } = useExperiment();
  const [hidden, setHidden] = useState<string[]>([]);
  const [sort, setSort] = useState<{ key: SortKey; dir: "asc" | "desc" }>({ key: "reward", dir: "desc" });
  const visible = useMemo(
    () => result?.policies.filter((policy) => !hidden.includes(policy.id)) ?? [],
    [result, hidden],
  );
  const sorted = useMemo(() => sortPolicies(visible, sort), [visible, sort]);

  function toggleSort(key: SortKey) {
    setSort((current) =>
      current.key === key ? { key, dir: current.dir === "asc" ? "desc" : "asc" } : { key, dir: "desc" },
    );
  }

  return (
    <div>
      <PageHeader
        eyebrow="Policies"
        title="Six policies, one shared set of weeks"
        lede="Each seed pre-draws turnout, blood type, and demand. Policies differ only in which arm they pull. Improvement is against Fixed Rotation on those same weeks."
      />
      <StatusBanner />
      {result && (
        <>
          <div className="mb-4 flex flex-wrap items-center gap-2">
            {result.policies.map((policy) => {
              const off = hidden.includes(policy.id);
              return (
                <button
                  key={policy.id}
                  type="button"
                  onClick={() =>
                    setHidden((current) =>
                      current.includes(policy.id) ? current.filter((id) => id !== policy.id) : [...current, policy.id],
                    )
                  }
                  className={`rounded-full border px-3 py-1 text-xs ${off ? "border-line text-muted" : "border-ink bg-ink text-paper"}`}
                >
                  {policy.name}
                </button>
              );
            })}
            <Button
              variant="outline"
              size="sm"
              className="ml-auto"
              onClick={() => downloadCsv("policy-comparison.csv", comparisonToCsv(result))}
            >
              Export CSV
            </Button>
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Mean cumulative reward</CardTitle>
              </CardHeader>
              <CardContent>
                <PolicyRewardBars policies={visible} />
                <p className="text-xs text-muted">Error bars are ±1 sample standard deviation across seeds.</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Reward path</CardTitle>
              </CardHeader>
              <CardContent>
                <RewardLines policies={visible} />
              </CardContent>
            </Card>
          </div>
          <Card className="mt-4">
            <CardHeader>
              <CardTitle>Arm selection frequency</CardTitle>
            </CardHeader>
            <CardContent>
              <ArmFrequencyChart policies={visible} />
            </CardContent>
          </Card>
          <Card className="mt-4">
            <CardContent className="px-0 pb-2 pt-2">
              <Table>
                <thead>
                  <tr>
                    <Sortable label="Policy" k="name" sort={sort} onSort={toggleSort} />
                    <Sortable label="Reward" k="reward" sort={sort} onSort={toggleSort} />
                    <Sortable label="Std" k="std" sort={sort} onSort={toggleSort} />
                    <Sortable label="vs rotation" k="improvement" sort={sort} onSort={toggleSort} />
                    <Sortable label="Units" k="units" sort={sort} onSort={toggleSort} />
                    <Sortable label="O−" k="oneg" sort={sort} onSort={toggleSort} />
                    <Th>Most chosen</Th>
                  </tr>
                </thead>
                <tbody>
                  {sorted.map((policy) => (
                    <tr key={policy.id}>
                      <Td>{policy.name}</Td>
                      <Td>{num(policy.mean_cumulative_reward, 1)}</Td>
                      <Td>{num(policy.std_cumulative_reward, 1)}</Td>
                      <Td>{pct(policy.improvement_vs_fixed)}</Td>
                      <Td>{num(policy.mean_total_units, 1)}</Td>
                      <Td>{num(policy.mean_o_negative_units, 1)}</Td>
                      <Td className="tabular-nums">{topArm(policy)}</Td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}

function topArm(policy: PolicySummary) {
  const [id, share] = Object.entries(policy.arm_frequency).sort((a, b) => b[1] - a[1])[0] ?? ["", 0];
  return `${armName(id)} ${num(share * 100, 0)}%`;
}

function sortPolicies(policies: PolicySummary[], sort: { key: SortKey; dir: "asc" | "desc" }) {
  const direction = sort.dir === "asc" ? 1 : -1;
  return [...policies].sort((a, b) => {
    const value = (policy: PolicySummary) => {
      if (sort.key === "name") return policy.name;
      if (sort.key === "reward") return policy.mean_cumulative_reward;
      if (sort.key === "std") return policy.std_cumulative_reward;
      if (sort.key === "improvement") return policy.improvement_vs_fixed ?? -Infinity;
      if (sort.key === "units") return policy.mean_total_units;
      return policy.mean_o_negative_units;
    };
    const left = value(a);
    const right = value(b);
    if (typeof left === "string" && typeof right === "string") return left.localeCompare(right) * direction;
    return ((left as number) - (right as number)) * direction;
  });
}

function Sortable({
  label,
  k,
  sort,
  onSort,
}: {
  label: string;
  k: SortKey;
  sort: { key: SortKey; dir: "asc" | "desc" };
  onSort: (key: SortKey) => void;
}) {
  const mark = sort.key === k ? (sort.dir === "asc" ? " ↑" : " ↓") : "";
  return (
    <Th>
      <button type="button" className="uppercase tracking-[0.12em]" onClick={() => onSort(k)}>
        {label}
        {mark}
      </button>
    </Th>
  );
}
