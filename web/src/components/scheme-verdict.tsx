"use client";

import { useEffect, useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { StatusBadge } from "@/components/StatusBadge";
import { pickText } from "@/lib/localize";
import { RESULTS_KEY, readJson } from "@/lib/session";
import type { MatchResponse, MatchResult } from "@/lib/types";

function useMatchResult(
  schemeId: string,
): MatchResult | null | undefined {
  const [result, setResult] = useState<MatchResult | null | undefined>(
    undefined,
  );
  useEffect(() => {
    let cancelled = false;
    void Promise.resolve().then(() => {
      if (cancelled) return;
      const resp = readJson<MatchResponse>(RESULTS_KEY);
      setResult(resp?.results.find((r) => r.scheme_id === schemeId) ?? null);
    });
    return () => {
      cancelled = true;
    };
  }, [schemeId]);
  return result;
}

function statusKey(status: MatchResult["status"]): string {
  return status === "not_eligible" ? "notEligible" : status;
}

type TFunc = ReturnType<typeof useTranslations>;

function statusLabel(
  result: MatchResult,
  t: TFunc,
): string {
  return result.status === "blocked"
    ? t("results.fixesNeeded", { count: result.fixes.length })
    : t(`status.${statusKey(result.status)}`);
}

export function SchemeStatusBadge({ schemeId }: { schemeId: string }) {
  const t = useTranslations();
  const result = useMatchResult(schemeId);
  if (!result) return null;
  return (
    <StatusBadge
      status={result.status}
      label={statusLabel(result, t)}
      aria={t(`status.${statusKey(result.status)}Aria`)}
      size="lg"
    />
  );
}

export function SchemeVerdictBoards({ schemeId }: { schemeId: string }) {
  const t = useTranslations();
  const locale = useLocale();
  const result = useMatchResult(schemeId);
  if (!result) return null;

  if (result.status === "eligible") {
    return (
      <div className="board board-l-arishina p-5">
        <p className="label text-asphalt">{t("status.eligible")}</p>
        <p className="mt-1.5 text-asphalt">{t("status.eligibleAria")}</p>
      </div>
    );
  }

  if (result.status === "blocked") {
    return (
      <>
        <div className="board board-l-kumkuma p-5">
          <p className="label text-kumkuma">{t("detail.whyBlocked")}</p>
          <ul className="mt-1.5 list-disc space-y-1.5 pl-5">
            {result.reasons.map((reason, i) => (
              <li key={i} className="text-asphalt">
                {pickText(reason.message, locale)}
              </li>
            ))}
          </ul>
        </div>
        <div className="board board-l-arishina p-5">
          <p className="label text-asphalt">{t("detail.howToFix")}</p>
          <div className="mt-1.5 flex flex-col gap-4">
            {result.fixes.map((fix) => (
              <div key={fix.fix_id}>
                <p className="font-display font-semibold text-asphalt">
                  {pickText(fix.title, locale)}
                </p>
                <ol className="mt-1 list-decimal space-y-1 pl-5">
                  {fix.steps.map((step, i) => (
                    <li key={i} className="text-[15px] text-gravel">
                      {pickText(step, locale)}
                    </li>
                  ))}
                </ol>
              </div>
            ))}
          </div>
        </div>
      </>
    );
  }

  return (
    <div className="board board-l-gravel p-5">
      <p className="label text-gravel">{t("detail.notEligibleReason")}</p>
      <ul className="mt-1.5 list-disc space-y-1.5 pl-5">
        {result.reasons.map((reason, i) => (
          <li key={i} className="text-asphalt">
            {pickText(reason.message, locale)}
          </li>
        ))}
      </ul>
      <p className="mt-3 text-[13px] leading-[1.5] text-gravel">
        {t("detail.criteriaChange")}
      </p>
    </div>
  );
}