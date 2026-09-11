import type { Localized } from "./types";

export function pickText(
  text: Localized | null | undefined,
  locale: string,
): string {
  if (!text) return "";
  return (locale === "kn" ? text.kn : text.en) || text.en || "";
}