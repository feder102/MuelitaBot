import Link from "next/link";

export default function NotFound() {
  return (
    <main className="glow flex flex-1 flex-col items-center justify-center px-6 py-24 text-center">
      <p className="text-6xl font-bold text-primary">404</p>
      <h1 className="mt-4 text-2xl font-semibold">Página no encontrada</h1>
      <p className="mt-2 max-w-sm text-muted">
        La página que buscás no existe o el negocio ya no está disponible.
      </p>
      <Link
        href="/"
        className="mt-8 rounded-lg bg-primary px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-primary-hover"
      >
        Volver al inicio
      </Link>
    </main>
  );
}
