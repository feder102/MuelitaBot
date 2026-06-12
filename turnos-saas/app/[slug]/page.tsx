import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { createAdminClient } from "@/lib/supabase/admin";
import type { Business, Service } from "@/lib/types";
import { BookingWidget } from "./booking-widget";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const admin = createAdminClient();
  const { data } = await admin
    .from("businesses")
    .select("name, description")
    .eq("slug", slug)
    .maybeSingle();
  if (!data) return { title: "Negocio no encontrado" };
  return {
    title: `${data.name} — Reservá tu turno`,
    description: data.description ?? `Reservá tu turno online en ${data.name}.`,
  };
}

export default async function PublicBookingPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  if (!/^[a-z0-9-]{3,40}$/.test(slug)) notFound();

  const admin = createAdminClient();
  const { data: business } = await admin
    .from("businesses")
    .select("*")
    .eq("slug", slug)
    .maybeSingle<Business>();
  if (!business) notFound();

  const { data: services } = await admin
    .from("services")
    .select("*")
    .eq("business_id", business.id)
    .eq("active", true)
    .order("created_at")
    .returns<Service[]>();

  return (
    <main
      className="flex-1"
      style={
        {
          "--primary": business.brand_primary,
          "--primary-hover": business.brand_primary,
          "--accent": business.brand_accent,
        } as React.CSSProperties
      }
    >
      <div className="glow border-b border-border">
        <header className="mx-auto max-w-3xl px-6 py-14 text-center">
          {business.logo_url && (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={business.logo_url}
              alt={`Logo de ${business.name}`}
              className="mx-auto mb-5 h-20 w-20 rounded-2xl border border-border object-cover"
            />
          )}
          <h1 className="text-4xl font-bold tracking-tight">{business.name}</h1>
          {business.description && (
            <p className="mx-auto mt-3 max-w-xl text-muted">
              {business.description}
            </p>
          )}
          <div className="mt-4 flex flex-wrap items-center justify-center gap-x-6 gap-y-1 text-sm text-muted">
            {business.address && <span>📍 {business.address}</span>}
            {business.phone && <span>📞 {business.phone}</span>}
          </div>
        </header>
      </div>

      <section className="mx-auto max-w-3xl px-6 py-10">
        {services && services.length > 0 ? (
          <BookingWidget slug={business.slug} services={services} />
        ) : (
          <p className="rounded-xl border border-border bg-surface p-8 text-center text-muted">
            Este negocio todavía no cargó sus servicios.
          </p>
        )}
      </section>

      <footer className="border-t border-border py-6 text-center text-xs text-muted">
        Reservas online con TurnosYa
      </footer>
    </main>
  );
}
