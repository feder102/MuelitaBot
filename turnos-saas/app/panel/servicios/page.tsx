import type { Metadata } from "next";
import { Card } from "@/components/ui/card";
import { requireBusiness } from "@/lib/get-business";
import { PLAN_LIMITS, formatLimit } from "@/lib/plans";
import { createClient } from "@/lib/supabase/server";
import type { Service } from "@/lib/types";
import { ServiceForm, ServiceList } from "./services-ui";

export const metadata: Metadata = { title: "Servicios" };

export default async function ServiciosPage() {
  const business = await requireBusiness();
  const supabase = await createClient();

  const { data: services } = await supabase
    .from("services")
    .select("*")
    .eq("business_id", business.id)
    .eq("active", true)
    .order("created_at")
    .returns<Service[]>();

  const limits = PLAN_LIMITS[business.plan];

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="text-2xl font-bold">Servicios</h1>
      <p className="mt-1 text-muted">
        Lo que tus clientes pueden reservar ({services?.length ?? 0} de{" "}
        {formatLimit(limits.maxServices).toLowerCase()})
      </p>

      <Card className="mt-6">
        <h2 className="mb-4 font-semibold">Nuevo servicio</h2>
        <ServiceForm />
      </Card>

      <div className="mt-6">
        <ServiceList services={services ?? []} />
      </div>
    </div>
  );
}
