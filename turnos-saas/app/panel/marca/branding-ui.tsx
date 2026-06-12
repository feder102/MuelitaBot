"use client";

import { useState, useTransition } from "react";
import { updateBranding } from "@/app/panel/actions";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { Business } from "@/lib/types";

export function BrandingForm({ business }: { business: Business }) {
  const [pending, startTransition] = useTransition();
  const [message, setMessage] = useState<{
    text: string;
    error: boolean;
  } | null>(null);

  function handleSubmit(formData: FormData) {
    setMessage(null);
    startTransition(async () => {
      const result = await updateBranding(formData);
      setMessage(
        result.ok
          ? { text: "Marca guardada. Mirá tu página pública.", error: false }
          : { text: result.error ?? "Error", error: true },
      );
    });
  }

  return (
    <form action={handleSubmit} className="space-y-4">
      <Input
        label="URL del logo"
        name="logoUrl"
        type="url"
        defaultValue={business.logo_url ?? ""}
        placeholder="https://tusitio.com/logo.png"
      />
      <div className="grid grid-cols-2 gap-4">
        <label className="block space-y-1.5">
          <span className="text-sm font-medium text-muted">
            Color principal
          </span>
          <input
            type="color"
            name="brandPrimary"
            defaultValue={business.brand_primary}
            className="h-10 w-full cursor-pointer rounded-lg border border-border bg-surface-2"
          />
        </label>
        <label className="block space-y-1.5">
          <span className="text-sm font-medium text-muted">Color de acento</span>
          <input
            type="color"
            name="brandAccent"
            defaultValue={business.brand_accent}
            className="h-10 w-full cursor-pointer rounded-lg border border-border bg-surface-2"
          />
        </label>
      </div>
      {message && (
        <p
          className={`text-sm ${message.error ? "text-danger" : "text-success"}`}
        >
          {message.text}
        </p>
      )}
      <Button type="submit" disabled={pending}>
        {pending ? "Guardando…" : "Guardar marca"}
      </Button>
    </form>
  );
}
