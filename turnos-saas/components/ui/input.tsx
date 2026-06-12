import type { InputHTMLAttributes, SelectHTMLAttributes } from "react";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
}

const fieldClasses =
  "w-full rounded-lg bg-surface-2 border border-border px-3 py-2 text-sm text-foreground placeholder:text-muted/60 focus:outline-none focus:ring-2 focus:ring-primary/60 focus:border-primary transition";

export function Input({ label, id, className = "", ...props }: InputProps) {
  const input = (
    <input id={id} className={`${fieldClasses} ${className}`} {...props} />
  );
  if (!label) return input;
  return (
    <label className="block space-y-1.5">
      <span className="text-sm font-medium text-muted">{label}</span>
      {input}
    </label>
  );
}

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
}

export function Select({ label, className = "", ...props }: SelectProps) {
  const select = (
    <select className={`${fieldClasses} ${className}`} {...props} />
  );
  if (!label) return select;
  return (
    <label className="block space-y-1.5">
      <span className="text-sm font-medium text-muted">{label}</span>
      {select}
    </label>
  );
}
