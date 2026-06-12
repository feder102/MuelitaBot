"use client";

import { useRef, useState, useTransition } from "react";
import { createService, deactivateService } from "@/app/panel/actions";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import type { Service } from "@/lib/types";

export function ServiceForm() {
  const formRef = useRef<HTMLFormElement>(null);
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  function handleSubmit(formData: FormData) {
    setError(null);
    startTransition(async () => {
      const result = await createService(formData);
      if (!result.ok) setError(result.error ?? "Error");
      else formRef.current?.reset();
    });
  }

  return (
    <form ref={formRef} action={handleSubmit} className="space-y-4">
      <Input
        label="Nombre"
        name="name"
        required
        maxLength={80}
        placeholder="Corte de pelo"
      />
      <div className="grid grid-cols-2 gap-4">
        <Input
          label="Duración (minutos)"
          name="durationMinutes"
          type="number"
          required
          min={15}
          max={240}
          step={15}
          defaultValue={60}
        />
        <Input
          label="Precio ($)"
          name="priceArs"
          type="number"
          required
          min={0}
          step={100}
          defaultValue={0}
        />
      </div>
      {error && <p className="text-sm text-danger">{error}</p>}
      <Button type="submit" disabled={pending}>
        {pending ? "Guardando…" : "Agregar servicio"}
      </Button>
    </form>
  );
}

export function ServiceList({ services }: { services: Service[] }) {
  const [pending, startTransition] = useTransition();

  if (services.length === 0) {
    return (
      <Card className="py-8 text-center text-muted">
        Todavía no cargaste servicios.
      </Card>
    );
  }

  return (
    <div className="space-y-3">
      {services.map((s) => (
        <Card key={s.id} className="flex items-center justify-between !p-4">
          <div>
            <p className="font-medium">{s.name}</p>
            <p className="text-sm text-muted">
              {s.duration_minutes} min
              {s.price_cents > 0 &&
                ` · $${(s.price_cents / 100).toLocaleString("es-AR")}`}
            </p>
          </div>
          <Button
            variant="danger"
            size="sm"
            disabled={pending}
            onClick={() => startTransition(() => deactivateService(s.id).then(() => {}))}
          >
            Eliminar
          </Button>
        </Card>
      ))}
    </div>
  );
}
