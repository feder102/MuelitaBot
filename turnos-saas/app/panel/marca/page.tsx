import Link from "next/link";
import type { Metadata } from "next";
import { Card } from "@/components/ui/card";
import { requireBusiness } from "@/lib/get-business";
import { PLAN_LIMITS } from "@/lib/plans";
import { BrandingForm } from "./branding-ui";

export const metadata: Metadata = { title: "Mi marca" };

export default async function MarcaPage() {
  const business = await requireBusiness();
  const canBrand = PLAN_LIMITS[business.plan].branding;

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="text-2xl font-bold">Mi marca</h1>
      <p className="mt-1 text-muted">
        Personalizá tu página pública con tu logo y tus colores.
      </p>

      {canBrand ? (
        <Card className="mt-6">
          <BrandingForm business={business} />
        </Card>
      ) : (
        <Card className="mt-6 border-primary/30 py-10 text-center">
          <div className="mb-3 text-3xl">🔒</div>
          <h2 className="text-lg font-semibold">
            Disponible en Pro y Premium
          </h2>
          <p className="mx-auto mt-2 max-w-sm text-sm text-muted">
            Subí de plan para mostrar tu logo y usar los colores de tu marca en
            tu página de reservas.
          </p>
          <Link
            href="/panel/plan"
            className="mt-6 inline-block rounded-lg bg-primary px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-primary-hover"
          >
            Ver planes
          </Link>
        </Card>
      )}
    </div>
  );
}
