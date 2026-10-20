"use client";

import { useEffect, useState } from "react";

import { useExperiment } from "@/components/experiment-context";
import { PageHeader, StatusBanner } from "@/components/feedback";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input, Label, Select } from "@/components/ui/input";
import { api, ApiError } from "@/lib/api";
import { num } from "@/lib/format";
import { POLICIES, type PolicyId } from "@/lib/labels";
import type { ArmCatalog, ArmEstimate, Recommendation } from "@/lib/types";

export default function PlannerPage() {
  const { demo, snapshot } = useExperiment();
  const [catalog, setCatalog] = useState<ArmEstimate[]>([]);
  const [catalogNote, setCatalogNote] = useState<string | null>(null);
  const [policy, setPolicy] = useState<PolicyId>("discounted_ucb");
  const [horizon, setHorizon] = useState(52);
  const [seed, setSeed] = useState(0);
  const [discount, setDiscount] = useState(0.95);
  const [ucb, setUcb] = useState(0.1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [usingDemo, setUsingDemo] = useState(false);
  const [recommendation, setRecommendation] = useState<Recommendation | null>(null);

  useEffect(() => {
    api<ArmCatalog>("/api/v1/arms?week=1")
      .then((payload) => {
        setCatalog(payload.arms);
        setCatalogNote(payload.arms[0]?.expected_reward_note ?? null);
      })
      .catch((caught) => {
        setCatalogNote(caught instanceof ApiError ? caught.message : "Arm catalogue unavailable.");
      });
  }, []);

  const cards = recommendation?.arms ?? catalog;

  async function recommend() {
    setLoading(true);
    setError(null);
    setUsingDemo(false);
    try {
      const payload = await api<Recommendation>("/api/v1/recommend", {
        method: "POST",
        body: JSON.stringify({
          policy,
          horizon,
          seed,
          discount,
          ucb_c: ucb,
        }),
      });
      setRecommendation(payload);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Recommendation failed.");
    } finally {
      setLoading(false);
    }
  }

  function showDemoRecommendation() {
    if (!snapshot?.recommendation) {
      setError("Load the demo snapshot from the banner first. It contains one precomputed recommendation.");
      return;
    }
    setRecommendation(snapshot.recommendation);
    setUsingDemo(true);
    setError(null);
  }

  return (
    <div>
      <PageHeader
        eyebrow="Drive planner"
        title="Next drive from algorithm statistics"
        lede="Expected turnout is the binomial mean. Expected reward is a mean-field calculation at the current shortage. Neither is a promised collection."
      />
      <StatusBanner />
      <Card className="mb-4">
        <CardContent className="grid gap-3 py-4 sm:grid-cols-2 lg:grid-cols-6">
          <Field label="Algorithm">
            <Select value={policy} onChange={(event) => setPolicy(event.target.value as PolicyId)}>
              {POLICIES.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="History weeks">
            <Input type="number" min={1} max={520} value={horizon} onChange={(event) => setHorizon(Number(event.target.value))} />
          </Field>
          <Field label="Seed">
            <Input type="number" min={0} value={seed} onChange={(event) => setSeed(Number(event.target.value))} />
          </Field>
          <Field label="Discount">
            <Input type="number" min={0.01} max={1} step={0.01} value={discount} onChange={(event) => setDiscount(Number(event.target.value))} />
          </Field>
          <Field label="UCB c">
            <Input type="number" min={0.01} max={5} step={0.01} value={ucb} onChange={(event) => setUcb(Number(event.target.value))} />
          </Field>
          <div className="flex items-end">
            <Button className="w-full" onClick={() => void recommend()} disabled={loading}>
              {loading ? "Scoring arms" : "Recommend next drive"}
            </Button>
          </div>
        </CardContent>
      </Card>
      {error && (
        <div className="mb-4 flex flex-col gap-3 rounded-lg border border-line bg-white px-4 py-3 text-sm sm:flex-row sm:items-center sm:justify-between">
          <p className="text-burgundy">{error}</p>
          <Button variant="outline" size="sm" onClick={showDemoRecommendation} disabled={!demo && !snapshot}>
            Use demo recommendation
          </Button>
        </div>
      )}
      {recommendation && (
        <Card className="mb-4">
          <CardHeader>
            <CardTitle>
              {recommendation.policy_name} · week {recommendation.decision_week}
              {usingDemo ? " · demo snapshot" : ""}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm leading-6 text-ink">{recommendation.explanation}</p>
            <p className="mt-2 text-xs leading-5 text-muted">{recommendation.note}</p>
          </CardContent>
        </Card>
      )}
      {!recommendation && catalogNote && <p className="mb-3 text-xs text-muted">{catalogNote}</p>}
      <div className="grid gap-3 md:grid-cols-2">
        {cards.map((arm) => (
          <ArmCard key={arm.id} arm={arm} chosen={recommendation?.recommended_arm_id === arm.id} live={Boolean(recommendation)} />
        ))}
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <Label>{label}</Label>
      <div className="mt-1">{children}</div>
    </label>
  );
}

function ArmCard({ arm, chosen, live }: { arm: ArmEstimate; chosen: boolean; live: boolean }) {
  const reward = live ? arm.expected_reward : arm.expected_reward_at_initial_stock;
  return (
    <Card className={chosen ? "border-burgundy" : ""}>
      <CardHeader>
        <CardTitle>
          {arm.name}
          {chosen ? " · recommended" : ""}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2 text-sm">
        <p className="text-muted">Tier {arm.tier} · pool {arm.pool} · multiplier ×{num(arm.seasonal_multiplier, 2)}</p>
        <div className="grid grid-cols-2 gap-2 text-xs">
          <Metric label="Expected turnout" value={num(arm.expected_turnout, 1)} />
          <Metric label={live ? "Expected reward" : "Reward at 60% stock"} value={num(reward, 1)} />
          <Metric label="Selection frequency" value={arm.selection_frequency == null ? "—" : `${num(arm.selection_frequency * 100, 1)}%`} />
          <Metric label="Uncertainty" value={arm.uncertainty == null ? "—" : num(arm.uncertainty, 3)} />
          <Metric label="Scaled mean" value={arm.scaled_mean == null ? "—" : num(arm.scaled_mean, 3)} />
          <Metric label="Count" value={arm.count == null ? "—" : num(arm.count, 2)} />
        </div>
        {arm.index != null && <p className="text-xs text-muted">UCB index {num(arm.index, 3)} · bonus {num(arm.bonus, 3)}</p>}
        {arm.sample != null && (
          <p className="text-xs text-muted">
            Thompson sample {num(arm.sample, 3)} · posterior {num(arm.posterior_mean, 3)} ± {num(arm.posterior_std, 3)}
          </p>
        )}
        <p className="text-xs leading-5 text-muted">{arm.pattern}</p>
        {arm.report_table_mean_donors != null && (
          <p className="text-xs text-muted">Report Table 4 lists an illustrative mean of {arm.report_table_mean_donors} donors. The figure above is computed from pool, tier, and season.</p>
        )}
      </CardContent>
    </Card>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="uppercase tracking-[0.12em] text-muted">{label}</p>
      <p className="mt-0.5 tabular-nums text-ink">{value}</p>
    </div>
  );
}
