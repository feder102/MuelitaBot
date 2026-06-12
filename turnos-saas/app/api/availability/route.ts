import { NextResponse } from "next/server";
import { z } from "zod";
import { getAvailableSlots } from "@/lib/availability";
import { artDateWeekday, artDayUtcRange, todayArt, addDays } from "@/lib/dates";
import { createAdminClient } from "@/lib/supabase/admin";

const querySchema = z.object({
  slug: z.string().regex(/^[a-z0-9-]{3,40}$/),
  serviceId: z.string().uuid(),
  date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
});

const MAX_DAYS_AHEAD = 60;

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const parsed = querySchema.safeParse({
    slug: searchParams.get("slug"),
    serviceId: searchParams.get("serviceId"),
    date: searchParams.get("date"),
  });
  if (!parsed.success) {
    return NextResponse.json({ error: "Parámetros inválidos" }, { status: 400 });
  }
  const { slug, serviceId, date } = parsed.data;

  const today = todayArt();
  if (date < today || date > addDays(today, MAX_DAYS_AHEAD)) {
    return NextResponse.json({ slots: [] });
  }

  const admin = createAdminClient();

  const { data: business } = await admin
    .from("businesses")
    .select("id")
    .eq("slug", slug)
    .maybeSingle();
  if (!business) {
    return NextResponse.json({ error: "Negocio no encontrado" }, { status: 404 });
  }

  const { data: service } = await admin
    .from("services")
    .select("id, duration_minutes")
    .eq("id", serviceId)
    .eq("business_id", business.id)
    .eq("active", true)
    .maybeSingle();
  if (!service) {
    return NextResponse.json({ error: "Servicio no encontrado" }, { status: 404 });
  }

  const weekday = artDateWeekday(date);
  const { data: workingHours } = await admin
    .from("working_hours")
    .select("open_time, close_time")
    .eq("business_id", business.id)
    .eq("day_of_week", weekday)
    .maybeSingle();

  const { start, end } = artDayUtcRange(date);
  const { data: busy } = await admin
    .from("appointments")
    .select("starts_at, ends_at")
    .eq("business_id", business.id)
    .in("status", ["PENDING", "CONFIRMED"])
    .gte("starts_at", start.toISOString())
    .lt("starts_at", end.toISOString());

  const slots = getAvailableSlots({
    dateART: date,
    workingHours: workingHours ?? null,
    durationMinutes: service.duration_minutes,
    busy: busy ?? [],
  });

  return NextResponse.json({ slots });
}
