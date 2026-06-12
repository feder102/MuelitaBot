import type { Metadata } from "next";
import { requireBusiness } from "@/lib/get-business";
import { createClient } from "@/lib/supabase/server";
import type { WorkingHour } from "@/lib/types";
import { WorkingHoursEditor } from "./working-hours-ui";

export const metadata: Metadata = { title: "Horarios" };

export default async function HorariosPage() {
  const business = await requireBusiness();
  const supabase = await createClient();

  const { data: hours } = await supabase
    .from("working_hours")
    .select("*")
    .eq("business_id", business.id)
    .returns<WorkingHour[]>();

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="text-2xl font-bold">Horarios de atención</h1>
      <p className="mt-1 text-muted">
        Definí los días y horarios en los que recibís turnos.
      </p>
      <div className="mt-6">
        <WorkingHoursEditor hours={hours ?? []} />
      </div>
    </div>
  );
}
