import { NextResponse } from "next/server";
import { z } from "zod";
import { createAdminClient } from "@/lib/supabase/admin";

const registroSchema = z.object({
  businessName: z.string().min(1).max(80),
  slug: z
    .string()
    .regex(/^[a-z0-9-]{3,40}$/, "Slug inválido"),
  email: z.string().email(),
  password: z.string().min(8).max(72),
});

const RESERVED_SLUGS = new Set([
  "panel",
  "login",
  "registro",
  "precios",
  "api",
]);

// Horario inicial por defecto: lunes a viernes de 9 a 18.
const DEFAULT_WORKING_HOURS = [1, 2, 3, 4, 5].map((day) => ({
  day_of_week: day,
  open_time: "09:00",
  close_time: "18:00",
}));

export async function POST(request: Request) {
  const body = await request.json().catch(() => null);
  const parsed = registroSchema.safeParse(body);
  if (!parsed.success) {
    return NextResponse.json(
      { error: "Revisá los datos ingresados." },
      { status: 400 },
    );
  }
  const { businessName, slug, email, password } = parsed.data;

  if (RESERVED_SLUGS.has(slug)) {
    return NextResponse.json(
      { error: "Esa dirección no está disponible." },
      { status: 409 },
    );
  }

  const admin = createAdminClient();

  const { data: existing } = await admin
    .from("businesses")
    .select("id")
    .eq("slug", slug)
    .maybeSingle();
  if (existing) {
    return NextResponse.json(
      { error: "Esa dirección ya está en uso. Probá con otra." },
      { status: 409 },
    );
  }

  const { data: created, error: userError } =
    await admin.auth.admin.createUser({
      email,
      password,
      email_confirm: true,
    });
  if (userError || !created.user) {
    const taken = userError?.message.toLowerCase().includes("already");
    return NextResponse.json(
      {
        error: taken
          ? "Ya existe una cuenta con ese email."
          : "No se pudo crear la cuenta.",
      },
      { status: taken ? 409 : 500 },
    );
  }

  const { data: business, error: bizError } = await admin
    .from("businesses")
    .insert({ owner_id: created.user.id, slug, name: businessName })
    .select()
    .single();

  if (bizError || !business) {
    // Sin negocio la cuenta no sirve: revertimos el usuario creado.
    await admin.auth.admin.deleteUser(created.user.id);
    const slugTaken = bizError?.code === "23505";
    return NextResponse.json(
      {
        error: slugTaken
          ? "Esa dirección ya está en uso. Probá con otra."
          : "No se pudo crear el negocio.",
      },
      { status: slugTaken ? 409 : 500 },
    );
  }

  await admin.from("working_hours").insert(
    DEFAULT_WORKING_HOURS.map((wh) => ({ ...wh, business_id: business.id })),
  );
  await admin.from("services").insert({
    business_id: business.id,
    name: "Consulta",
    duration_minutes: 60,
    price_cents: 0,
  });

  return NextResponse.json({ ok: true, slug }, { status: 201 });
}
