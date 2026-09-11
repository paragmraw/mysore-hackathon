import type { ButtonHTMLAttributes } from "react";

export function Chip({
  selected,
  ...props
}: Omit<ButtonHTMLAttributes<HTMLButtonElement>, "className"> & {
  selected: boolean;
}) {
  return (
    <button
      aria-pressed={selected}
      className="min-h-12 rounded-tile border-2 border-kerb-deep bg-board px-4 py-3 text-left text-[17px] transition-colors hover:border-asphalt aria-pressed:border-asphalt aria-pressed:bg-[var(--arishina-soft)] aria-pressed:font-semibold focus-ring"
      {...props}
    />
  );
}