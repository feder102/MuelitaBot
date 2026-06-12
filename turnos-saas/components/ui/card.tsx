import type { HTMLAttributes } from "react";

export function Card({
  className = "",
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={`card-gradient rounded-xl border border-border p-5 ${className}`}
      {...props}
    />
  );
}
