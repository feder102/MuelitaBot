"use client";

import { useState, useTransition } from "react";
import { updateProfile } from "@/app/panel/actions";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { Business } from "@/lib/types";

export function ProfileForm({ business }: { business: Business }) {
  const [pending, startTransition] = useTransition();
  const [message, setMessage] = useState<{
    text: string;
    error: boolean;
  } | null>(null);

  function handleSubmit(formData: FormData) {
    setMessage(null);
    startTransition(async () => {
      const result = await updateProfile(formData);
      setMessage(
        result.ok
          ? { text: "Perfil guardado.", error: false }
          : { text: result.error ?? "Error", error: true },
      );
    });
  }

  return (
    <form action={handleSubmit} className="space-y-4">
      <Input
        label="Nombre del negocio"
        name="name"
        required
        maxLength={80}
        defaultValue={business.name}
      />
      <label className="block space-y-1.5">
        <span className="text-sm font-medium text-muted">Descripción</span>
        <textarea
          name="description"
          maxLength={300}
          rows={3}
          defaultValue={business.description ?? ""}
          placeholder="Contale a tus clientes qué hacés"
          className="w-full rounded-lg border border-border bg-surface-2 px-3 py-2 text-sm text-foreground placeholder:text-muted/60 transition focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/60"
        />
      </label>
      <div className="grid gap-4 sm:grid-cols-2">
        <Input
          label="Teléfono"
          name="phone"
          maxLength={30}
          defaultValue={business.phone ?? ""}
          placeholder="+5491122334455"
        />
        <Input
          label="Dirección"
          name="address"
          maxLength={120}
          defaultValue={business.address ?? ""}
          placeholder="Av. Corrientes 1234, CABA"
        />
      </div>
      {message && (
        <p
          className={`text-sm ${message.error ? "text-danger" : "text-success"}`}
        >
          {message.text}
        </p>
      )}
      <Button type="submit" disabled={pending}>
        {pending ? "Guardando…" : "Guardar cambios"}
      </Button>
    </form>
  );
}
