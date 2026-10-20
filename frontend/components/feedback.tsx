"use client";

import { Button } from "@/components/ui/button";
import { useExperiment } from "@/components/experiment-context";

export function PageHeader({
  eyebrow,
  title,
  lede,
}: {
  eyebrow: string;
  title: string;
  lede: string;
}) {
  return (
    <header className="mb-6 max-w-3xl">
      <p className="text-[11px] font-medium uppercase tracking-[0.16em] text-burgundy">{eyebrow}</p>
      <h1 className="mt-1 font-serif text-3xl font-medium tracking-tight text-ink">{title}</h1>
      <p className="mt-2 text-sm leading-6 text-muted">{lede}</p>
    </header>
  );
}

export function StatusBanner() {
  const { loading, error, demo, notice, status, elapsedMs, loadDemo } = useExperiment();
  if (!loading && !error && !demo) return null;
  return (
    <div className="mb-5 rounded-lg border border-line bg-white px-4 py-3 text-sm">
      {loading && (
        <div>
          <div className="mb-2 h-1 overflow-hidden rounded-full bg-paper">
            <div className="h-full w-1/3 animate-pulse bg-burgundy" />
          </div>
          <p className="text-ink">
            {status}. Waiting on the simulator · {(elapsedMs / 1000).toFixed(1)}s
          </p>
        </div>
      )}
      {error && (
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-burgundy">{error}</p>
          <Button variant="outline" size="sm" onClick={() => void loadDemo()}>
            Load labeled demo snapshot
          </Button>
        </div>
      )}
      {demo && notice && !loading && (
        <p>
          <span className="font-medium text-burgundy">Demo snapshot.</span>{" "}
          <span className="text-muted">{notice}</span>
        </p>
      )}
    </div>
  );
}
