"use client";

import Link from "next/link";
import { useState } from "react";

import { usePlan } from "@/components/plan-context";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input, Label, Select } from "@/components/ui/input";
import { ARMS, BLOOD_TYPES, POLICIES } from "@/lib/labels";
import {
  BLOOD_LABELS,
  OBJECTIVES,
  POLICY_HELP,
  demoForm,
  parseInventoryCsv,
  type CsvPreview,
  type PlanForm,
} from "@/lib/plan";

function today() {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${now.getFullYear()}-${month}-${day}`;
}

function FieldNote({ message }: { message?: string }) {
  if (!message) return null;
  return <p className="text-sm text-burgundy">{message}</p>;
}

export default function PlanPage() {
  const { ready, form, setForm, updateForm, fieldErrors, error, loading, submit, reset } = usePlan();
  const [preview, setPreview] = useState<CsvPreview | null>(null);
  const [fileName, setFileName] = useState("");

  if (!ready) {
    return <p className="text-sm text-muted">Loading your draft…</p>;
  }

  function setLevel(kind: "stock" | "target", type: (typeof BLOOD_TYPES)[number], value: string) {
    updateForm({
      usingDemo: false,
      [kind]: { ...form[kind], [type]: value },
    });
  }

  function toggleArm(id: string) {
    const arms = form.arms.includes(id) ? form.arms.filter((arm) => arm !== id) : [...form.arms, id];
    updateForm({ arms, usingDemo: form.usingDemo });
  }

  async function onFile(file: File | undefined) {
    if (!file) return;
    setFileName(file.name);
    const text = await file.text();
    setPreview(parseInventoryCsv(text));
  }

  function applyPreview() {
    if (!preview || preview.errors.length > 0) return;
    const next: PlanForm = {
      ...form,
      usingDemo: false,
      stock: { ...form.stock, ...preview.stock },
      target: { ...form.target, ...preview.target },
    };
    setForm(next);
    setPreview(null);
    setFileName("");
    const input = document.getElementById("inventory-csv");
    if (input instanceof HTMLInputElement) input.value = "";
  }

  return (
    <div className="space-y-6">
      <div className="max-w-3xl">
        <p className="text-xs font-medium uppercase tracking-[0.16em] text-burgundy">Plan a drive</p>
        <h1 className="mt-2 font-serif text-4xl text-ink">Tell us what your blood bank has.</h1>
        <p className="mt-3 text-base leading-relaxed text-muted">
          Enter your stock, the drives you can run, and how much blood you expect to need. The
          recommendation comes from the simulator, not from a made-up answer in the page.
        </p>
      </div>

      {form.usingDemo ? (
        <p className="rounded-lg border border-line bg-white px-4 py-3 text-sm text-ink">
          These are sample numbers for a practice run. They are not a real hospital’s inventory.
        </p>
      ) : null}

      {error ? (
        <p className="rounded-lg border border-burgundy/30 bg-white px-4 py-3 text-sm text-burgundy" role="alert">
          {error}
        </p>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>Your blood bank</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <div className="space-y-1.5 md:col-span-2">
            <Label htmlFor="facility" className="normal-case tracking-normal text-sm text-ink">
              Blood bank or facility name
            </Label>
            <Input
              id="facility"
              value={form.facilityName}
              onChange={(event) => updateForm({ facilityName: event.target.value })}
              placeholder="Optional"
              maxLength={120}
              aria-invalid={Boolean(fieldErrors.facilityName)}
            />
            <FieldNote message={fieldErrors.facilityName} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="planning-date" className="normal-case tracking-normal text-sm text-ink">
              Planning date
            </Label>
            <Input
              id="planning-date"
              type="date"
              value={form.planningDate}
              onChange={(event) => updateForm({ planningDate: event.target.value })}
              aria-invalid={Boolean(fieldErrors.planningDate)}
              required
            />
            <p className="text-sm text-muted">
              The date sets the time of year for campus breaks, festivals, and workplace campaigns.
              It does not change the community-centre slowdown or the tech-park opening. Those follow
              the number of weeks in this plan.
            </p>
            <FieldNote message={fieldErrors.planningDate} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="horizon" className="normal-case tracking-normal text-sm text-ink">
              Planning length
            </Label>
            <Input
              id="horizon"
              type="number"
              min={1}
              max={104}
              step={1}
              value={form.horizon}
              onChange={(event) => updateForm({ horizon: event.target.value })}
              aria-invalid={Boolean(fieldErrors.horizon)}
            />
            <p className="text-sm text-muted">How many weeks the simulator should practice before it recommends the next drive.</p>
            <FieldNote message={fieldErrors.horizon} />
          </div>
          <div className="space-y-1.5 md:col-span-2">
            <Label htmlFor="demand" className="normal-case tracking-normal text-sm text-ink">
              Expected weekly demand
            </Label>
            <Input
              id="demand"
              type="number"
              min={0}
              step="any"
              value={form.weeklyDemand}
              onChange={(event) => updateForm({ weeklyDemand: event.target.value, usingDemo: false })}
              aria-invalid={Boolean(fieldErrors.weeklyDemand)}
              placeholder="Units per week"
            />
            <p className="text-sm text-muted">Total units you expect patients to need each week, across all blood types.</p>
            <FieldNote message={fieldErrors.weeklyDemand} />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Blood you have now</CardTitle>
          <p className="text-sm text-muted">Enter units on the shelf and the stock level you want to hold. Do not enter donor names.</p>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                setForm(demoForm(form.planningDate || today()));
                setPreview(null);
              }}
            >
              Load demo data
            </Button>
            <Button type="button" variant="outline" onClick={reset}>
              Reset form
            </Button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[36rem] text-sm">
              <thead>
                <tr className="border-b border-line text-left text-muted">
                  <th className="py-2 pr-3 font-medium">Blood type</th>
                  <th className="py-2 pr-3 font-medium">Current stock</th>
                  <th className="py-2 font-medium">Target stock</th>
                </tr>
              </thead>
              <tbody>
                {BLOOD_TYPES.map((type) => (
                  <tr key={type} className="border-b border-line/80">
                    <th className="py-2 pr-3 text-left font-medium text-ink">{BLOOD_LABELS[type]}</th>
                    <td className="py-2 pr-3">
                      <Input
                        aria-label={`Current ${BLOOD_LABELS[type]} stock`}
                        type="number"
                        min={0}
                        step="any"
                        value={form.stock[type]}
                        onChange={(event) => setLevel("stock", type, event.target.value)}
                        aria-invalid={Boolean(fieldErrors[`stock.${type}`])}
                      />
                      <FieldNote message={fieldErrors[`stock.${type}`]} />
                    </td>
                    <td className="py-2">
                      <Input
                        aria-label={`${BLOOD_LABELS[type]} target stock`}
                        type="number"
                        min={0}
                        step="any"
                        value={form.target[type]}
                        onChange={(event) => setLevel("target", type, event.target.value)}
                        aria-invalid={Boolean(fieldErrors[`target.${type}`])}
                      />
                      <FieldNote message={fieldErrors[`target.${type}`]} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="space-y-2 rounded-md border border-line bg-paper/60 p-4">
            <Label htmlFor="inventory-csv" className="normal-case tracking-normal text-sm text-ink">
              Or upload a CSV
            </Label>
            <p className="text-sm text-muted">
              Use columns named blood type, current stock, and target stock. Nothing is applied until you confirm the preview.
            </p>
            <Input
              id="inventory-csv"
              type="file"
              accept=".csv,text/csv"
              onChange={(event) => onFile(event.target.files?.[0])}
            />
            {fileName ? <p className="text-sm text-ink">{fileName}</p> : null}
            {preview ? (
              <div className="space-y-3">
                {preview.errors.map((item) => (
                  <p key={item} className="text-sm text-burgundy">
                    {item}
                  </p>
                ))}
                {preview.notes.map((item) => (
                  <p key={item} className="text-sm text-muted">
                    {item}
                  </p>
                ))}
                {preview.errors.length === 0 ? (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-line text-left text-muted">
                          <th className="py-1 pr-3 font-medium">Blood type</th>
                          <th className="py-1 pr-3 font-medium">Stock in file</th>
                          <th className="py-1 font-medium">Target in file</th>
                        </tr>
                      </thead>
                      <tbody>
                        {BLOOD_TYPES.filter((type) => preview.stock[type] != null || preview.target[type] != null).map(
                          (type) => (
                            <tr key={type} className="border-b border-line/80">
                              <td className="py-1 pr-3">{BLOOD_LABELS[type]}</td>
                              <td className="py-1 pr-3">{preview.stock[type] ?? "—"}</td>
                              <td className="py-1">{preview.target[type] ?? "—"}</td>
                            </tr>
                          ),
                        )}
                      </tbody>
                    </table>
                  </div>
                ) : null}
                <Button type="button" variant="outline" disabled={preview.errors.length > 0} onClick={applyPreview}>
                  Use these numbers
                </Button>
              </div>
            ) : null}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Drives you can run</CardTitle>
          <p className="text-sm text-muted">Turn off any site or time that is not an option for you.</p>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="flex gap-2">
            <Button type="button" variant="ghost" onClick={() => updateForm({ arms: ARMS.map((arm) => arm.id) })}>
              Choose all
            </Button>
            <Button type="button" variant="ghost" onClick={() => updateForm({ arms: [] })}>
              Clear
            </Button>
          </div>
          <fieldset className="grid gap-2 sm:grid-cols-2">
            <legend className="sr-only">Eligible drives</legend>
            {ARMS.map((arm) => (
              <label key={arm.id} className="flex items-center gap-2 rounded-md border border-line bg-white px-3 py-2 text-sm">
                <input
                  type="checkbox"
                  checked={form.arms.includes(arm.id)}
                  onChange={() => toggleArm(arm.id)}
                />
                {arm.name}
              </label>
            ))}
          </fieldset>
          <FieldNote message={fieldErrors.arms} />

          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="policy" className="normal-case tracking-normal text-sm text-ink">
                Algorithm
              </Label>
              <Select
                id="policy"
                value={form.policy}
                onChange={(event) => updateForm({ policy: event.target.value as PlanForm["policy"] })}
              >
                {POLICIES.map((policy) => (
                  <option key={policy.id} value={policy.id}>
                    {policy.name}
                  </option>
                ))}
              </Select>
              <p className="text-sm text-muted">{POLICY_HELP[form.policy]}</p>
            </div>
            <fieldset className="space-y-2">
              <legend className="text-sm font-medium text-ink">What should the score favour?</legend>
              {OBJECTIVES.map((objective) => (
                <label key={objective.id} className="block rounded-md border border-line px-3 py-2 text-sm">
                  <span className="flex items-center gap-2 font-medium">
                    <input
                      type="radio"
                      name="objective"
                      checked={form.objective === objective.id}
                      onChange={() => updateForm({ objective: objective.id })}
                    />
                    {objective.label}
                  </span>
                  <span className="mt-1 block pl-6 text-muted">{objective.help}</span>
                </label>
              ))}
            </fieldset>
          </div>

          <details className="rounded-md border border-line px-4 py-3">
            <summary className="cursor-pointer text-sm font-medium">More settings</summary>
            <div className="mt-3 grid gap-4 md:grid-cols-2">
              <div className="space-y-1.5">
                <Label htmlFor="discount" className="normal-case tracking-normal text-sm text-ink">
                  How much old weeks fade
                </Label>
                <Input
                  id="discount"
                  type="number"
                  min={0.01}
                  max={1}
                  step="0.01"
                  value={form.discount}
                  onChange={(event) => updateForm({ discount: event.target.value })}
                  aria-invalid={Boolean(fieldErrors.discount)}
                />
                <p className="text-sm text-muted">
                  1 keeps every week. 0.95 lets older weeks matter less. Used by Discounted UCB and Discounted Thompson Sampling.
                </p>
                <FieldNote message={fieldErrors.discount} />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="ucb" className="normal-case tracking-normal text-sm text-ink">
                  Extra push for less-used drives
                </Label>
                <Input
                  id="ucb"
                  type="number"
                  min={0.01}
                  max={5}
                  step="0.01"
                  value={form.ucbC}
                  onChange={(event) => updateForm({ ucbC: event.target.value })}
                  aria-invalid={Boolean(fieldErrors.ucbC)}
                />
                <p className="text-sm text-muted">Used by UCB1 and Discounted UCB. Higher means more tries of drives with little history.</p>
                <FieldNote message={fieldErrors.ucbC} />
              </div>
            </div>
          </details>
        </CardContent>
      </Card>

      <div className="flex flex-wrap items-center gap-3">
        <Button type="button" variant="burgundy" size="lg" onClick={submit} disabled={loading}>
          {loading ? "Working…" : "Generate Drive Recommendation"}
        </Button>
        <Link href="/planner" className="text-sm text-muted underline-offset-4 hover:underline">
          Open the technical planner
        </Link>
      </div>
    </div>
  );
}
