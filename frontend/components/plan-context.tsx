"use client";

import { useRouter } from "next/navigation";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { ApiError, api } from "@/lib/api";
import {
  emptyForm,
  toPlanRequest,
  validatePlan,
  type PlanCompare,
  type PlanForm,
  type PlanRequestBody,
  type PlanResult,
} from "@/lib/plan";

const STORAGE_KEY = "blood-drive-plan-v1";

type PlanContextValue = {
  ready: boolean;
  form: PlanForm;
  setForm: (form: PlanForm) => void;
  updateForm: (patch: Partial<PlanForm>) => void;
  result: PlanResult | null;
  compare: PlanCompare | null;
  fieldErrors: Record<string, string>;
  error: string | null;
  loading: boolean;
  comparing: boolean;
  submit: () => Promise<void>;
  comparePolicies: (body?: PlanRequestBody) => Promise<void>;
  reset: () => void;
};

const PlanContext = createContext<PlanContextValue | null>(null);

export function PlanProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const [form, setForm] = useState<PlanForm>(emptyForm);
  const [result, setResult] = useState<PlanResult | null>(null);
  const [compare, setCompare] = useState<PlanCompare | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [comparing, setComparing] = useState(false);

  useEffect(() => {
    try {
      const saved = sessionStorage.getItem(STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved) as {
          form?: PlanForm;
          result?: PlanResult;
          compare?: PlanCompare;
        };
        if (parsed.form?.stock && parsed.form.target) setForm(parsed.form);
        if (parsed.result?.recommended) setResult(parsed.result);
        if (parsed.compare?.rows) setCompare(parsed.compare);
      }
    } catch {
      sessionStorage.removeItem(STORAGE_KEY);
    }
    setReady(true);
  }, []);

  useEffect(() => {
    if (!ready) return;
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ form, result, compare }));
  }, [ready, form, result, compare]);

  const replaceForm = useCallback((next: PlanForm) => {
    setForm(next);
    setFieldErrors({});
    setError(null);
  }, []);

  const updateForm = useCallback((patch: Partial<PlanForm>) => {
    setForm((current) => ({ ...current, ...patch }));
    setFieldErrors({});
    setError(null);
  }, []);

  const submit = useCallback(async () => {
    const errors = validatePlan(form);
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) {
      setError("Check the highlighted fields, then try again.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const next = await api<PlanResult>("/api/v1/plan", {
        method: "POST",
        body: JSON.stringify(toPlanRequest(form)),
      });
      setResult(next);
      setCompare(null);
      router.push("/plan/results");
    } catch (caught) {
      const message = caught instanceof ApiError ? caught.message : "The recommendation could not be created.";
      setError(
        message.includes("demo snapshot")
          ? "We could not reach the planning service. Check that it is running, then try again."
          : message,
      );
    } finally {
      setLoading(false);
    }
  }, [form, router]);

  const comparePolicies = useCallback(async (body?: PlanRequestBody) => {
    if (!body) {
      const errors = validatePlan(form);
      setFieldErrors(errors);
      if (Object.keys(errors).length > 0) {
        setError("The saved inputs are incomplete, so the comparison did not run.");
        return;
      }
    }
    setComparing(true);
    setError(null);
    try {
      const next = await api<PlanCompare>("/api/v1/plan/compare", {
        method: "POST",
        body: JSON.stringify(body ?? toPlanRequest(form)),
      });
      setCompare(next);
    } catch (caught) {
      const message = caught instanceof ApiError ? caught.message : "The comparison could not be created.";
      setError(
        message.includes("demo snapshot")
          ? "We could not reach the planning service. Check that it is running, then try again."
          : message,
      );
    } finally {
      setComparing(false);
    }
  }, [form]);

  const reset = useCallback(() => {
    setForm(emptyForm());
    setResult(null);
    setCompare(null);
    setFieldErrors({});
    setError(null);
  }, []);

  const value = useMemo(
    () => ({
      ready,
      form,
      setForm: replaceForm,
      updateForm,
      result,
      compare,
      fieldErrors,
      error,
      loading,
      comparing,
      submit,
      comparePolicies,
      reset,
    }),
    [
      ready,
      form,
      replaceForm,
      updateForm,
      result,
      compare,
      fieldErrors,
      error,
      loading,
      comparing,
      submit,
      comparePolicies,
      reset,
    ],
  );

  return <PlanContext.Provider value={value}>{children}</PlanContext.Provider>;
}

export function usePlan() {
  const value = useContext(PlanContext);
  if (!value) throw new Error("usePlan must be used inside PlanProvider");
  return value;
}
