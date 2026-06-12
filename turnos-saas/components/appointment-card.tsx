"use client";

import { useState, useTransition } from "react";
import { updateAppointmentStatus } from "@/app/panel/actions";
import { formatArtTime } from "@/lib/dates";
import type { Appointment, AppointmentStatus } from "@/lib/types";
import { StatusBadge } from "./status-badge";
import { Button } from "./ui/button";

export type AppointmentWithService = Appointment & {
  services: { name: string } | null;
};

function formatPrice(cents: number): string {
  return `$${(cents / 100).toLocaleString("es-AR")}`;
}

export function AppointmentCard({
  appointment,
}: {
  appointment: AppointmentWithService;
}) {
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const startsAt = new Date(appointment.starts_at);

  function transition(status: AppointmentStatus) {
    setError(null);
    startTransition(async () => {
      const result = await updateAppointmentStatus(appointment.id, status);
      if (!result.ok) setError(result.error ?? "Error");
    });
  }

  return (
    <div className="card-gradient rounded-xl border border-border p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-center gap-4">
          <div className="rounded-lg bg-surface-2 px-3 py-2 text-center">
            <p className="text-lg font-bold leading-tight">
              {formatArtTime(startsAt)}
            </p>
            <p className="text-xs text-muted">hs</p>
          </div>
          <div>
            <p className="font-medium">{appointment.customer_name}</p>
            <p className="text-sm text-muted">
              {appointment.services?.name ?? "Servicio"}
              {appointment.price_cents > 0 &&
                ` · ${formatPrice(appointment.price_cents)}`}
            </p>
            <p className="mt-0.5 text-xs text-muted">
              DNI {appointment.customer_dni} · {appointment.customer_phone} ·{" "}
              {appointment.customer_email}
            </p>
          </div>
        </div>
        <StatusBadge status={appointment.status} />
      </div>

      {(appointment.status === "PENDING" ||
        appointment.status === "CONFIRMED") && (
        <div className="mt-3 flex flex-wrap gap-2 border-t border-border pt-3">
          {appointment.status === "PENDING" && (
            <Button
              size="sm"
              disabled={pending}
              onClick={() => transition("CONFIRMED")}
            >
              Confirmar
            </Button>
          )}
          {appointment.status === "CONFIRMED" && (
            <Button
              size="sm"
              disabled={pending}
              onClick={() => transition("COMPLETED")}
            >
              Marcar completado
            </Button>
          )}
          <Button
            size="sm"
            variant="danger"
            disabled={pending}
            onClick={() => transition("CANCELLED")}
          >
            Cancelar
          </Button>
          {error && <p className="self-center text-sm text-danger">{error}</p>}
        </div>
      )}
    </div>
  );
}
