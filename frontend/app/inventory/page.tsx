"use client";

import { useMemo, useState } from "react";

import { ShortageLines, StockLines, StockTargetBars } from "@/components/charts";
import { useExperiment } from "@/components/experiment-context";
import { PageHeader, StatusBanner } from "@/components/feedback";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";
import { Table, Td, Th } from "@/components/ui/table";
import { num } from "@/lib/format";
import { BLOOD_TYPES } from "@/lib/labels";

export default function InventoryPage() {
  const { result } = useExperiment();
  const [policyId, setPolicyId] = useState("discounted_ucb");
  const [critical, setCritical] = useState(25);
  const [watch, setWatch] = useState(50);
  const policy = result?.policies.find((item) => item.id === policyId) ?? result?.policies[0];
  const thresholdError = critical >= watch || critical < 0 || watch > 150;

  const rows = useMemo(() => {
    if (!policy) return [];
    return BLOOD_TYPES.map((type) => {
      const stock = policy.final_stock_mean[type] ?? 0;
      const target = policy.target_stock[type] ?? 0;
      const share = target ? stock / target : 0;
      let status = "Stable";
      if (share * 100 < critical) status = "Critical";
      else if (share * 100 < watch) status = "Low";
      return {
        type,
        stock,
        target,
        share,
        shortage: policy.final_shortage_mean[type] ?? 0,
        collected: policy.blood_type_units[type] ?? 0,
        demand: policy.mean_weekly_demand[type] ?? 0,
        status,
      };
    });
  }, [policy, critical, watch]);

  return (
    <div>
      <PageHeader
        eyebrow="Inventory"
        title="Stock, target, and shortage"
        lede="End-of-horizon means from the latest experiment. Shortage is clip(1 − stock / target, 0, 1), the same quantity inside the reward."
      />
      <StatusBanner />
      {policy && (
        <>
          <div className="mb-4 grid gap-3 sm:grid-cols-3">
            <label className="block">
              <Label>Policy</Label>
              <select
                className="mt-1 h-9 w-full rounded-md border border-line bg-white px-2 text-sm"
                value={policy.id}
                onChange={(event) => setPolicyId(event.target.value)}
              >
                {result?.policies.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <Label>Critical below % of target</Label>
              <Input className="mt-1" type="number" min={0} max={100} value={critical} onChange={(event) => setCritical(Number(event.target.value))} />
            </label>
            <label className="block">
              <Label>Low below % of target</Label>
              <Input className="mt-1" type="number" min={1} max={150} value={watch} onChange={(event) => setWatch(Number(event.target.value))} />
            </label>
          </div>
          {thresholdError && <p className="mb-3 text-sm text-burgundy">Set critical below the low threshold, both between 0 and 150.</p>}
          <Card>
            <CardContent className="px-0 pb-2 pt-2">
              <Table>
                <thead>
                  <tr>
                    <Th>Type</Th>
                    <Th>Stock</Th>
                    <Th>Target</Th>
                    <Th>Of target</Th>
                    <Th>Shortage</Th>
                    <Th>Collected</Th>
                    <Th>Weekly demand</Th>
                    <Th>Status</Th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => (
                    <tr key={row.type}>
                      <Td>{row.type}</Td>
                      <Td>{num(row.stock, 1)}</Td>
                      <Td>{num(row.target, 1)}</Td>
                      <Td>{num(row.share * 100, 1)}%</Td>
                      <Td>{num(row.shortage * 100, 1)}%</Td>
                      <Td>{num(row.collected, 1)}</Td>
                      <Td>{num(row.demand, 2)}</Td>
                      <Td>
                        <Badge className={row.status === "Critical" ? "border-burgundy text-burgundy" : ""}>{row.status}</Badge>
                      </Td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            </CardContent>
          </Card>
          <div className="mt-4 grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Final stock and target</CardTitle>
              </CardHeader>
              <CardContent>
                <StockTargetBars policy={policy} />
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Stock vs target over time</CardTitle>
              </CardHeader>
              <CardContent>
                <StockLines policy={policy} types={BLOOD_TYPES} />
              </CardContent>
            </Card>
          </div>
          <Card className="mt-4">
            <CardHeader>
              <CardTitle>Shortage after each week</CardTitle>
            </CardHeader>
            <CardContent>
              <ShortageLines policy={policy} types={BLOOD_TYPES} />
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
