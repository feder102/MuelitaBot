import type { Metadata } from "next";
import { Card } from "@/components/ui/card";
import { artMonthStartUtc } from "@/lib/dates";
import { requireBusiness } from "@/lib/get-business";
import { PLAN_LIMITS, formatLimit } from "@/lib/plans";
import { createClient } from "@/lib/supabase/server";
import { PlanSwitcher } from "./plan-ui";

export const metadata: Metadata = { title: "Mi plan" };

function UsageBar({
  label,
  used,
  limit,
}: {
  label: string;
  used: number;
  limit: number;
}) {
  const unlimited = limit === Infinity;
  const ratio = unlimited ? 0 : Math.min(used / limit, 1);
  return (
    <div>
      <div className="mb-1 flex justify-between text-sm">
        <span className="text-muted">{label}</span>
        <span>
          {used} / {unlimited ? "∞" : limit}
        </span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-surface-2">
        <div
          className={`h-full rounded-full ${ratio >= 1 ? "bg-danger" : "bg-primary"}`}
          style={{ width: unlimited ? "4%" : `${Math.max(ratio * 100, 2)}%` }}
        />
      </div>
    </div>
  );
}

export default async function PlanPage() {
  const business = await requireBusiness();
  const supabase = await createClient();
  const limits = PLAN_LIMITS[business.plan];

  const [apptRes, svcRes] = await Promise.all([
    supabase
      .from("appointments")
      .select("id", { count: "exact", head: true })
      .eq("business_id", business.id)
      .neq("status", "CANCELLED")
      .gte("created_at", artMonthStartUtc().toISOString()),
    supabase
      .from("services")
      .select("id", { count: "exact", head: true })
      .eq("business_id", business.id)
      .eq("active", true),
  ]);

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="text-2xl font-bold">Mi plan</h1>
      <p className="mt-1 text-muted">
        Estás en el plan <strong>{limits.label}</strong>.
      </p>

      <Card className="mt-6 space-y-5">
        <h2 className="font-semibold">Uso este mes</h2>
        <UsageBar
          label="Turnos del mes"
          used={apptRes.count ?? 0}
          limit={limits.maxAppointmentsPerMonth}
        />
        <UsageBar
          label="Servicios activos"
          used={svcRes.count ?? 0}
          limit={limits.maxServices}
        />
        <div className="grid grid-cols-2 gap-3 border-t border-border pt-4 text-sm">
          <p className="text-muted">
            Marca personalizada:{" "}
            <span className="text-foreground">
              {limits.branding ? "Incluida" : "No incluida"}
            </span>
          </p>
          <p className="text-muted">
            Recordatorios WhatsApp:{" "}
            <span className="text-foreground">
              {limits.reminders ? "Incluidos" : "No incluidos"}
            </span>
          </p>
          <p className="text-muted">
            Turnos por mes:{" "}
            <span className="text-foreground">
              {formatLimit(limits.maxAppointmentsPerMonth)}
            </span>
          </p>
          <p className="text-muted">
            Servicios:{" "}
            <span className="text-foreground">
              {formatLimit(limits.maxServices)}
            </span>
          </p>
        </div>
      </Card>

      <h2 className="mb-4 mt-10 text-lg font-semibold">Cambiar de plan</h2>
      <p className="mb-4 text-sm text-muted">
        El cambio es inmediato. La facturación se gestiona por separado (sin
        pasarela de pago en esta versión).
      </p>
      <PlanSwitcher currentPlan={business.plan} />
    </div>
  );
}
