"use client";

import { useState } from "react";

import { PolicyRewardBars, RewardLines, StockLines } from "@/components/charts";
import { useExperiment } from "@/components/experiment-context";
import { PageHeader, StatusBanner } from "@/components/feedback";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, Td, Th } from "@/components/ui/table";
import { num, pct } from "@/lib/format";
import { BLOOD_TYPES, NEGATIVE_TYPES } from "@/lib/labels";

export default function OverviewPage() {
  const { result } = useExperiment();
  const [activeId, setActiveId] = useState("discounted_ucb");
  const active = result?.policies.find((policy) => policy.id === activeId) ?? result?.policies[0];
  const critical = active
    ? BLOOD_TYPES.filter((type) => {
        const target = active.target_stock[type] || 1;
        return active.final_stock_mean[type] / target < 0.25;
      })
    : [];

  return (
    <div>
      <PageHeader
        eyebrow="Overview"
        title="Simulated inventory and policy reward"
        lede="A quick seeded run loads on open. Raw reward is the shortage-weighted sum. Learners see that number divided by 100."
      />
      <StatusBanner />
      {result && active && (
        <>
          <div className="mb-4 flex flex-wrap gap-2">
            {result.policies.map((policy) => (
              <button
                key={policy.id}
                type="button"
                onClick={() => setActiveId(policy.id)}
                className={`rounded-full border px-3 py-1 text-xs ${
                  policy.id === active.id
                    ? "border-burgundy bg-burgundy text-white"
                    : "border-line bg-white text-ink"
                }`}
              >
                {policy.name}
              </button>
            ))}
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Stat label="Cumulative reward" value={num(active.mean_cumulative_reward, 0)} detail={`± ${num(active.std_cumulative_reward, 0)}`} />
            <Stat label="Units collected" value={num(active.mean_total_units, 0)} detail="Mean across seeds" />
            <Stat label="O-negative units" value={num(active.mean_o_negative_units, 0)} detail={pct(active.improvement_vs_fixed) + " reward vs rotation"} />
            <Stat label="Critical types" value={String(critical.length)} detail={critical.length ? critical.join(", ") : "None under 25% of target"} />
          </div>
          <div className="mt-4 grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Cumulative reward</CardTitle>
              </CardHeader>
              <CardContent>
                <RewardLines policies={result.policies} />
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Mean reward by policy</CardTitle>
              </CardHeader>
              <CardContent>
                <PolicyRewardBars policies={result.policies} />
              </CardContent>
            </Card>
          </div>
          <Card className="mt-4">
            <CardHeader>
              <CardTitle>Stock as a share of target · {active.name}</CardTitle>
            </CardHeader>
            <CardContent>
              <StockLines policy={active} types={NEGATIVE_TYPES} />
              <p className="mt-2 text-xs text-muted">Negative types only. The line is end-of-week stock divided by the two-week target.</p>
            </CardContent>
          </Card>
          <Card className="mt-4">
            <CardHeader>
              <CardTitle>Latest experiment</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="mb-3 flex flex-wrap gap-2">
                <Badge>{result.parameters.preset}</Badge>
                <Badge>{result.parameters.horizon} weeks</Badge>
                <Badge>{result.parameters.n_seeds} seeds</Badge>
                <Badge>γ {result.parameters.discount}</Badge>
                <Badge>c {result.parameters.ucb_c}</Badge>
                <Badge>{num(result.runtime_ms, 0)} ms</Badge>
              </div>
              <Table>
                <thead>
                  <tr>
                    <Th>Policy</Th>
                    <Th>Reward</Th>
                    <Th>vs rotation</Th>
                    <Th>Units</Th>
                    <Th>O−</Th>
                  </tr>
                </thead>
                <tbody>
                  {result.policies.map((policy) => (
                    <tr key={policy.id}>
                      <Td>{policy.name}</Td>
                      <Td>{num(policy.mean_cumulative_reward, 1)}</Td>
                      <Td>{pct(policy.improvement_vs_fixed)}</Td>
                      <Td>{num(policy.mean_total_units, 1)}</Td>
                      <Td>{num(policy.mean_o_negative_units, 1)}</Td>
                    </tr>
                  ))}
                </tbody>
              </Table>
              <p className="mt-3 text-xs leading-5 text-muted">{result.reward_note}</p>
              <details className="mt-2 text-xs leading-5 text-muted">
                <summary className="cursor-pointer text-ink">Evaluation limits</summary>
                <p className="mt-2">{result.limitations}</p>
              </details>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}

function Stat({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <Card>
      <CardContent className="px-4 py-4">
        <p className="text-[11px] uppercase tracking-[0.14em] text-muted">{label}</p>
        <p className="mt-2 font-serif text-3xl tabular-nums text-ink">{value}</p>
        <p className="mt-1 text-xs text-muted">{detail}</p>
      </CardContent>
    </Card>
  );
}
