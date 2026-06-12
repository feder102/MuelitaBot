import type { Metadata } from "next";
import {
  AppointmentCard,
  type AppointmentWithService,
} from "@/components/appointment-card";
import { Card } from "@/components/ui/card";
import { artDayUtcRange, artMonthStartUtc, formatArtDate, todayArt } from "@/lib/dates";
import { requireBusiness } from "@/lib/get-business";
import { createClient } from "@/lib/supabase/server";

export const metadata: Metadata = { title: "Panel" };

function formatPrice(cents: number): string {
  return `$${(cents / 100).toLocaleString("es-AR")}`;
}

export default async function PanelHomePage() {
  const business = await requireBusiness();
  const supabase = await createClient();

  const today = todayArt();
  const { start, end } = artDayUtcRange(today);

  const [todayRes, monthRes, pendingRes] = await Promise.all([
    supabase
      .from("appointments")
      .select("*, services(name)")
      .eq("business_id", business.id)
      .gte("starts_at", start.toISOString())
      .lt("starts_at", end.toISOString())
      .order("starts_at")
      .returns<AppointmentWithService[]>(),
    supabase
      .from("appointments")
      .select("price_cents")
      .eq("business_id", business.id)
      .eq("status", "COMPLETED")
      .gte("starts_at", artMonthStartUtc().toISOString()),
    supabase
      .from("appointments")
      .select("id", { count: "exact", head: true })
      .eq("business_id", business.id)
      .eq("status", "PENDING")
      .gte("starts_at", new Date().toISOString()),
  ]);

  const todayAppointments = todayRes.data ?? [];
  const monthRevenueCents = (monthRes.data ?? []).reduce(
    (sum, a) => sum + a.price_cents,
    0,
  );
  const pendingCount = pendingRes.count ?? 0;
  const activeToday = todayAppointments.filter(
    (a) => a.status === "PENDING" || a.status === "CONFIRMED",
  ).length;

  return (
    <div className="mx-auto max-w-4xl">
      <h1 className="text-2xl font-bold capitalize">
        {formatArtDate(new Date())}
      </h1>
      <p className="mt-1 text-muted">Resumen de tu día</p>

      <div className="mt-6 grid gap-4 sm:grid-cols-3">
        <Card>
          <p className="text-sm text-muted">Turnos de hoy</p>
          <p className="mt-1 text-3xl font-bold">{activeToday}</p>
        </Card>
        <Card>
          <p className="text-sm text-muted">Ingresos del mes</p>
          <p className="mt-1 text-3xl font-bold text-success">
            {formatPrice(monthRevenueCents)}
          </p>
          <p className="mt-1 text-xs text-muted">Turnos completados</p>
        </Card>
        <Card>
          <p className="text-sm text-muted">Pendientes de confirmar</p>
          <p className="mt-1 text-3xl font-bold text-warning">{pendingCount}</p>
        </Card>
      </div>

      <h2 className="mb-4 mt-10 text-lg font-semibold">Turnos de hoy</h2>
      {todayAppointments.length === 0 ? (
        <Card className="py-10 text-center text-muted">
          No tenés turnos para hoy.
          <p className="mt-1 text-sm">
            Compartí tu página{" "}
            <a
              href={`/${business.slug}`}
              target="_blank"
              className="text-primary hover:underline"
            >
              /{business.slug}
            </a>{" "}
            para recibir reservas.
          </p>
        </Card>
      ) : (
        <div className="space-y-3">
          {todayAppointments.map((a) => (
            <AppointmentCard key={a.id} appointment={a} />
          ))}
        </div>
      )}
    </div>
  );
}
