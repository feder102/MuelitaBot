import Link from "next/link";
import { PLAN_LIMITS, PLAN_ORDER, formatPriceArs } from "@/lib/plans";

const features = [
  {
    title: "Página de reservas propia",
    description:
      "Cada negocio tiene su página pública con su logo y colores, donde los clientes eligen día y horario en segundos.",
    icon: "🗓️",
  },
  {
    title: "Agenda siempre al día",
    description:
      "Turnos del día, vista semanal e ingresos del mes en un panel pensado para profesionales.",
    icon: "📊",
  },
  {
    title: "Recordatorios por WhatsApp",
    description:
      "Confirmación al reservar y recordatorios automáticos 24 horas y 1 hora antes del turno. Menos ausencias.",
    icon: "💬",
  },
  {
    title: "Sin doble reserva",
    description:
      "La disponibilidad se calcula en tiempo real según tus horarios y servicios. Imposible superponer turnos.",
    icon: "🔒",
  },
];

export default function LandingPage() {
  return (
    <main className="flex-1">
      <div className="glow">
        <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
          <Link href="/" className="text-lg font-bold tracking-tight">
            Turnos<span className="text-primary">Ya</span>
          </Link>
          <nav className="flex items-center gap-2">
            <Link
              href="/precios"
              className="rounded-lg px-3 py-2 text-sm text-muted transition-colors hover:text-foreground"
            >
              Precios
            </Link>
            <Link
              href="/login"
              className="rounded-lg px-3 py-2 text-sm text-muted transition-colors hover:text-foreground"
            >
              Ingresar
            </Link>
            <Link
              href="/registro"
              className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white shadow-lg shadow-primary/20 transition-colors hover:bg-primary-hover"
            >
              Crear cuenta
            </Link>
          </nav>
        </header>

        <section className="mx-auto max-w-6xl px-6 pb-24 pt-20 text-center">
          <p className="mb-4 inline-block rounded-full border border-primary/30 bg-primary/10 px-4 py-1 text-sm text-primary">
            Turnos online para profesionales y negocios
          </p>
          <h1 className="mx-auto max-w-3xl text-5xl font-bold leading-tight tracking-tight sm:text-6xl">
            Tu agenda, abierta{" "}
            <span className="bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">
              las 24 horas
            </span>
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-lg text-muted">
            Creá tu página de reservas en minutos. Tus clientes eligen el
            horario, vos gestionás todo desde un panel simple, y WhatsApp se
            encarga de los recordatorios.
          </p>
          <div className="mt-10 flex items-center justify-center gap-4">
            <Link
              href="/registro"
              className="rounded-lg bg-primary px-8 py-3.5 text-base font-medium text-white shadow-lg shadow-primary/25 transition-colors hover:bg-primary-hover"
            >
              Empezar gratis
            </Link>
            <Link
              href="/precios"
              className="rounded-lg border border-border bg-surface px-8 py-3.5 text-base font-medium transition-colors hover:bg-surface-2"
            >
              Ver planes
            </Link>
          </div>
        </section>
      </div>

      <section className="mx-auto max-w-6xl px-6 py-20">
        <div className="grid gap-6 sm:grid-cols-2">
          {features.map((f) => (
            <div
              key={f.title}
              className="card-gradient rounded-xl border border-border p-6"
            >
              <div className="mb-3 text-3xl">{f.icon}</div>
              <h3 className="mb-2 text-lg font-semibold">{f.title}</h3>
              <p className="text-sm leading-relaxed text-muted">
                {f.description}
              </p>
            </div>
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-6 pb-24">
        <h2 className="mb-10 text-center text-3xl font-bold">
          Planes para cada etapa
        </h2>
        <div className="grid gap-6 md:grid-cols-3">
          {PLAN_ORDER.map((tier) => {
            const plan = PLAN_LIMITS[tier];
            const highlight = tier === "pro";
            return (
              <div
                key={tier}
                className={`card-gradient rounded-xl border p-6 ${
                  highlight ? "border-primary shadow-lg shadow-primary/10" : "border-border"
                }`}
              >
                <h3 className="text-lg font-semibold">{plan.label}</h3>
                <p className="mt-1 text-sm text-muted">{plan.tagline}</p>
                <p className="mt-4 text-3xl font-bold">
                  {formatPriceArs(plan.priceArs)}
                  {plan.priceArs > 0 && (
                    <span className="text-sm font-normal text-muted"> /mes</span>
                  )}
                </p>
                <Link
                  href="/registro"
                  className={`mt-6 block rounded-lg py-2.5 text-center text-sm font-medium transition-colors ${
                    highlight
                      ? "bg-primary text-white hover:bg-primary-hover"
                      : "border border-border bg-surface-2 hover:bg-border"
                  }`}
                >
                  Empezar
                </Link>
              </div>
            );
          })}
        </div>
      </section>

      <footer className="border-t border-border py-8 text-center text-sm text-muted">
        TurnosYa — Reservá turnos online
      </footer>
    </main>
  );
}
