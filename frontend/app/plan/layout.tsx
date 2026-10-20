"use client";

import { PlanProvider } from "@/components/plan-context";
import type { ReactNode } from "react";

export default function PlanLayout({ children }: { children: ReactNode }) {
  return <PlanProvider>{children}</PlanProvider>;
}
