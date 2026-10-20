"use client";

import { useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { useExperiment } from "@/components/experiment-context";
import { PageHeader, StatusBanner } from "@/components/feedback";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";
import { Table, Td, Th } from "@/components/ui/table";
import { api, ApiError } from "@/lib/api";
import { num, pct } from "@/lib/format";
import { POLICIES, type PolicyId } from "@/lib/labels";
import type { Sensitivity } from "@/lib/types";

const ALL = POLICIES.map((policy) => policy.id);

export default function LabPage() {
  const { run, result, loading } = useExperiment();
  const [horizon, setHorizon] = useState(52);
  const [seeds, setSeeds] = useState(3);
  const [stock, setStock] = useState(0.6);
  const [demand, setDemand] = useState(90);
  const [discount, setDiscount] = useState(0.95);
  const [ucb, setUcb] = useState(0.1);
  const [selected, setSelected] = useState<PolicyId[]>([...ALL]);
  const [formError, setFormError] = useState<string | null>(null);
  const [sensitivity, setSensitivity] = useState<Sensitivity | null>(null);
  const [sensError, setSensError] = useState<string | null>(null);
  const [sensLoading, setSensLoading] = useState(false);

  function validate() {
    if (horizon < 1 || horizon > 520) return "Horizon must be between 1 and 520 weeks.";
    if (seeds < 1 || seeds > 30) return "Seeds must be between 1 and 30.";
    if (stock < 0 || stock > 1.5) return "Initial stock must be between 0 and 1.5 times target.";
    if (demand < 1 || demand > 5000) return "Weekly demand must be between 1 and 5000.";
    if (discount <= 0 || discount > 1) return "Discount must be greater than 0 and at most 1.";
    if (ucb <= 0 || ucb > 5) return "UCB coefficient must be greater than 0 and at most 5.";
    if (selected.length === 0) return "Select at least one policy.";
    return null;
  }

  function resetDefaults() {
    setStock(0.6);
    setDemand(90);
    setDiscount(0.95);
    setUcb(0.1);
    setSelected([...ALL]);
  }

  function quick() {
    setFormError(null);
    setHorizon(52);
    setSeeds(3);
    resetDefaults();
    void run({ preset: "quick" }, "Quick evaluation · 52 weeks · 3 seeds");
  }

  function full() {
    setFormError(null);
    setHorizon(104);
    setSeeds(10);
    resetDefaults();
    void run({ preset: "full" }, "Full evaluation · 104 weeks · 10 seeds");
  }

  function custom() {
    const message = validate();
    setFormError(message);
    if (message) return;
    void run(
      {
        preset: "custom",
        horizon,
        n_seeds: seeds,
        initial_stock_fraction: stock,
        weekly_demand: demand,
        discount,
        ucb_c: ucb,
        policies: selected,
      },
      `Custom run · ${horizon} weeks · ${seeds} seeds`,
    );
  }

  async function runSensitivity(preset: "quick" | "full") {
    setSensLoading(true);
    setSensError(null);
    try {
      const payload = await api<Sensitivity>("/api/v1/sensitivity", {
        method: "POST",
        body: JSON.stringify({ preset }),
      });
      setSensitivity(payload);
    } catch (caught) {
      setSensError(caught instanceof ApiError ? caught.message : "Sensitivity run failed.");
    } finally {
      setSensLoading(false);
    }
  }

  const sensChart = sensitivity
    ? sensitivity.discount_grid.map((gamma) => {
        const row: Record<string, number> = { gamma };
        for (const item of sensitivity.rows) {
          if (item.discount === gamma && item.improvement_vs_fixed != null) row[item.policy] = item.improvement_vs_fixed;
        }
        return row;
      })
    : [];

  return (
    <div>
      <PageHeader
        eyebrow="Simulation lab"
        title="Change the horizon, then rerun"
        lede="Quick is 52 weeks and 3 seeds. Full is the report's 104 weeks and 10 seeds. Discounted rules need a horizon past week 40 before Tech-Park Evening starts to ramp."
      />
      <StatusBanner />
      <Card>
        <CardContent className="grid gap-3 py-4 sm:grid-cols-2 lg:grid-cols-3">
          <NumberField label="Horizon (weeks)" value={horizon} onChange={setHorizon} min={1} max={520} />
          <NumberField label="Seeds" value={seeds} onChange={setSeeds} min={1} max={30} />
          <NumberField label="Initial stock fraction" value={stock} onChange={setStock} min={0} max={1.5} step={0.05} />
          <NumberField label="Weekly demand" value={demand} onChange={setDemand} min={1} max={5000} />
          <NumberField label="Discount γ" value={discount} onChange={setDiscount} min={0.01} max={1} step={0.01} />
          <NumberField label="UCB coefficient c" value={ucb} onChange={setUcb} min={0.01} max={5} step={0.01} />
        </CardContent>
      </Card>
      <div className="my-4 flex flex-wrap gap-2">
        {POLICIES.map((policy) => {
          const on = selected.includes(policy.id);
          return (
            <button
              key={policy.id}
              type="button"
              onClick={() =>
                setSelected((current) =>
                  current.includes(policy.id) ? current.filter((id) => id !== policy.id) : [...current, policy.id],
                )
              }
              className={`rounded-full border px-3 py-1 text-xs ${on ? "border-ink bg-ink text-paper" : "border-line bg-white text-muted"}`}
            >
              {policy.name}
            </button>
          );
        })}
      </div>
      {formError && <p className="mb-3 text-sm text-burgundy">{formError}</p>}
      <div className="flex flex-wrap gap-2">
        <Button onClick={quick} disabled={loading}>
          Quick simulation
        </Button>
        <Button variant="burgundy" onClick={full} disabled={loading}>
          Full evaluation
        </Button>
        <Button variant="outline" onClick={custom} disabled={loading}>
          Run selected policies
        </Button>
      </div>
      {result && (
        <p className="mt-4 text-sm text-muted">
          Latest result: {result.parameters.horizon} weeks, seeds {result.parameters.seeds.join(", ")},{" "}
          {num(result.runtime_ms, 0)} ms, {result.policies.length} policies. Open Policies or Overview to read it.
        </p>
      )}
      <Card className="mt-6">
        <CardHeader>
          <CardTitle>Discount-factor sensitivity</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="mb-3 flex flex-wrap gap-2">
            <Button variant="outline" size="sm" disabled={sensLoading} onClick={() => void runSensitivity("quick")}>
              Quick sensitivity
            </Button>
            <Button variant="outline" size="sm" disabled={sensLoading} onClick={() => void runSensitivity("full")}>
              Full sensitivity
            </Button>
          </div>
          {sensLoading && <p className="text-sm text-muted">Running discounted UCB and Thompson Sampling across the gamma grid.</p>}
          {sensError && <p className="text-sm text-burgundy">{sensError}</p>}
          {sensitivity && (
            <>
              <p className="mb-3 text-xs leading-5 text-muted">
                {sensitivity.note} Runtime {num(sensitivity.runtime_ms, 0)} ms. Horizon {sensitivity.horizon}, seeds{" "}
                {sensitivity.seeds.join(", ")}.
              </p>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={sensChart}>
                    <CartesianGrid stroke="#efeae4" vertical={false} />
                    <XAxis dataKey="gamma" tick={{ fontSize: 11, fill: "#6d645c" }} />
                    <YAxis tick={{ fontSize: 11, fill: "#6d645c" }} unit="%" />
                    <Tooltip />
                    <Line type="monotone" dataKey="discounted_ucb" name="Discounted UCB" stroke="#8d3b3b" dot isAnimationActive={false} />
                    <Line type="monotone" dataKey="discounted_thompson" name="Thompson" stroke="#1c2834" dot isAnimationActive={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
              <Table>
                <thead>
                  <tr>
                    <Th>Policy</Th>
                    <Th>γ</Th>
                    <Th>Reward</Th>
                    <Th>vs rotation</Th>
                    <Th>O−</Th>
                  </tr>
                </thead>
                <tbody>
                  {sensitivity.rows.map((row) => (
                    <tr key={`${row.policy}-${row.discount}`}>
                      <Td>{row.name}</Td>
                      <Td>{row.discount ?? "—"}</Td>
                      <Td>{num(row.mean_cumulative_reward, 1)}</Td>
                      <Td>{pct(row.improvement_vs_fixed)}</Td>
                      <Td>{num(row.mean_o_negative_units, 1)}</Td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function NumberField({
  label,
  value,
  onChange,
  min,
  max,
  step,
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
  min: number;
  max: number;
  step?: number;
}) {
  return (
    <label className="block">
      <Label>{label}</Label>
      <Input
        className="mt-1"
        type="number"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
      />
    </label>
  );
}
