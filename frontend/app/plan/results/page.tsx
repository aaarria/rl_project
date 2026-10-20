"use client";

import Link from "next/link";

import { usePlan } from "@/components/plan-context";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { num } from "@/lib/format";
import { BLOOD_TYPES, armName } from "@/lib/labels";
import { BLOOD_LABELS, downloadText, planToCsv, requestFromResult } from "@/lib/plan";

function Tag({ children }: { children: string }) {
  return (
    <span className="rounded-full border border-line bg-paper px-2 py-0.5 text-[11px] font-medium uppercase tracking-[0.12em] text-muted">
      {children}
    </span>
  );
}

export default function ResultsPage() {
  const { ready, result, compare, error, loading, comparing, submit, comparePolicies } = usePlan();

  if (!ready) {
    return <p className="text-sm text-muted">Loading the last recommendation…</p>;
  }

  if (!result) {
    return (
      <div className="max-w-xl space-y-3">
        <h1 className="font-serif text-3xl">No recommendation yet</h1>
        <p className="text-muted">Enter your stock and drive options first. The results on this page come from that run.</p>
        <Button asChild variant="burgundy">
          <Link href="/plan">Plan a Blood Drive</Link>
        </Button>
      </div>
    );
  }

  const chosenArms = result.inputs.arms.map((id) => armName(id)).join(", ");

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="max-w-3xl">
          <p className="text-xs font-medium uppercase tracking-[0.16em] text-burgundy">Recommendation</p>
          <h1 className="mt-2 font-serif text-4xl text-ink">{result.recommended.name}</h1>
          <p className="mt-2 text-lg text-ink">{result.recommended.slot}</p>
          <p className="mt-3 text-base leading-relaxed text-muted">{result.plain_reason}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button asChild variant="outline">
            <Link href="/plan">Edit Inputs</Link>
          </Button>
          <Button type="button" variant="outline" onClick={submit} disabled={loading}>
            {loading ? "Working…" : "Run Again"}
          </Button>
          <Button type="button" variant="outline" onClick={() => comparePolicies(requestFromResult(result))} disabled={comparing}>
            {comparing ? "Comparing…" : "Compare Policies"}
          </Button>
          <Button
            type="button"
            variant="burgundy"
            onClick={() => downloadText("drive-recommendation.csv", planToCsv(result))}
          >
            Export Results
          </Button>
        </div>
      </div>

      {error ? (
        <p className="rounded-lg border border-burgundy/30 bg-white px-4 py-3 text-sm text-burgundy" role="alert">
          {error}
        </p>
      ) : null}

      <p className="rounded-lg border border-burgundy/30 bg-white px-4 py-3 text-sm leading-relaxed text-ink">
        {result.estimates.label} The practice run is also simulated. Nothing on this page is a guaranteed turnout or a clinical forecast.
      </p>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader>
            <Tag>Your inputs</Tag>
            <CardTitle className="pt-2">What you entered</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 text-sm">
            <p>{result.facility_name || "No facility name"}</p>
            <p>Starts {result.planning_date}</p>
            <p>{num(result.weekly_demand)} units of demand per week</p>
            <p>{result.horizon_weeks} practice weeks</p>
            <p>{result.objective_label}</p>
            <p className="text-muted">{chosenArms}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <Tag>Simulated estimate</Tag>
            <CardTitle className="pt-2">Next recommended drive</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 text-sm">
            <p>About {num(result.estimates.donors, 1)} donors</p>
            <p>About {num(result.estimates.collection_units, 1)} units</p>
            <p>Objective score {num(result.estimates.objective_score, 1)}</p>
            <p>Shortage-weighted reward {num(result.estimates.shortage_weighted_reward, 1)}</p>
            <p className="text-muted">{result.policy_name}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <Tag>Simulated history</Tag>
            <CardTitle className="pt-2">Practice weeks</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 text-sm">
            <p>{num(result.simulated_history.total_units, 0)} units collected in the simulation</p>
            <p>{num(result.simulated_history.o_negative_units, 0)} of those were O-negative</p>
            <p>Objective total {num(result.simulated_history.objective_score, 0)}</p>
            <p className="text-muted">{result.simulated_history.label}</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Stock, target, and what the simulator had left</CardTitle>
          <p className="text-sm text-muted">
            Opening stock and targets are yours. The last column is the simulated shelf after {result.horizon_weeks} weeks, before the recommended drive is held.
          </p>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <table className="w-full min-w-[40rem] text-sm">
            <thead>
              <tr className="border-b border-line text-left text-muted">
                <th className="py-2 pr-3 font-medium">Blood type</th>
                <th className="py-2 pr-3 font-medium">Your stock</th>
                <th className="py-2 pr-3 font-medium">Your target</th>
                <th className="py-2 pr-3 font-medium">Simulated stock after the plan</th>
                <th className="py-2 font-medium">Estimated units at the next drive</th>
              </tr>
            </thead>
            <tbody>
              {BLOOD_TYPES.map((type) => (
                <tr key={type} className="border-b border-line/80">
                  <th className="py-2 pr-3 text-left font-medium">{BLOOD_LABELS[type]}</th>
                  <td className="py-2 pr-3">{num(result.inventory.opening_stock[type], 0)}</td>
                  <td className="py-2 pr-3">{num(result.inventory.target_stock[type], 0)}</td>
                  <td className="py-2 pr-3">{num(result.inventory.final_stock[type], 1)}</td>
                  <td className="py-2">{num(result.estimates.by_type[type], 1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Other drives you allowed</CardTitle>
          <p className="text-sm text-muted">
            Ranked by the same objective for the week after your plan. Donor and unit figures are averages from the seasonal model, not a promise.
          </p>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <table className="w-full min-w-[36rem] text-sm">
            <thead>
              <tr className="border-b border-line text-left text-muted">
                <th className="py-2 pr-3 font-medium">Rank</th>
                <th className="py-2 pr-3 font-medium">Drive</th>
                <th className="py-2 pr-3 font-medium">When and where</th>
                <th className="py-2 pr-3 font-medium">Estimated donors</th>
                <th className="py-2 font-medium">Objective score</th>
              </tr>
            </thead>
            <tbody>
              {result.alternatives.map((row) => (
                <tr key={row.id} className="border-b border-line/80">
                  <td className="py-2 pr-3">{row.rank}</td>
                  <td className="py-2 pr-3 font-medium">
                    {row.name}
                    {row.selected ? <span className="ml-2 text-burgundy">Recommended</span> : null}
                  </td>
                  <td className="py-2 pr-3">{row.slot}</td>
                  <td className="py-2 pr-3">{num(row.expected_donors, 1)}</td>
                  <td className="py-2">{num(row.objective_score, 1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>

      {compare ? (
        <Card>
          <CardHeader>
            <CardTitle>Same stock, six algorithms</CardTitle>
            <p className="text-sm text-muted">{compare.note}</p>
          </CardHeader>
          <CardContent className="overflow-x-auto">
            <table className="w-full min-w-[40rem] text-sm">
              <thead>
                <tr className="border-b border-line text-left text-muted">
                  <th className="py-2 pr-3 font-medium">Algorithm</th>
                  <th className="py-2 pr-3 font-medium">Recommended drive</th>
                  <th className="py-2 pr-3 font-medium">Simulated units</th>
                  <th className="py-2 pr-3 font-medium">Simulated O-negative</th>
                  <th className="py-2 font-medium">Objective total</th>
                </tr>
              </thead>
              <tbody>
                {compare.rows.map((row) => (
                  <tr key={row.id} className="border-b border-line/80">
                    <td className="py-2 pr-3 font-medium">
                      {row.name}
                      {row.selected_by_user ? <span className="ml-2 text-burgundy">Yours</span> : null}
                    </td>
                    <td className="py-2 pr-3">{row.recommended_name}</td>
                    <td className="py-2 pr-3">{num(row.simulated_units, 0)}</td>
                    <td className="py-2 pr-3">{num(row.simulated_o_negative_units, 0)}</td>
                    <td className="py-2">{num(row.simulated_objective_score, 0)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      ) : null}

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <Tag>Configured assumptions</Tag>
            <CardTitle className="pt-2">What the simulator assumed</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm leading-relaxed text-muted">
            <p>{result.date_effect}</p>
            <p>{result.objective_note}</p>
            {result.assumptions.map((item) => (
              <p key={item}>{item}</p>
            ))}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <Tag>Limits</Tag>
            <CardTitle className="pt-2">What this cannot tell you</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm leading-relaxed text-muted">
            {result.limitations.slice(0, 5).map((item) => (
              <p key={item}>{item}</p>
            ))}
            <details>
              <summary className="cursor-pointer text-ink">More detail from the method</summary>
              <div className="mt-2 space-y-2">
                {result.limitations.slice(5).map((item) => (
                  <p key={item}>{item}</p>
                ))}
                <p className="text-ink">{result.technical_explanation}</p>
              </div>
            </details>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
