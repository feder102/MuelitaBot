"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { createClient } from "@/lib/supabase/client";

function slugify(name: string): string {
  return name
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 40);
}

export default function RegistroPage() {
  const router = useRouter();
  const [businessName, setBusinessName] = useState("");
  const [slug, setSlug] = useState("");
  const [slugTouched, setSlugTouched] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  function handleNameChange(value: string) {
    setBusinessName(value);
    if (!slugTouched) setSlug(slugify(value));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    const res = await fetch("/api/registro", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ businessName, slug, email, password }),
    });

    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      setError(data.error ?? "No se pudo crear la cuenta. Probá de nuevo.");
      setLoading(false);
      return;
    }

    const supabase = createClient();
    const { error: signInError } = await supabase.auth.signInWithPassword({
      email,
      password,
    });
    if (signInError) {
      router.push("/login");
      return;
    }
    router.push("/panel");
    router.refresh();
  }

  return (
    <main className="glow flex flex-1 items-center justify-center px-6 py-16">
      <div className="w-full max-w-sm">
        <Link
          href="/"
          className="mb-8 block text-center text-2xl font-bold tracking-tight"
        >
          Turnos<span className="text-primary">Ya</span>
        </Link>
        <div className="card-gradient rounded-xl border border-border p-7">
          <h1 className="mb-1 text-xl font-semibold">Registrá tu negocio</h1>
          <p className="mb-6 text-sm text-muted">
            Empezás con el plan Básico, gratis.
          </p>
          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              label="Nombre del negocio"
              required
              value={businessName}
              onChange={(e) => handleNameChange(e.target.value)}
              placeholder="Estética Luna"
              maxLength={80}
            />
            <div className="space-y-1.5">
              <span className="text-sm font-medium text-muted">
                Dirección de tu página
              </span>
              <div className="flex items-center gap-1 rounded-lg border border-border bg-surface-2 px-3 py-2 text-sm focus-within:border-primary focus-within:ring-2 focus-within:ring-primary/60">
                <span className="text-muted">turnosya.app/</span>
                <input
                  required
                  value={slug}
                  onChange={(e) => {
                    setSlugTouched(true);
                    setSlug(slugify(e.target.value));
                  }}
                  placeholder="estetica-luna"
                  pattern="[a-z0-9-]{3,40}"
                  title="Entre 3 y 40 caracteres: minúsculas, números y guiones"
                  className="w-full bg-transparent text-foreground outline-none placeholder:text-muted/60"
                />
              </div>
            </div>
            <Input
              label="Email"
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="tu@email.com"
            />
            <Input
              label="Contraseña"
              type="password"
              required
              minLength={8}
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Mínimo 8 caracteres"
            />
            {error && <p className="text-sm text-danger">{error}</p>}
            <Button type="submit" disabled={loading} className="w-full" size="lg">
              {loading ? "Creando cuenta…" : "Crear cuenta gratis"}
            </Button>
          </form>
          <p className="mt-5 text-center text-sm text-muted">
            ¿Ya tenés cuenta?{" "}
            <Link href="/login" className="text-primary hover:underline">
              Ingresá
            </Link>
          </p>
        </div>
      </div>
    </main>
  );
}
