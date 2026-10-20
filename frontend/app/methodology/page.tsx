"use client";

import { useEffect, useState } from "react";

import { PageHeader } from "@/components/feedback";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import type { AppConfig } from "@/lib/types";

const ALGORITHMS = [
  {
    name: "Fixed Rotation",
    body: "Plays arm t mod 8. It ignores rewards. This is the baseline the other policies are compared with.",
  },
  {
    name: "Random",
    body: "Draws an arm uniformly. The draw is seeded. Recorded rewards are not used to choose the next arm.",
  },
  {
    name: "Greedy",
    body: "Tries each arm once, then always plays the highest undiscounted mean. It has no way back if that arm later declines.",
  },
  {
    name: "UCB1",
    body: "Plays the arm with the highest mean plus c · sqrt(2 ln N / n). Unvisited arms are tried first. Counts never fade, so early evidence keeps full weight.",
  },
  {
    name: "Discounted UCB",
    body: "Same index as UCB1, with counts and reward sums multiplied by gamma each week. At gamma = 1 it matches UCB1.",
  },
  {
    name: "Discounted Thompson Sampling",
    body: "Draws each arm from a Gaussian posterior. The mean is (discounted reward sum + 0.5) / (discounted count + 1), and the standard deviation is 0.1 / sqrt(count + 1).",
  },
];

export default function MethodologyPage() {
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [configError, setConfigError] = useState<string | null>(null);

  useEffect(() => {
    api<AppConfig>("/api/v1/config")
      .then(setConfig)
      .catch((caught) => setConfigError(caught instanceof Error ? caught.message : "Configuration unavailable."));
  }, []);

  return (
    <div>
      <PageHeader
        eyebrow="Methodology"
        title="How the simulator decides"
        lede="The design follows the attached project report. Numbers on the other pages are computed here. They are not copied from the report's result table."
      />
      <div className="space-y-4">
        <Card>
          <CardHeader>
            <CardTitle>One simulated week</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm leading-6 text-muted">
            <p>
              Eight drive configurations are the arms. Stock of eight ABO/Rh types is the state. The reward depends on that stock, so the problem sits between a bandit and a Markov decision process. The policies still treat it as a bandit: they see only the reward of the arm they chose.
            </p>
            <ol className="list-decimal space-y-1 pl-4 text-ink">
              {(config?.week_order ?? [
                "Shortage is computed from current stock, before collection.",
                "The policy selects one arm.",
                "Turnout is binomial and the blood-type mix is multinomial.",
                "Raw reward uses units, priority, and current shortage.",
                "The policy updates only the selected arm, on reward / 100.",
                "Demand is drawn, wastage hits stock on hand, and inventory is floored at zero.",
              ]).map((step) => (
                <li key={step}>{step}</li>
              ))}
            </ol>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Reward</CardTitle>
          </CardHeader>
          <CardContent className="text-sm leading-6">
            <p className="font-mono text-xs text-ink">
              {config?.reward.formula ?? "reward = sum(units[k] * priority[k] * (0.1 + shortage[k]))"}
            </p>
            <p className="mt-3 text-muted">
              Priorities are O-negative 2.0, A-negative 1.3, B-negative and AB-negative 1.5, and 1.0 for the other four types. The 0.1 floor keeps a small value on a type that is already at target. Charts and tables show this raw sum. The six learners divide it by{" "}
              {config?.reward.scale_used_by_learners ?? 100} before updating their means, so the UCB bonus sits on a comparable scale.
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Six policies</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {ALGORITHMS.map((item) => (
              <div key={item.name}>
                <p className="text-sm font-medium text-ink">{item.name}</p>
                <p className="text-sm leading-6 text-muted">{item.body}</p>
              </div>
            ))}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Exploration, drift, and discounting</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm leading-6 text-muted">
            <p>
              Exploration tries an arm whose mean is still uncertain. Exploitation plays the current best estimate. UCB explores through the bonus, which shrinks as the count grows. Thompson Sampling explores by drawing from the posterior. Greedy stops exploring after the first pass.
            </p>
            <p>
              The arms are non-stationary. Campus turnout falls in breaks, corporate lunch peaks in two campaign windows, the mall peaks in a festival window, the community centre decays after week 30, and Tech-Park Evening stays small until week 40 and then ramps. A method that never forgets can stay stuck on an arm that was good early.
            </p>
            <p>
              Discounting multiplies old counts and reward sums by gamma each week. The effective memory is about 1 / (1 − gamma). The lab can rerun the two discounted policies across a grid of gamma, including gamma = 1, which turns discounted UCB back into UCB1.
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Evaluation</CardTitle>
          </CardHeader>
          <CardContent className="text-sm leading-6 text-muted">
            <p>
              The full preset is 104 weeks and seeds 0 through 9, with gamma 0.95 and UCB c = 0.1. Every policy on a seed sees the same pre-drawn turnout, blood-type mix, and demand. Differences come from the arms they choose. A simulator that drew noise only after the choice would give each policy a different random stream, and the ranking could move for that reason alone. The quick preset is 52 weeks and three seeds so the interface can load without the full study.
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>What is measured, and what is assumed</CardTitle>
          </CardHeader>
          <CardContent className="text-sm leading-6 text-muted">
            {configError && <p className="mb-3 text-burgundy">{configError}</p>}
            <ul className="list-disc space-y-2 pl-4">
              {(config?.assumptions ?? [
                "The UCI file has no blood types, locations, or stock.",
                "The e-RaktKosh extract is not in this workspace.",
                "Seasonal windows and the three O-negative-boosted arms are labeled assumptions.",
              ]).map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>References</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm leading-6 text-muted">
            <p>Patel, Sheth, and Srivastav. Adaptive Blood Drive Scheduling: A Multi-Armed Bandit Approach to Reduce Blood Type Shortages. Group 8 project report, included in this workspace as a PDF.</p>
            <p>Yeh, I-Cheng. Blood Transfusion Service Center. UCI Machine Learning Repository, 2008. https://archive.ics.uci.edu/dataset/176/blood+transfusion+service+center</p>
            <p>Yeh, Yang, and Ting. Knowledge discovery on RFM model using Bernoulli sequence. Expert Systems with Applications, 2008/2009.</p>
            <p>Auer, Cesa-Bianchi, and Fischer. Finite-time analysis of the multiarmed bandit problem. Machine Learning, 2002. UCB1.</p>
            <p>Garivier and Moulines. On upper-confidence bound policies for switching bandit problems. ALT, 2011. Discounted UCB.</p>
            <p>Thompson. On the likelihood that one unknown probability exceeds another. Biometrika, 1933. Chapelle and Li. An empirical evaluation of Thompson sampling. NeurIPS, 2011.</p>
            <p>Sutton and Barto. Reinforcement Learning: An Introduction, 2nd ed. MIT Press, 2018.</p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
