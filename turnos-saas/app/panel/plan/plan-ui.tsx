"use client";

import { useState, useTransition } from "react";
import { changePlan } from "@/app/panel/actions";
import { Button } from "@/components/ui/button";
import {
  PLAN_LIMITS,
  PLAN_ORDER,
  formatPriceArs,
  type PlanTier,
} from "@/lib/plans";

export function PlanSwitcher({ currentPlan }: { currentPlan: PlanTier }) {
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  function handleChange(plan: PlanTier) {
    setError(null);
    startTransition(async () => {
      const result = await changePlan(plan);
      if (!result.ok) setError(result.error ?? "Error");
    });
  }

  return (
    <div>
      {error && <p className="mb-3 text-sm text-danger">{error}</p>}
      <div className="grid gap-4 md:grid-cols-3">
        {PLAN_ORDER.map((tier) => {
          const plan = PLAN_LIMITS[tier];
          const isCurrent = tier === currentPlan;
          return (
            <div
              key={tier}
              className={`card-gradient flex flex-col rounded-xl border p-5 ${
                isCurrent ? "border-primary" : "border-border"
              }`}
            >
              <h3 className="font-semibold">{plan.label}</h3>
              <p className="mt-1 text-2xl font-bold">
                {formatPriceArs(plan.priceArs)}
                {plan.priceArs > 0 && (
                  <span className="text-xs font-normal text-muted"> /mes</span>
                )}
              </p>
              <ul className="mt-3 flex-1 space-y-1.5 text-sm text-muted">
                {plan.features.slice(0, 4).map((f) => (
                  <li key={f}>· {f}</li>
                ))}
              </ul>
              <Button
                variant={isCurrent ? "secondary" : "primary"}
                size="sm"
                className="mt-4"
                disabled={isCurrent || pending}
                onClick={() => handleChange(tier)}
              >
                {isCurrent ? "Plan actual" : `Cambiar a ${plan.label}`}
              </Button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
