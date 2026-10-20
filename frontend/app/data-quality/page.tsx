"use client";

import { useEffect, useState } from "react";

import { PageHeader } from "@/components/feedback";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, Td, Th } from "@/components/ui/table";
import { api, ApiError, loadDemoSnapshot } from "@/lib/api";
import { num } from "@/lib/format";
import type { DataQuality } from "@/lib/types";

export default function DataQualityPage() {
  const [report, setReport] = useState<DataQuality | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [demo, setDemo] = useState(false);

  useEffect(() => {
    api<DataQuality>("/api/v1/data-quality")
      .then(setReport)
      .catch((caught) => setError(caught instanceof ApiError ? caught.message : "Data audit failed."));
  }, []);

  async function loadDemoAudit() {
    try {
      const snapshot = await loadDemoSnapshot();
      setReport(snapshot.data_quality);
      setDemo(true);
      setError(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Demo snapshot unavailable.");
    }
  }

  return (
    <div>
      <PageHeader
        eyebrow="Data quality"
        title="What the UCI file actually contains"
        lede="Measured from the local transfusion.data file. Drive locations, blood types, and hospital stock are not in it."
      />
      {error && (
        <div className="mb-4 flex flex-col gap-3 rounded-lg border border-line bg-white px-4 py-3 text-sm sm:flex-row sm:items-center sm:justify-between">
          <p className="text-burgundy">{error}</p>
          <Button variant="outline" size="sm" onClick={() => void loadDemoAudit()}>
            Load labeled demo audit
          </Button>
        </div>
      )}
      {demo && (
        <p className="mb-4 rounded-lg border border-burgundy/30 bg-white px-4 py-3 text-sm text-muted">
          <span className="font-medium text-burgundy">Demo snapshot.</span> This audit was saved from the local file when the snapshot was built. It is not a fresh API read.
        </p>
      )}
      {report && <Audit report={report} />}
    </div>
  );
}

function Audit({ report }: { report: DataQuality }) {
  const positive = report.target.positive_rate * 100;
  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Check label="Rows" ok={report.checks.row_count_748} text={`${report.shape.rows} / 748`} />
        <Check label="Columns" ok={report.checks.five_columns} text={report.shape.column_names.join(", ")} />
        <Check label="Missing cells" ok={report.checks.no_missing_values} text={String(report.missing_and_malformed.malformed_or_non_numeric_cells)} />
        <Check label="Target" ok={report.checks.binary_target} text="0 / 1" />
      </div>
      <Card>
        <CardHeader>
          <CardTitle>Source</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm leading-6 text-muted">
          <p className="text-ink">{report.dataset.citation}</p>
          <p>{report.dataset.paper}</p>
          <p>{report.dataset.geography}</p>
          <p>{report.dataset.target_definition}</p>
          <p className="break-all text-xs">SHA-256 {report.parsing.sha256}</p>
        </CardContent>
      </Card>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>March 2007 target</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="mb-2 flex h-3 overflow-hidden rounded-full bg-paper">
              <div className="bg-burgundy" style={{ width: `${positive}%` }} />
              <div className="bg-ink/80" style={{ width: `${100 - positive}%` }} />
            </div>
            <p className="text-sm text-ink">
              Donated {report.target.donated_march_2007} ({num(positive, 1)}%). Did not donate {report.target.did_not_donate} (
              {num(report.target.negative_rate * 100, 1)}%).
            </p>
            <p className="mt-2 text-xs text-muted">
              The names file says about 24% positive. This file is {num(report.target.positive_rate * 100, 2)}%. {report.target.imbalance}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Duplicates kept</CardTitle>
          </CardHeader>
          <CardContent className="text-sm leading-6">
            <p>Extra copies: {report.duplicates.extra_copies_of_repeated_rows}</p>
            <p>Rows in a duplicate group: {report.duplicates.rows_that_belong_to_a_duplicate_group}</p>
            <p>Unique rows: {report.duplicates.unique_rows}</p>
            <p className="mt-2 text-xs text-muted">{report.duplicates.action}</p>
          </CardContent>
        </Card>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>Descriptive statistics from the file</CardTitle>
        </CardHeader>
        <CardContent className="px-0">
          <Table>
            <thead>
              <tr>
                <Th>Variable</Th>
                <Th>Min</Th>
                <Th>Max</Th>
                <Th>Mean</Th>
                <Th>Sample std</Th>
                <Th>Missing</Th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(report.ranges_and_descriptive_statistics).map(([name, stats]) => (
                <tr key={name}>
                  <Td>{name}</Td>
                  <Td>{num(stats.min, 3)}</Td>
                  <Td>{num(stats.max, 3)}</Td>
                  <Td>{num(stats.mean, 3)}</Td>
                  <Td>{num(stats.std_sample, 3)}</Td>
                  <Td>{stats.missing}</Td>
                </tr>
              ))}
            </tbody>
          </Table>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Names-file table versus this CSV</CardTitle>
        </CardHeader>
        <CardContent className="px-0">
          <Table>
            <thead>
              <tr>
                <Th>Variable</Th>
                <Th>Names mean</Th>
                <Th>File mean</Th>
                <Th>Names std</Th>
                <Th>File std</Th>
              </tr>
            </thead>
            <tbody>
              {report.names_file_comparison.map((row) => (
                <tr key={row.variable}>
                  <Td>{row.variable}</Td>
                  <Td>{num(row.published_mean, 3)}</Td>
                  <Td>{num(row.actual_mean, 3)}</Td>
                  <Td>{num(row.published_std, 3)}</Td>
                  <Td>{num(row.actual_std_sample, 3)}</Td>
                </tr>
              ))}
            </tbody>
          </Table>
          <p className="px-5 pt-3 text-xs text-muted">
            Monetary equals Frequency × 250 on {report.consistency.monetary_not_equal_to_frequency_times_250 === 0 ? "every row" : `${report.consistency.monetary_not_equal_to_frequency_times_250} mismatched rows`}. Time is below Recency on {report.consistency.time_less_than_recency} rows.
          </p>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Loyalty calibration</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="mb-3 text-sm leading-6 text-muted">{report.calibration_note}</p>
          <p className="mb-2 text-xs uppercase tracking-[0.14em] text-muted">Natural frequency bins</p>
          <Table>
            <thead>
              <tr>
                <Th>Bin</Th>
                <Th>n</Th>
                <Th>Donated rate</Th>
              </tr>
            </thead>
            <tbody>
              {report.calibration.natural_frequency_bins.map((row) => (
                <tr key={row.bin}>
                  <Td>{row.bin}</Td>
                  <Td>{row.n}</Td>
                  <Td>{num(row.donated_rate * 100, 2)}%</Td>
                </tr>
              ))}
            </tbody>
          </Table>
          <p className="mb-2 mt-4 text-xs uppercase tracking-[0.14em] text-muted">Equal-count ranks</p>
          <Table>
            <thead>
              <tr>
                <Th>Quartile</Th>
                <Th>n</Th>
                <Th>Frequency</Th>
                <Th>Donated rate</Th>
              </tr>
            </thead>
            <tbody>
              {report.calibration.equal_count_quartiles.map((row) => (
                <tr key={row.quartile}>
                  <Td>{row.quartile}</Td>
                  <Td>{row.n}</Td>
                  <Td>
                    {row.frequency_min}–{row.frequency_max}
                  </Td>
                  <Td>{num(row.donated_rate * 100, 2)}%</Td>
                </tr>
              ))}
            </tbody>
          </Table>
          <p className="mt-3 text-xs text-muted">{report.calibration.middle_tier_note}</p>
        </CardContent>
      </Card>
      <Card className="border-burgundy/40">
        <CardHeader>
          <CardTitle>Not measured from this file</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="list-disc space-y-1 pl-4 text-sm text-ink">
            {report.not_in_this_file.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
          <ul className="mt-3 list-disc space-y-1 pl-4 text-xs leading-5 text-muted">
            {report.limitations.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}

function Check({ label, ok, text }: { label: string; ok: boolean; text: string }) {
  return (
    <Card>
      <CardContent className="px-4 py-4">
        <p className="text-[11px] uppercase tracking-[0.14em] text-muted">{label}</p>
        <p className={`mt-2 text-sm font-medium ${ok ? "text-ink" : "text-burgundy"}`}>{ok ? "Passes" : "Check"}</p>
        <p className="mt-1 text-xs text-muted">{text}</p>
      </CardContent>
    </Card>
  );
}
