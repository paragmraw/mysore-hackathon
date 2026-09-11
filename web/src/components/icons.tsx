import type { SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement>;

function Icon({ className, children, ...props }: IconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
      {...props}
    >
      {children}
    </svg>
  );
}

export function BackIcon({ className = "w-[22px] h-[22px]" }: IconProps) {
  return (
    <Icon className={className} strokeWidth="2">
      <path d="M15 18l-6-6 6-6" />
    </Icon>
  );
}

export function ChevronIcon({ className = "w-[18px] h-[18px]" }: IconProps) {
  return (
    <Icon className={className} strokeWidth="2">
      <path d="M6 9l6 6 6-6" />
    </Icon>
  );
}

export function LockIcon({ className = "w-[18px] h-[18px]" }: IconProps) {
  return (
    <Icon className={className} strokeWidth="2">
      <rect x="4" y="11" width="16" height="10" rx="2" />
      <path d="M8 11V7a4 4 0 0 1 8 0v4" />
    </Icon>
  );
}

/* ─── status icons (stroke 2) ──────────────────────────────────────── */

/** Check mark — the "eligible" mark. */
export function CheckIcon({ className = "w-5 h-5" }: IconProps) {
  return (
    <Icon className={className} strokeWidth="2.5">
      <path d="M5 12.5l4.5 4.5L19 7.5" />
    </Icon>
  );
}

/** Wrench — the "fix needed" mark. */
export function WrenchIcon({ className = "w-5 h-5" }: IconProps) {
  return (
    <Icon className={className} strokeWidth="2">
      <path d="M14.5 6.5a4.5 4.5 0 0 0-6 5.6L4 16.6a2 2 0 1 0 2.8 2.8l4.5-4.5a4.5 4.5 0 0 0 5.6-6l-2.9 2.9-2.5-2.5 2.9-2.9z" />
    </Icon>
  );
}

/** Prohibitory sign — the "not eligible" mark. */
export function ProhibitoryIcon({ className = "w-5 h-5" }: IconProps) {
  return (
    <Icon className={className} strokeWidth="2">
      <circle cx="12" cy="12" r="8" />
      <path d="M6.3 6.3 L17.7 17.7" />
    </Icon>
  );
}

/** Chevron-right — forward/go affordance. */
export function GoIcon({ className = "w-[18px] h-[18px]" }: IconProps) {
  return (
    <Icon className={className} strokeWidth="2">
      <path d="M9 6l6 6-6 6" />
    </Icon>
  );
}
