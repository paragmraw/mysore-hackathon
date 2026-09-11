import type { MatchResult } from "@/lib/types";
import { CheckIcon, ProhibitoryIcon, WrenchIcon } from "./icons";

type MatchStatus = MatchResult["status"];
const statusStyles: Record<MatchStatus, string> = {
  eligible: "bg-arishina text-asphalt",
  blocked: "border-2 border-kumkuma bg-[var(--kumkuma-soft)] text-kumkuma",
  not_eligible: "border-2 border-kerb-deep bg-transparent text-gravel",
};

const statusIcons: Record<MatchStatus, typeof CheckIcon> = {
  eligible: CheckIcon,
  blocked: WrenchIcon,
  not_eligible: ProhibitoryIcon,
};

export function StatusBadge({
  status,
  label,
  aria,
  size = "md",
}: {
  status: MatchStatus;
  label: string;
  aria: string;
  size?: "md" | "lg";
}) {
  const Icon = statusIcons[status];
  const iconClass =
    size === "lg" ? "w-[18px] h-[18px]" : "w-4 h-4";
  const box =
    size === "lg"
      ? "px-3 py-2 text-[14px]"
      : "px-2.5 py-1.5 text-[13.5px]";

  return (
    <span
      role="img"
      aria-label={aria}
      className={`flex shrink-0 items-center gap-1.5 rounded-tile font-display font-semibold ${box} ${statusStyles[status]}`}
    >
      <Icon className={iconClass} />
      {label}
    </span>
  );
}