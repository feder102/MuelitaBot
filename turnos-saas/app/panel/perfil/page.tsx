import type { Metadata } from "next";
import { Card } from "@/components/ui/card";
import { requireBusiness } from "@/lib/get-business";
import { ProfileForm } from "./profile-ui";

export const metadata: Metadata = { title: "Perfil" };

export default async function PerfilPage() {
  const business = await requireBusiness();

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="text-2xl font-bold">Perfil del negocio</h1>
      <p className="mt-1 text-muted">
        Esta información se muestra en tu página pública{" "}
        <a
          href={`/${business.slug}`}
          target="_blank"
          className="text-primary hover:underline"
        >
          /{business.slug}
        </a>
        .
      </p>
      <Card className="mt-6">
        <ProfileForm business={business} />
      </Card>
    </div>
  );
}
