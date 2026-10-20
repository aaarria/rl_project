"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

import { api, ApiError, loadDemoSnapshot } from "@/lib/api";
import type { Comparison, DemoSnapshot, SimulateBody } from "@/lib/types";

type ExperimentContextValue = {
  result: Comparison | null;
  loading: boolean;
  error: string | null;
  demo: boolean;
  notice: string | null;
  status: string;
  elapsedMs: number;
  snapshot: DemoSnapshot | null;
  run: (body: SimulateBody, status?: string) => Promise<void>;
  loadDemo: () => Promise<void>;
};

const ExperimentContext = createContext<ExperimentContextValue | null>(null);

export function ExperimentProvider({ children }: { children: ReactNode }) {
  const [result, setResult] = useState<Comparison | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [demo, setDemo] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [status, setStatus] = useState("Quick evaluation");
  const [elapsedMs, setElapsedMs] = useState(0);
  const [snapshot, setSnapshot] = useState<DemoSnapshot | null>(null);

  async function run(body: SimulateBody, nextStatus = "Running simulation") {
    setLoading(true);
    setError(null);
    setDemo(false);
    setNotice(null);
    setStatus(nextStatus);
    const started = Date.now();
    setElapsedMs(0);
    const timer = window.setInterval(() => setElapsedMs(Date.now() - started), 200);
    try {
      const data = await api<Comparison>("/api/v1/simulate", {
        method: "POST",
        body: JSON.stringify(body),
      });
      setResult(data);
    } catch (caught) {
      const message = caught instanceof ApiError ? caught.message : "The simulation request failed.";
      setError(message);
    } finally {
      window.clearInterval(timer);
      setElapsedMs(Date.now() - started);
      setLoading(false);
    }
  }

  async function loadDemo() {
    setLoading(true);
    setError(null);
    try {
      const data = await loadDemoSnapshot();
      setSnapshot(data);
      setResult(data.result);
      setDemo(true);
      setNotice(data.notice);
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : "The demo snapshot could not be loaded.";
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void run({ preset: "quick" }, "Quick evaluation · 52 weeks · 3 seeds");
  }, []);

  return (
    <ExperimentContext.Provider
      value={{ result, loading, error, demo, notice, status, elapsedMs, snapshot, run, loadDemo }}
    >
      {children}
    </ExperimentContext.Provider>
  );
}

export function useExperiment() {
  const value = useContext(ExperimentContext);
  if (!value) throw new Error("useExperiment must be used inside ExperimentProvider");
  return value;
}
