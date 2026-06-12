"use client";

import { useState, useTransition } from "react";
import { clearWorkingHours, setWorkingHours } from "@/app/panel/actions";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { WEEKDAY_NAMES } from "@/lib/dates";
import type { WorkingHour } from "@/lib/types";

// Lunes a domingo, en el orden habitual de una semana laboral.
const DAY_ORDER = [1, 2, 3, 4, 5, 6, 0];

export function WorkingHoursEditor({ hours }: { hours: WorkingHour[] }) {
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const byDay = new Map(hours.map((h) => [h.day_of_week, h]));

  function handleSave(formData: FormData) {
    setError(null);
    startTransition(async () => {
      const result = await setWorkingHours(formData);
      if (!result.ok) setError(result.error ?? "Error");
    });
  }

  function handleClear(day: number) {
    setError(null);
    startTransition(async () => {
      const result = await clearWorkingHours(day);
      if (!result.ok) setError(result.error ?? "Error");
    });
  }

  return (
    <div className="space-y-3">
      {error && <p className="text-sm text-danger">{error}</p>}
      {DAY_ORDER.map((day) => {
        const current = byDay.get(day);
        return (
          <Card key={day} className="!p-4">
            <form
              action={handleSave}
              className="flex flex-wrap items-center gap-3"
            >
              <input type="hidden" name="dayOfWeek" value={day} />
              <span className="w-24 font-medium">{WEEKDAY_NAMES[day]}</span>
              {current ? (
                <Badge tone="success">Abierto</Badge>
              ) : (
                <Badge>Cerrado</Badge>
              )}
              <div className="ml-auto flex items-center gap-2">
                <input
                  type="time"
                  name="openTime"
                  required
                  defaultValue={current?.open_time.slice(0, 5) ?? "09:00"}
                  className="rounded-lg border border-border bg-surface-2 px-2 py-1.5 text-sm [color-scheme:dark]"
                />
                <span className="text-muted">a</span>
                <input
                  type="time"
                  name="closeTime"
                  required
                  defaultValue={current?.close_time.slice(0, 5) ?? "18:00"}
                  className="rounded-lg border border-border bg-surface-2 px-2 py-1.5 text-sm [color-scheme:dark]"
                />
                <Button type="submit" size="sm" disabled={pending}>
                  Guardar
                </Button>
                {current && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    disabled={pending}
                    onClick={() => handleClear(day)}
                  >
                    Cerrar día
                  </Button>
                )}
              </div>
            </form>
          </Card>
        );
      })}
    </div>
  );
}
