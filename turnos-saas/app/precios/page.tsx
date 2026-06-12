import Link from "next/link";
import type { Metadata } from "next";
import { PLAN_LIMITS, PLAN_ORDER, formatPriceArs } from "@/lib/plans";

export const metadata: Metadata = { title: "Precios" };

export default function PreciosPage() {
  return (
    <main className="glow flex-1">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
        <Link href="/" className="text-lg font-bold tracking-tight">
          Turnos<span className="text-primary">Ya</span>
        </Link>
        <nav className="flex items-center gap-2">
          <Link
            href="/login"
            className="rounded-lg px-3 py-2 text-sm text-muted transition-colors hover:text-foreground"
          >
            Ingresar
          </Link>
          <Link
            href="/registro"
            className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-primary-hover"
          >
            Crear cuenta
          </Link>
        </nav>
      </header>

      <section className="mx-auto max-w-6xl px-6 py-16">
        <h1 className="text-center text-4xl font-bold tracking-tight">
          Elegí tu plan
        </h1>
        <p className="mx-auto mt-4 max-w-xl text-center text-muted">
          Empezá gratis y subí de plan cuando tu agenda lo necesite. Sin
          permanencia.
        </p>

        <div className="mt-14 grid gap-6 md:grid-cols-3">
          {PLAN_ORDER.map((tier) => {
            const plan = PLAN_LIMITS[tier];
            const highlight = tier === "pro";
            return (
              <div
                key={tier}
                className={`card-gradient relative flex flex-col rounded-xl border p-7 ${
                  highlight
                    ? "border-primary shadow-xl shadow-primary/10"
                    : "border-border"
                }`}
              >
                {highlight && (
                  <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-primary px-3 py-0.5 text-xs font-medium text-white">
                    Más elegido
                  </span>
                )}
                <h2 className="text-xl font-semibold">{plan.label}</h2>
                <p className="mt-1 text-sm text-muted">{plan.tagline}</p>
                <p className="mt-5 text-4xl font-bold">
                  {formatPriceArs(plan.priceArs)}
                  {plan.priceArs > 0 && (
                    <span className="text-sm font-normal text-muted"> /mes</span>
                  )}
                </p>
                <ul className="mt-6 flex-1 space-y-3">
                  {plan.features.map((feature) => (
                    <li key={feature} className="flex gap-2 text-sm">
                      <span className="text-success">✓</span>
                      <span className="text-foreground/90">{feature}</span>
                    </li>
                  ))}
                </ul>
                <Link
                  href="/registro"
                  className={`mt-8 block rounded-lg py-3 text-center text-sm font-medium transition-colors ${
                    highlight
                      ? "bg-primary text-white hover:bg-primary-hover"
                      : "border border-border bg-surface-2 hover:bg-border"
                  }`}
                >
                  {plan.priceArs === 0 ? "Empezar gratis" : `Elegir ${plan.label}`}
                </Link>
              </div>
            );
          })}
        </div>
      </section>
    </main>
  );
}
