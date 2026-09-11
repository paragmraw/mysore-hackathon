import type { ButtonHTMLAttributes } from "react";

const base =
  "inline-flex items-center justify-center gap-2 min-h-12 px-5 rounded-tile font-display font-bold transition focus-ring active:translate-y-px disabled:opacity-40 disabled:pointer-events-none";

const variants = {
  primary:
    "bg-asphalt text-fog hover:bg-[color-mix(in_oklch,var(--color-asphalt)_88%,white)]",
  secondary:
    "bg-transparent text-asphalt border-2 border-kerb-deep hover:bg-[var(--asphalt-soft)]",
} as const;

export function buttonClass(
  variant: keyof typeof variants = "primary",
  block = false,
) {
  return `${base} ${variants[variant]} ${block ? "w-full" : ""}`;
}

export function Button({
  variant = "primary",
  block = false,
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: keyof typeof variants;
  block?: boolean;
}) {
  return (
    <button
      className={`${buttonClass(variant, block)} ${className}`}
      {...props}
    />
  );
}