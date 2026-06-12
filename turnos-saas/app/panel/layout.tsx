import Link from "next/link";
import { requireBusiness } from "@/lib/get-business";
import { PLAN_LIMITS } from "@/lib/plans";
import { Badge } from "@/components/ui/badge";
import { LogoutButton } from "./logout-button";

const navItems = [
  { href: "/panel", label: "Hoy", icon: "🏠" },
  { href: "/panel/agenda", label: "Agenda", icon: "📅" },
  { href: "/panel/servicios", label: "Servicios", icon: "💼" },
  { href: "/panel/horarios", label: "Horarios", icon: "🕐" },
  { href: "/panel/marca", label: "Mi marca", icon: "🎨" },
  { href: "/panel/perfil", label: "Perfil", icon: "⚙️" },
  { href: "/panel/plan", label: "Mi plan", icon: "⭐" },
];

export default async function PanelLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const business = await requireBusiness();

  return (
    <div className="flex min-h-screen flex-1 flex-col md:flex-row">
      <aside className="flex w-full flex-col border-b border-border bg-surface md:min-h-screen md:w-60 md:border-b-0 md:border-r">
        <div className="border-b border-border p-4">
          <Link href="/panel" className="text-lg font-bold tracking-tight">
            Turnos<span className="text-primary">Ya</span>
          </Link>
          <p className="mt-1 truncate text-sm text-muted">{business.name}</p>
          <Badge tone="primary" className="mt-2">
            Plan {PLAN_LIMITS[business.plan].label}
          </Badge>
        </div>
        <nav className="flex flex-row gap-1 overflow-x-auto p-3 md:flex-col">
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="flex shrink-0 items-center gap-2.5 rounded-lg px-3 py-2 text-sm text-muted transition-colors hover:bg-surface-2 hover:text-foreground"
            >
              <span>{item.icon}</span>
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="mt-auto hidden border-t border-border p-3 md:block">
          <a
            href={`/${business.slug}`}
            target="_blank"
            className="mb-1 flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm text-muted transition-colors hover:bg-surface-2 hover:text-foreground"
          >
            <span>🔗</span> Ver mi página
          </a>
          <LogoutButton />
        </div>
      </aside>
      <main className="flex-1 p-6 md:p-10">{children}</main>
    </div>
  );
}
