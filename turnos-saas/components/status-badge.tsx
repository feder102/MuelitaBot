import { Badge } from "./ui/badge";
import type { AppointmentStatus } from "@/lib/types";

const config: Record<
  AppointmentStatus,
  { label: string; tone: "warning" | "primary" | "success" | "danger" }
> = {
  PENDING: { label: "Pendiente", tone: "warning" },
  CONFIRMED: { label: "Confirmado", tone: "primary" },
  COMPLETED: { label: "Completado", tone: "success" },
  CANCELLED: { label: "Cancelado", tone: "danger" },
};

export function StatusBadge({ status }: { status: AppointmentStatus }) {
  const { label, tone } = config[status];
  return <Badge tone={tone}>{label}</Badge>;
}
