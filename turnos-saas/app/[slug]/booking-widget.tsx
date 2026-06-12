"use client";

import { useCallback, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { Slot } from "@/lib/availability";
import { addDays, formatArtDateShort, todayArt } from "@/lib/dates";
import type { Service } from "@/lib/types";

function formatPrice(cents: number): string {
  if (cents === 0) return "";
  return ` · $${(cents / 100).toLocaleString("es-AR")}`;
}

type Step = "service" | "slot" | "details" | "done";

export function BookingWidget({
  slug,
  services,
}: {
  slug: string;
  services: Service[];
}) {
  const [step, setStep] = useState<Step>("service");
  const [service, setService] = useState<Service | null>(
    services.length === 1 ? services[0] : null,
  );
  const [date, setDate] = useState(todayArt());
  const [slots, setSlots] = useState<Slot[] | null>(null);
  const [slot, setSlot] = useState<Slot | null>(null);
  const [loadingSlots, setLoadingSlots] = useState(false);

  const [name, setName] = useState("");
  const [dni, setDni] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const days = useMemo(() => {
    const today = todayArt();
    return Array.from({ length: 14 }, (_, i) => addDays(today, i));
  }, []);

  const loadSlots = useCallback(
    async (serviceId: string, dateART: string) => {
      setLoadingSlots(true);
      setSlots(null);
      setSlot(null);
      try {
        const res = await fetch(
          `/api/availability?slug=${slug}&serviceId=${serviceId}&date=${dateART}`,
        );
        const data = await res.json();
        setSlots(res.ok ? (data.slots ?? []) : []);
      } catch {
        setSlots([]);
      } finally {
        setLoadingSlots(false);
      }
    },
    [slug],
  );

  function selectService(s: Service) {
    setService(s);
    setStep("slot");
    loadSlots(s.id, date);
  }

  function selectDate(d: string) {
    setDate(d);
    if (service) loadSlots(service.id, d);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!service || !slot) return;
    setError(null);
    setSubmitting(true);

    const res = await fetch("/api/bookings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        slug,
        serviceId: service.id,
        startsAt: slot.startsAtUtc,
        customerName: name,
        customerDni: dni,
        customerEmail: email,
        customerPhone: phone,
      }),
    });

    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      setError(data.error ?? "No se pudo crear la reserva. Probá de nuevo.");
      setSubmitting(false);
      if (res.status === 409) {
        // El horario se ocupó mientras completaba el formulario.
        setStep("slot");
        loadSlots(service.id, date);
      }
      return;
    }

    setStep("done");
  }

  if (step === "done" && service && slot) {
    return (
      <div className="card-gradient rounded-xl border border-success/30 p-8 text-center">
        <div className="mb-3 text-4xl">✅</div>
        <h2 className="text-xl font-semibold">¡Turno reservado!</h2>
        <p className="mt-2 text-muted">
          {service.name} — {formatArtDateShort(date)} a las {slot.label} hs.
        </p>
        <p className="mt-1 text-sm text-muted">
          Te enviamos la confirmación por WhatsApp al {phone}.
        </p>
        <Button
          variant="secondary"
          className="mt-6"
          onClick={() => {
            setStep("service");
            setSlot(null);
            setName("");
            setDni("");
            setEmail("");
            setPhone("");
          }}
        >
          Reservar otro turno
        </Button>
      </div>
    );
  }

  return (
    <div className="card-gradient rounded-xl border border-border p-6 sm:p-8">
      {/* Paso 1: servicio */}
      <div>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted">
          1 · Elegí el servicio
        </h2>
        <div className="grid gap-2 sm:grid-cols-2">
          {services.map((s) => (
            <button
              key={s.id}
              type="button"
              onClick={() => selectService(s)}
              className={`rounded-lg border px-4 py-3 text-left text-sm transition-colors ${
                service?.id === s.id
                  ? "border-primary bg-primary/10"
                  : "border-border bg-surface-2 hover:border-muted"
              }`}
            >
              <span className="font-medium">{s.name}</span>
              <span className="block text-xs text-muted">
                {s.duration_minutes} min{formatPrice(s.price_cents)}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Paso 2: fecha y horario */}
      {service && step !== "service" && (
        <div className="mt-8">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted">
            2 · Elegí día y horario
          </h2>
          <div className="flex gap-2 overflow-x-auto pb-2">
            {days.map((d) => (
              <button
                key={d}
                type="button"
                onClick={() => selectDate(d)}
                className={`shrink-0 rounded-lg border px-3 py-2 text-sm capitalize transition-colors ${
                  date === d
                    ? "border-primary bg-primary/10 text-foreground"
                    : "border-border bg-surface-2 text-muted hover:border-muted"
                }`}
              >
                {formatArtDateShort(d)}
              </button>
            ))}
          </div>

          <div className="mt-4">
            {loadingSlots && (
              <p className="py-6 text-center text-sm text-muted">
                Buscando horarios…
              </p>
            )}
            {!loadingSlots && slots && slots.length === 0 && (
              <p className="py-6 text-center text-sm text-muted">
                No hay horarios disponibles ese día. Probá con otra fecha.
              </p>
            )}
            {!loadingSlots && slots && slots.length > 0 && (
              <div className="grid grid-cols-4 gap-2 sm:grid-cols-6">
                {slots.map((s) => (
                  <button
                    key={s.startsAtUtc}
                    type="button"
                    onClick={() => {
                      setSlot(s);
                      setStep("details");
                    }}
                    className={`rounded-lg border py-2 text-sm transition-colors ${
                      slot?.startsAtUtc === s.startsAtUtc
                        ? "border-primary bg-primary text-white"
                        : "border-border bg-surface-2 hover:border-primary"
                    }`}
                  >
                    {s.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Paso 3: datos del cliente */}
      {service && slot && step === "details" && (
        <form onSubmit={handleSubmit} className="mt-8">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted">
            3 · Tus datos
          </h2>
          <p className="mb-4 rounded-lg border border-primary/30 bg-primary/10 px-4 py-2.5 text-sm">
            {service.name} — {formatArtDateShort(date)} a las {slot.label} hs
          </p>
          <div className="grid gap-4 sm:grid-cols-2">
            <Input
              label="Nombre y apellido"
              required
              maxLength={80}
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Juana Pérez"
            />
            <Input
              label="DNI"
              required
              inputMode="numeric"
              pattern="\d{6,12}"
              title="Solo números, entre 6 y 12 dígitos"
              value={dni}
              onChange={(e) => setDni(e.target.value.replace(/\D/g, ""))}
              placeholder="30123456"
            />
            <Input
              label="Email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="juana@email.com"
            />
            <Input
              label="Teléfono (WhatsApp)"
              type="tel"
              required
              pattern="\+?\d{8,15}"
              title="Solo números, con código de área. Ej: +5491122334455"
              value={phone}
              onChange={(e) =>
                setPhone(e.target.value.replace(/[^\d+]/g, ""))
              }
              placeholder="+5491122334455"
            />
          </div>
          {error && <p className="mt-4 text-sm text-danger">{error}</p>}
          <Button
            type="submit"
            size="lg"
            disabled={submitting}
            className="mt-6 w-full"
          >
            {submitting ? "Reservando…" : "Confirmar reserva"}
          </Button>
        </form>
      )}
    </div>
  );
}
