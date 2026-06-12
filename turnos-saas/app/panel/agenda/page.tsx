import Link from "next/link";
import type { Metadata } from "next";
import {
  AppointmentCard,
  type AppointmentWithService,
} from "@/components/appointment-card";
import { Card } from "@/components/ui/card";
import {
  addDays,
  artDateWeekday,
  artDayUtcRange,
  formatArtDateShort,
  todayArt,
  utcToArtDate,
  WEEKDAY_NAMES,
} from "@/lib/dates";
import { requireBusiness } from "@/lib/get-business";
import { createClient } from "@/lib/supabase/server";

export const metadata: Metadata = { title: "Agenda semanal" };

/** Lunes de la semana que contiene la fecha dada. */
function weekStart(dateART: string): string {
  const weekday = artDateWeekday(dateART);
  const sinceMonday = (weekday + 6) % 7;
  return addDays(dateART, -sinceMonday);
}

export default async function AgendaPage({
  searchParams,
}: {
  searchParams: Promise<{ semana?: string }>;
}) {
  const business = await requireBusiness();
  const supabase = await createClient();

  const { semana } = await searchParams;
  const base = /^\d{4}-\d{2}-\d{2}$/.test(semana ?? "")
    ? (semana as string)
    : todayArt();
  const monday = weekStart(base);
  const days = Array.from({ length: 7 }, (_, i) => addDays(monday, i));

  const { start } = artDayUtcRange(days[0]);
  const { end } = artDayUtcRange(days[6]);

  const { data } = await supabase
    .from("appointments")
    .select("*, services(name)")
    .eq("business_id", business.id)
    .gte("starts_at", start.toISOString())
    .lt("starts_at", end.toISOString())
    .order("starts_at")
    .returns<AppointmentWithService[]>();

  const appointments = data ?? [];
  const byDay = new Map<string, AppointmentWithService[]>(
    days.map((d) => [d, []]),
  );
  for (const a of appointments) {
    byDay.get(utcToArtDate(new Date(a.starts_at)))?.push(a);
  }

  const today = todayArt();

  return (
    <div className="mx-auto max-w-4xl">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Agenda semanal</h1>
          <p className="mt-1 text-muted">
            Semana del {formatArtDateShort(days[0])} al{" "}
            {formatArtDateShort(days[6])}
          </p>
        </div>
        <div className="flex gap-2">
          <Link
            href={`/panel/agenda?semana=${addDays(monday, -7)}`}
            className="rounded-lg border border-border bg-surface-2 px-4 py-2 text-sm transition-colors hover:bg-border"
          >
            ← Anterior
          </Link>
          <Link
            href="/panel/agenda"
            className="rounded-lg border border-border bg-surface-2 px-4 py-2 text-sm transition-colors hover:bg-border"
          >
            Hoy
          </Link>
          <Link
            href={`/panel/agenda?semana=${addDays(monday, 7)}`}
            className="rounded-lg border border-border bg-surface-2 px-4 py-2 text-sm transition-colors hover:bg-border"
          >
            Siguiente →
          </Link>
        </div>
      </div>

      <div className="mt-8 space-y-8">
        {days.map((day) => {
          const dayAppointments = byDay.get(day) ?? [];
          const isToday = day === today;
          return (
            <section key={day}>
              <h2
                className={`mb-3 text-sm font-semibold uppercase tracking-wide ${
                  isToday ? "text-primary" : "text-muted"
                }`}
              >
                {WEEKDAY_NAMES[artDateWeekday(day)]} {day.slice(8)}/
                {day.slice(5, 7)}
                {isToday && " · Hoy"}
              </h2>
              {dayAppointments.length === 0 ? (
                <Card className="py-4 text-center text-sm text-muted">
                  Sin turnos
                </Card>
              ) : (
                <div className="space-y-3">
                  {dayAppointments.map((a) => (
                    <AppointmentCard key={a.id} appointment={a} />
                  ))}
                </div>
              )}
            </section>
          );
        })}
      </div>
    </div>
  );
}
