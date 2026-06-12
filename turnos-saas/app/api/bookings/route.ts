import { NextResponse } from "next/server";
import { z } from "zod";
import { getAvailableSlots } from "@/lib/availability";
import {
  artDateWeekday,
  artDayUtcRange,
  artMonthStartUtc,
  utcToArtDate,
} from "@/lib/dates";
import { createBookingNotifications } from "@/lib/notifications/dispatch";
import { PLAN_LIMITS, type PlanTier } from "@/lib/plans";
import { createAdminClient } from "@/lib/supabase/admin";
import type { Appointment } from "@/lib/types";

const bookingSchema = z.object({
  slug: z.string().regex(/^[a-z0-9-]{3,40}$/),
  serviceId: z.string().uuid(),
  startsAt: z.string().datetime(),
  customerName: z.string().min(1).max(80),
  customerDni: z.string().regex(/^\d{6,12}$/, "DNI inválido"),
  customerEmail: z.string().email(),
  customerPhone: z.string().regex(/^\+?\d{8,15}$/, "Teléfono inválido"),
});

export async function POST(request: Request) {
  const body = await request.json().catch(() => null);
  const parsed = bookingSchema.safeParse(body);
  if (!parsed.success) {
    return NextResponse.json(
      { error: "Revisá los datos ingresados." },
      { status: 400 },
    );
  }
  const data = parsed.data;
  const startsAt = new Date(data.startsAt);

  const admin = createAdminClient();

  const { data: business } = await admin
    .from("businesses")
    .select("id, name, plan")
    .eq("slug", data.slug)
    .maybeSingle();
  if (!business) {
    return NextResponse.json(
      { error: "Negocio no encontrado." },
      { status: 404 },
    );
  }

  const { data: service } = await admin
    .from("services")
    .select("id, name, duration_minutes, price_cents")
    .eq("id", data.serviceId)
    .eq("business_id", business.id)
    .eq("active", true)
    .maybeSingle();
  if (!service) {
    return NextResponse.json(
      { error: "Servicio no encontrado." },
      { status: 404 },
    );
  }

  // Límite mensual del plan (turnos no cancelados del mes argentino actual).
  const plan = business.plan as PlanTier;
  const limit = PLAN_LIMITS[plan].maxAppointmentsPerMonth;
  if (limit !== Infinity) {
    const { count } = await admin
      .from("appointments")
      .select("id", { count: "exact", head: true })
      .eq("business_id", business.id)
      .neq("status", "CANCELLED")
      .gte("created_at", artMonthStartUtc().toISOString());
    if ((count ?? 0) >= limit) {
      return NextResponse.json(
        { error: "El negocio alcanzó el límite de turnos de su plan este mes." },
        { status: 403 },
      );
    }
  }

  // Revalidamos que el horario pedido siga disponible (horarios de atención,
  // anticipación mínima y solapamientos).
  const dateART = utcToArtDate(startsAt);
  const weekday = artDateWeekday(dateART);
  const { data: workingHours } = await admin
    .from("working_hours")
    .select("open_time, close_time")
    .eq("business_id", business.id)
    .eq("day_of_week", weekday)
    .maybeSingle();

  const { start, end } = artDayUtcRange(dateART);
  const { data: busy } = await admin
    .from("appointments")
    .select("starts_at, ends_at")
    .eq("business_id", business.id)
    .in("status", ["PENDING", "CONFIRMED"])
    .gte("starts_at", start.toISOString())
    .lt("starts_at", end.toISOString());

  const slots = getAvailableSlots({
    dateART,
    workingHours: workingHours ?? null,
    durationMinutes: service.duration_minutes,
    busy: busy ?? [],
  });
  const slot = slots.find((s) => s.startsAtUtc === startsAt.toISOString());
  if (!slot) {
    return NextResponse.json(
      { error: "Ese horario ya no está disponible. Elegí otro." },
      { status: 409 },
    );
  }

  const { data: appointment, error: insertError } = await admin
    .from("appointments")
    .insert({
      business_id: business.id,
      service_id: service.id,
      customer_name: data.customerName,
      customer_dni: data.customerDni,
      customer_email: data.customerEmail,
      customer_phone: data.customerPhone,
      starts_at: slot.startsAtUtc,
      ends_at: slot.endsAtUtc,
      price_cents: service.price_cents,
    })
    .select()
    .single();

  if (insertError || !appointment) {
    // 23P01: violación de la exclusion constraint → otro cliente ganó el slot.
    if (insertError?.code === "23P01") {
      return NextResponse.json(
        { error: "Ese horario acaba de ocuparse. Elegí otro." },
        { status: 409 },
      );
    }
    return NextResponse.json(
      { error: "No se pudo crear la reserva." },
      { status: 500 },
    );
  }

  await createBookingNotifications(admin, {
    appointment: appointment as Appointment,
    businessName: business.name,
    serviceName: service.name,
    plan,
  });

  return NextResponse.json({ ok: true, appointmentId: appointment.id }, { status: 201 });
}
