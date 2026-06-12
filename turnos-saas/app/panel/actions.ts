"use server";

import { revalidatePath } from "next/cache";
import { z } from "zod";
import { requireBusiness } from "@/lib/get-business";
import { notifyCancellation } from "@/lib/notifications/dispatch";
import { PLAN_LIMITS, PLAN_ORDER, type PlanTier } from "@/lib/plans";
import { createAdminClient } from "@/lib/supabase/admin";
import { createClient } from "@/lib/supabase/server";
import type { Appointment, AppointmentStatus } from "@/lib/types";

export interface ActionResult {
  ok: boolean;
  error?: string;
}

// ── Turnos ────────────────────────────────────────────────────────────────────

const allowedTransitions: Record<AppointmentStatus, AppointmentStatus[]> = {
  PENDING: ["CONFIRMED", "CANCELLED"],
  CONFIRMED: ["COMPLETED", "CANCELLED"],
  COMPLETED: [],
  CANCELLED: [],
};

export async function updateAppointmentStatus(
  appointmentId: string,
  newStatus: AppointmentStatus,
): Promise<ActionResult> {
  const business = await requireBusiness();
  const supabase = await createClient();

  const { data: appointment } = await supabase
    .from("appointments")
    .select("*, services(name)")
    .eq("id", appointmentId)
    .eq("business_id", business.id)
    .maybeSingle<Appointment & { services: { name: string } | null }>();

  if (!appointment) return { ok: false, error: "Turno no encontrado." };
  if (!allowedTransitions[appointment.status].includes(newStatus)) {
    return { ok: false, error: "Ese cambio de estado no está permitido." };
  }

  const { error } = await supabase
    .from("appointments")
    .update({ status: newStatus })
    .eq("id", appointmentId);
  if (error) return { ok: false, error: "No se pudo actualizar el turno." };

  if (newStatus === "CANCELLED") {
    await notifyCancellation(createAdminClient(), {
      appointment,
      businessName: business.name,
      serviceName: appointment.services?.name ?? "Turno",
    });
  }

  revalidatePath("/panel");
  revalidatePath("/panel/agenda");
  return { ok: true };
}

// ── Servicios ────────────────────────────────────────────────────────────────

const serviceSchema = z.object({
  name: z.string().min(1, "El nombre es obligatorio").max(80),
  durationMinutes: z.coerce.number().int().min(15).max(240),
  priceArs: z.coerce.number().min(0).max(100_000_000),
});

export async function createService(formData: FormData): Promise<ActionResult> {
  const business = await requireBusiness();
  const parsed = serviceSchema.safeParse({
    name: formData.get("name"),
    durationMinutes: formData.get("durationMinutes"),
    priceArs: formData.get("priceArs"),
  });
  if (!parsed.success) {
    return { ok: false, error: parsed.error.issues[0].message };
  }

  const supabase = await createClient();
  const maxServices = PLAN_LIMITS[business.plan].maxServices;
  if (maxServices !== Infinity) {
    const { count } = await supabase
      .from("services")
      .select("id", { count: "exact", head: true })
      .eq("business_id", business.id)
      .eq("active", true);
    if ((count ?? 0) >= maxServices) {
      return {
        ok: false,
        error: `Tu plan permite hasta ${maxServices} servicios. Pasate a un plan superior para agregar más.`,
      };
    }
  }

  const { error } = await supabase.from("services").insert({
    business_id: business.id,
    name: parsed.data.name,
    duration_minutes: parsed.data.durationMinutes,
    price_cents: Math.round(parsed.data.priceArs * 100),
  });
  if (error) return { ok: false, error: "No se pudo crear el servicio." };

  revalidatePath("/panel/servicios");
  return { ok: true };
}

export async function deactivateService(serviceId: string): Promise<ActionResult> {
  const business = await requireBusiness();
  const supabase = await createClient();
  const { error } = await supabase
    .from("services")
    .update({ active: false })
    .eq("id", serviceId)
    .eq("business_id", business.id);
  if (error) return { ok: false, error: "No se pudo eliminar el servicio." };
  revalidatePath("/panel/servicios");
  return { ok: true };
}

// ── Horarios ─────────────────────────────────────────────────────────────────

const workingHoursSchema = z.object({
  dayOfWeek: z.coerce.number().int().min(0).max(6),
  openTime: z.string().regex(/^\d{2}:\d{2}$/),
  closeTime: z.string().regex(/^\d{2}:\d{2}$/),
});

export async function setWorkingHours(formData: FormData): Promise<ActionResult> {
  const business = await requireBusiness();
  const parsed = workingHoursSchema.safeParse({
    dayOfWeek: formData.get("dayOfWeek"),
    openTime: formData.get("openTime"),
    closeTime: formData.get("closeTime"),
  });
  if (!parsed.success) return { ok: false, error: "Horario inválido." };
  if (parsed.data.closeTime <= parsed.data.openTime) {
    return { ok: false, error: "El cierre debe ser después de la apertura." };
  }

  const supabase = await createClient();
  const { error } = await supabase.from("working_hours").upsert(
    {
      business_id: business.id,
      day_of_week: parsed.data.dayOfWeek,
      open_time: parsed.data.openTime,
      close_time: parsed.data.closeTime,
    },
    { onConflict: "business_id,day_of_week" },
  );
  if (error) return { ok: false, error: "No se pudo guardar el horario." };
  revalidatePath("/panel/horarios");
  return { ok: true };
}

export async function clearWorkingHours(dayOfWeek: number): Promise<ActionResult> {
  const business = await requireBusiness();
  const supabase = await createClient();
  const { error } = await supabase
    .from("working_hours")
    .delete()
    .eq("business_id", business.id)
    .eq("day_of_week", dayOfWeek);
  if (error) return { ok: false, error: "No se pudo borrar el horario." };
  revalidatePath("/panel/horarios");
  return { ok: true };
}

// ── Perfil ───────────────────────────────────────────────────────────────────

const profileSchema = z.object({
  name: z.string().min(1, "El nombre es obligatorio").max(80),
  description: z.string().max(300).optional(),
  phone: z.string().max(30).optional(),
  address: z.string().max(120).optional(),
});

export async function updateProfile(formData: FormData): Promise<ActionResult> {
  const business = await requireBusiness();
  const parsed = profileSchema.safeParse({
    name: formData.get("name"),
    description: formData.get("description") ?? undefined,
    phone: formData.get("phone") ?? undefined,
    address: formData.get("address") ?? undefined,
  });
  if (!parsed.success) {
    return { ok: false, error: parsed.error.issues[0].message };
  }

  const supabase = await createClient();
  const { error } = await supabase
    .from("businesses")
    .update({
      name: parsed.data.name,
      description: parsed.data.description || null,
      phone: parsed.data.phone || null,
      address: parsed.data.address || null,
    })
    .eq("id", business.id);
  if (error) return { ok: false, error: "No se pudo guardar el perfil." };
  revalidatePath("/panel", "layout");
  return { ok: true };
}

// ── Marca ────────────────────────────────────────────────────────────────────

const brandingSchema = z.object({
  logoUrl: z.string().url("La URL del logo no es válida").or(z.literal("")),
  brandPrimary: z.string().regex(/^#[0-9a-fA-F]{6}$/),
  brandAccent: z.string().regex(/^#[0-9a-fA-F]{6}$/),
});

export async function updateBranding(formData: FormData): Promise<ActionResult> {
  const business = await requireBusiness();
  if (!PLAN_LIMITS[business.plan].branding) {
    return {
      ok: false,
      error: "La personalización de marca está disponible en los planes Pro y Premium.",
    };
  }

  const parsed = brandingSchema.safeParse({
    logoUrl: formData.get("logoUrl") ?? "",
    brandPrimary: formData.get("brandPrimary"),
    brandAccent: formData.get("brandAccent"),
  });
  if (!parsed.success) {
    return { ok: false, error: parsed.error.issues[0].message };
  }

  const supabase = await createClient();
  const { error } = await supabase
    .from("businesses")
    .update({
      logo_url: parsed.data.logoUrl || null,
      brand_primary: parsed.data.brandPrimary,
      brand_accent: parsed.data.brandAccent,
    })
    .eq("id", business.id);
  if (error) return { ok: false, error: "No se pudo guardar la marca." };
  revalidatePath("/panel/marca");
  return { ok: true };
}

// ── Plan ─────────────────────────────────────────────────────────────────────

export async function changePlan(plan: PlanTier): Promise<ActionResult> {
  if (!PLAN_ORDER.includes(plan)) return { ok: false, error: "Plan inválido." };
  const business = await requireBusiness();

  const supabase = await createClient();
  const { error } = await supabase
    .from("businesses")
    .update({ plan })
    .eq("id", business.id);
  if (error) return { ok: false, error: "No se pudo cambiar el plan." };
  revalidatePath("/panel", "layout");
  return { ok: true };
}
