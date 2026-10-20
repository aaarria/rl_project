"use client";

import Link from "next/link";
import { ArrowRight, Droplets, GitCompare, Scale, ShieldAlert } from "lucide-react";

import { useExperiment } from "@/components/experiment-context";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { num } from "@/lib/format";
import { BLOOD_TYPES } from "@/lib/labels";

const STEPS = [
  {
    number: "1",
    title: "Enter what you have",
    text: "Add your stock, the level you want to hold, and how much blood you expect to need each week.",
  },
  {
    number: "2",
    title: "Choose drives you can run",
    text: "Keep the sites and times that are real options. Turn the others off.",
  },
  {
    number: "3",
    title: "Read the recommendation",
    text: "See one suggested drive, the other options in order, and a plain reason. The numbers are simulated.",
  },
];

const CAPABILITIES = [
  {
    icon: Droplets,
    title: "Inventory monitoring",
    text: "See current stock next to the targets you set, for all eight blood types.",
  },
  {
    icon: Scale,
    title: "Shortage prioritization",
    text: "Types below target can count more, so the plan leans toward what you are short of.",
  },
  {
    icon: ArrowRight,
    title: "Adaptive drive recommendations",
    text: "The algorithm tries the drives you allow and leans toward the ones that scored better.",
  },
  {
    icon: GitCompare,
    title: "Policy comparison",
    text: "Run the same stock through six algorithms and see which drive each one would pick.",
  },
];

export default function HomePage() {
  const { result, loading } = useExperiment();
  const example = result?.policies.find((policy) => policy.id === "discounted_ucb") ?? result?.policies[0];

  return (
    <div className="space-y-14">
      <section className="max-w-3xl">
        <p className="text-xs font-medium uppercase tracking-[0.16em] text-burgundy">Blood bank planning</p>
        <h1 className="mt-3 font-serif text-4xl leading-tight text-ink md:text-5xl">
          Make Every Blood Donation Drive Count.
        </h1>
        <p className="mt-4 text-lg leading-relaxed text-muted">
          An adaptive planning platform that helps blood banks prioritize shortages, evaluate donation-drive options and make more informed scheduling decisions using reinforcement learning.
        </p>
        <div className="mt-6 flex flex-wrap gap-3">
          <Button asChild variant="burgundy" size="lg">
            <Link href="/plan">Plan a Blood Drive</Link>
          </Button>
          <Button asChild variant="outline" size="lg">
            <Link href="/overview">Explore Analytics</Link>
          </Button>
        </div>
        <p className="mt-6 flex gap-3 rounded-lg border border-burgundy/30 bg-white px-4 py-3 text-sm leading-relaxed text-ink">
          <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-burgundy" aria-hidden />
          <span>
            The current system uses simulated outcomes. It is not clinically validated, and it does not guarantee how many donors will attend.
          </span>
        </p>
      </section>

      <section>
        <h2 className="font-serif text-2xl text-ink">How it works</h2>
        <div className="mt-4 grid gap-4 md:grid-cols-3">
          {STEPS.map((step) => (
            <Card key={step.number}>
              <CardHeader>
                <p className="text-sm font-medium text-burgundy">Step {step.number}</p>
                <CardTitle className="text-base">{step.title}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm leading-relaxed text-muted">{step.text}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      <section>
        <h2 className="font-serif text-2xl text-ink">What you can do</h2>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          {CAPABILITIES.map((item) => {
            const Icon = item.icon;
            return (
              <Card key={item.title}>
                <CardHeader>
                  <Icon className="h-4 w-4 text-burgundy" aria-hidden />
                  <CardTitle className="text-base">{item.title}</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm leading-relaxed text-muted">{item.text}</p>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
        <Card>
          <CardHeader>
            <CardTitle>Example from the simulator</CardTitle>
            <p className="text-sm text-muted">
              A short practice run, not your hospital. Stock here starts from the simulator’s own assumptions.
            </p>
          </CardHeader>
          <CardContent>
            {example ? (
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-line text-left text-muted">
                    <th className="py-2 pr-3 font-medium">Blood type</th>
                    <th className="py-2 pr-3 font-medium">Simulated stock</th>
                    <th className="py-2 font-medium">Share of target</th>
                  </tr>
                </thead>
                <tbody>
                  {BLOOD_TYPES.map((type) => {
                    const stock = example.final_stock_mean[type] ?? 0;
                    const target = example.target_stock[type] || 1;
                    return (
                      <tr key={type} className="border-b border-line/80">
                        <td className="py-2 pr-3">{type}</td>
                        <td className="py-2 pr-3">{num(stock, 1)}</td>
                        <td className="py-2">{num((stock / target) * 100, 0)}%</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            ) : (
              <p className="text-sm text-muted">
                {loading
                  ? "A short practice run is still finishing. The example will appear here when it does."
                  : "The example appears when the simulator is available. Your own plan does not depend on it."}
              </p>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>How the learning works</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm leading-relaxed text-muted">
            <p>
              The planner does not look up a fixed answer. It plays through your planning period one week at a time.
            </p>
            <p>
              Each week it picks one drive you allowed, sees a simulated collection, and updates that drive’s score. It only learns from the drive it picked.
            </p>
            <p>
              Drives that have not been tried much can still be chosen, so one lucky week does not decide the plan. After the practice weeks, it recommends the drive with the best score for the following week.
            </p>
            <p>
              <Link href="/methodology" className="text-ink underline-offset-4 hover:underline">
                Read the method
              </Link>
            </p>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
