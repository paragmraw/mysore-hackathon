"use client";

import { useEffect, useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { AppHeader } from "@/components/AppHeader";
import { Button } from "@/components/Button";
import { CscFinder } from "@/components/csc-finder";
import { ChevronIcon, GoIcon } from "@/components/icons";
import { StatusBadge } from "@/components/StatusBadge";
import { Link, useRouter } from "@/i18n/navigation";
import { pickText } from "@/lib/localize";
import { ANSWERS_KEY, RESULTS_KEY, readJson } from "@/lib/session";
import { useUser } from "@/lib/user-context";
import type { MatchResponse, MatchResult } from "@/lib/types";

type GroupStatus = MatchResult["status"];

const GROUP_ORDER: GroupStatus[] = ["eligible", "blocked", "not_eligible"];

export default function ResultsPage() {
  const t = useTranslations();
  const router = useRouter();
  const [resp, setResp] = useState<MatchResponse | "loading">("loading");
  const [notEligibleOpen, setNotEligibleOpen] = useState(false);
  const [initialPincode, setInitialPincode] = useState("");

  useEffect(() => {
    let cancelled = false;
    void Promise.resolve().then(() => {
      if (cancelled) return;
      const data = readJson<MatchResponse>(RESULTS_KEY);
      if (!data || !Array.isArray(data.results)) {
        router.replace("/intake");
        return;
      }
      const stored = readJson<{ answers?: Record<string, string | null> }>(
        ANSWERS_KEY,
      );
      const pin = stored?.answers?.pincode;
      if (typeof pin === "string") setInitialPincode(pin);
      setResp(data);
    });
    return () => {
      cancelled = true;
    };
  }, [router]);

  if (resp === "loading") {
    return (
      <>
        <AppHeader />
        <main className="mx-auto w-full max-w-2xl flex-1 px-4 pt-6 md:px-6" />
      </>
    );
  }

  const groups = GROUP_ORDER.map((status) => ({
    status,
    items: resp.results.filter((r) => r.status === status),
  })).filter((g) => g.items.length > 0);

  return (
    <>
      <AppHeader />
      <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col px-4 pb-10 pt-6 md:px-6 md:pt-8">
        <div className="my-auto">
        <h1 className="title text-asphalt">
          {t("results.title")}
        </h1>
        <div className="center-line mt-4 mb-8" aria-hidden="true" />

        {groups.map((group) => {
          const tabLabel =
            group.status === "blocked"
              ? t("results.oneDiversion")
              : t(`status.${statusKey(group.status)}`);
          const count = (
            <span className="text-[13px] text-gravel tabular-nums">
              {group.items.length}
            </span>
          );
          const board = (
            <div className="board">
              {group.items.map((r, i) => (
                <ResultRow key={r.scheme_id} result={r} first={i === 0} />
              ))}
            </div>
          );

          if (group.status === "not_eligible") {
            return (
              <section key={group.status}>
                <div className="mt-8 mb-3 flex items-baseline gap-2.5">
                  <button
                    type="button"
                    className="pill inline-flex items-center gap-2 bg-asphalt text-fog focus-ring"
                    aria-expanded={notEligibleOpen}
                    aria-controls="not-eligible-panel"
                    onClick={() => setNotEligibleOpen(!notEligibleOpen)}
                  >
                    {tabLabel}
                    <ChevronIcon
                      className={`h-[14px] w-[14px] transition-transform duration-200 ${
                        notEligibleOpen ? "rotate-180" : ""
                      }`}
                    />
                  </button>
                  {count}
                </div>
                {notEligibleOpen && board}
              </section>
            );
          }

          return (
            <section key={group.status}>
              <div className="mt-8 mb-3 flex items-baseline gap-2.5">
                <span className="pill bg-asphalt text-fog">
                  {tabLabel}
                </span>
                {count}
              </div>
              {board}
            </section>
          );
        })}

        <section className="mt-10" aria-labelledby="csc-heading">
          <div className="board p-5">
            <p id="csc-heading" className="label text-asphalt">
              {t("csc.title")}
            </p>
            <p className="mt-1.5 text-[15px] text-gravel">
              {t("csc.sub")}
            </p>
            <div className="mt-4">
              <CscFinder initialPincode={initialPincode} />
            </div>
          </div>
        </section>
        </div>
      </main>
    </>
  );
}

function statusKey(status: GroupStatus): string {
  return status === "not_eligible" ? "notEligible" : status;
}

function ResultRow({
  result,
  first,
}: {
  result: MatchResult;
  first: boolean;
}) {
  const t = useTranslations();
  const locale = useLocale();
  const router = useRouter();
  const { user } = useUser();

  const label =
    result.status === "blocked"
      ? t("results.fixesNeeded", { count: result.fixes.length })
      : t(`status.${statusKey(result.status)}`);
  const showReason = result.status !== "eligible" && result.reasons.length > 0;
  const showDeepCheck = !!user && result.status !== "not_eligible";

  return (
    <div
      className={`flex items-center gap-4 px-4 py-4 text-left ${
        first ? "" : "border-t border-kerb"
      }`}
    >
      <Link
        href={`/scheme/${result.scheme_id}`}
        aria-label={`${pickText(result.name, locale)} — ${t(`status.${statusKey(result.status)}Aria`)}`}
        className="flex min-w-0 flex-1 items-center gap-4 focus-ring"
      >
        <StatusBadge
          status={result.status}
          label={label}
          aria={t(`status.${statusKey(result.status)}Aria`)}
        />
        <span className="min-w-0 flex-1">
          <span className="block font-display text-[20px] font-bold leading-[1.3] text-asphalt">
            {pickText(result.name, locale)}
          </span>
          <span className="block text-[15px] text-gravel">
            {pickText(result.summ, locale)}
          </span>
          {showReason && (
            <span className="block text-[13px] leading-[1.5] text-gravel">
              {pickText(result.reasons[0].message, locale)}
            </span>
          )}
        </span>
        <GoIcon className="h-[18px] w-[18px] shrink-0 text-gravel" />
      </Link>
      {showDeepCheck && (
        <Button
          variant="secondary"
          className="shrink-0"
          onClick={() => router.push(`/deep-check/${result.scheme_id}`)}
        >
          {t("results.deepCheck")}
        </Button>
      )}
    </div>
  );
}
