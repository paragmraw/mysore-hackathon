"use client";

import { useMemo, useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { AppHeader } from "@/components/AppHeader";
import { Button, buttonClass } from "@/components/Button";
import { Chip } from "@/components/Chip";
import { RouteStrip } from "@/components/RouteStrip";
import { Link, useRouter } from "@/i18n/navigation";
import { postQuickMatch } from "@/lib/api-client";
import { pickText } from "@/lib/localize";
import { QUICK_KEY, writeJson } from "@/lib/session";
import { useUser } from "@/lib/user-context";
import type { Question, QuickMatchResponse, ShowIfMap } from "@/lib/types";

type Answers = Record<string, string | null>;

const inr = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 0,
});

function formatINR(n: number): string {
  return inr.format(n);
}

function showIfSatisfied(
  showIf: ShowIfMap | undefined,
  answers: Answers,
): boolean {
  if (!showIf) return true;
  for (const [ref, condition] of Object.entries(showIf)) {
    const answer = answers[ref];
    if (typeof answer !== "string" || answer === "") return false;
    if (Array.isArray(condition)) {
      if (!condition.includes(answer)) return false;
    } else {
      const value = Number(answer);
      if (Number.isNaN(value)) return false;
      if (condition.min != null && value < condition.min) return false;
      if (condition.max != null && value > condition.max) return false;
    }
  }
  return true;
}

function computeVisible(
  questions: readonly Question[],
  answers: Answers,
): Question[] {
  return questions.filter((q) => showIfSatisfied(q.showIf, answers));
}

function isAnswered(q: Question, answers: Answers): boolean {
  const value = answers[q.id];
  if (typeof value !== "string") return false;
  if (q.type === "single_select") return value.length > 0;
  if (q.type === "number") return /^\d+$/.test(value);
  return /^\d{6}$/.test(value); // pincode
}

export function QuickCheckWizard({
  questions,
}: {
  questions: readonly Question[];
}) {
  const t = useTranslations("quickCheck");
  const tIntake = useTranslations("intake");
  const tProcessing = useTranslations("processing");
  const tBack = useTranslations();
  const locale = useLocale();
  const router = useRouter();
  const { user } = useUser();

  const [phase, setPhase] = useState<"questions" | "loading" | "teaser" | "error">(
    "questions",
  );
  const [qIndex, setQIndex] = useState(0);
  const [answers, setAnswers] = useState<Answers>({});
  const [resp, setResp] = useState<QuickMatchResponse | null>(null);

  const visible = useMemo(
    () => computeVisible(questions, answers),
    [questions, answers],
  );
  const idx = Math.min(qIndex, visible.length - 1);
  const q = visible[idx];
  const selected = typeof q !== "undefined" ? answers[q.id] : undefined;

  const applyAnswer = (id: string, value: string | null) => {
    setAnswers((prev) => {
      const next = { ...prev, [id]: value };
      const visibleIds = new Set(
        computeVisible(questions, next).map((vq) => vq.id),
      );
      for (const key of Object.keys(next)) {
        if (key !== id && !visibleIds.has(key)) delete next[key];
      }
      return next;
    });
  };

  const runQuickMatch = async () => {
    setPhase("loading");
    try {
      const r = await postQuickMatch(answers, locale);
      writeJson(QUICK_KEY, { locale, answers });
      setResp(r);
      setPhase("teaser");
    } catch {
      setPhase("error");
    }
  };

  const next = () => {
    if (!q) return;
    if (idx < visible.length - 1) {
      setQIndex(idx + 1);
    } else {
      void runQuickMatch();
    }
  };

  const back = () => {
    if (idx > 0) {
      setQIndex(idx - 1);
    } else {
      router.push("/");
    }
  };

  const restart = () => {
    setPhase("questions");
    setQIndex(0);
    setAnswers({});
    setResp(null);
  };

  if (phase === "loading") {
    return (
      <>
        <AppHeader />
        <main className="mx-auto flex w-full max-w-xl flex-1 flex-col px-4 py-10 md:px-6">
          <div className="my-auto">
            <span className="pill inline-block bg-arishina text-asphalt">
              {tProcessing("enRoute")}
            </span>
            <p className="mt-6 text-[17px] text-asphalt">
              {tProcessing("slow")}
            </p>
          </div>
        </main>
      </>
    );
  }

  if (phase === "error") {
    return (
      <>
        <AppHeader />
        <main className="mx-auto flex w-full max-w-xl flex-1 flex-col px-4 py-10 md:px-6">
          <div className="my-auto">
            <div className="board board-l-kumkuma p-5">
              <p className="label text-kumkuma">{t("error")}</p>
            </div>
            <div className="mt-4 flex flex-col gap-2">
              <Button block onClick={() => void runQuickMatch()}>
                {t("retry")}
              </Button>
              <button
                onClick={restart}
                className="mx-auto mt-1 text-[15px] font-semibold text-asphalt underline decoration-kerb-deep underline-offset-4 hover:decoration-asphalt focus-ring"
              >
                {t("backToQuestions")}
              </button>
            </div>
          </div>
        </main>
      </>
    );
  }

  if (phase === "teaser" && resp) {
    const month = resp.benefit_total.month;
    const oneTime = resp.benefit_total["one-time"];
    return (
      <>
        <AppHeader />
        <main className="mx-auto flex w-full max-w-xl flex-1 flex-col px-4 pt-6 md:px-6 md:pt-8">
          <div className="my-auto">
            <h1 className="title text-asphalt">{t("teaserTitle")}</h1>
            <p className="mt-2 text-[15px] text-gravel">{t("teaserSub")}</p>
            <ul className="mt-6 flex flex-col gap-3">
              {resp.results.slice(0, 5).map((r) => (
                <li
                  key={r.scheme_id}
                  className="board flex items-center justify-between gap-3 p-4"
                >
                  <span className="min-w-0 font-display text-[17px] font-bold text-asphalt">
                    {pickText(r.name, locale)}
                  </span>
                  <span className="shrink-0 text-[15px] font-semibold tabular-nums text-asphalt">
                    {pickText(r.amount, locale)}
                  </span>
                </li>
              ))}
            </ul>
            {(month > 0 || oneTime > 0) && (
              <div className="board board-l-arishina mt-4 p-4">
                {month > 0 && (
                  <p className="text-[17px] font-semibold text-asphalt">
                    {t("worthMonth", { amount: formatINR(month) })}
                  </p>
                )}
                {oneTime > 0 && (
                  <p className="mt-1 text-[15px] text-gravel">
                    {t("worthOneTime", { amount: formatINR(oneTime) })}
                  </p>
                )}
              </div>
            )}
            <div className="mt-6 flex flex-col gap-2">
              {user ? (
                <Link href="/intake" className={buttonClass("primary", true)}>
                  {t("continueCta")}
                </Link>
              ) : (
                <>
                  <Link
                    href="/login?next=/intake"
                    className={buttonClass("primary", true)}
                  >
                    {t("loginCta")}
                  </Link>
                  <Link
                    href="/register?next=/intake"
                    className={buttonClass("secondary", true)}
                  >
                    {t("registerCta")}
                  </Link>
                </>
              )}
              <button
                onClick={restart}
                className="mx-auto mt-1 text-[15px] font-semibold text-asphalt underline decoration-kerb-deep underline-offset-4 hover:decoration-asphalt focus-ring"
              >
                {t("backToQuestions")}
              </button>
            </div>
          </div>
        </main>
      </>
    );
  }

  if (!q) return null;

  const label = pickText(q.label, locale);
  const isLast = idx === visible.length - 1;
  const isText = q.type === "number" || q.type === "pincode";
  const inputValue = typeof selected === "string" ? selected : "";

  const setInput = (raw: string) => {
    const digits = raw.replace(/\D/g, "");
    const capped =
      q.type === "pincode" ? digits.slice(0, 6) : digits.slice(0, 9);
    applyAnswer(q.id, capped === "" ? null : capped);
  };

  return (
    <>
      <AppHeader back={{ label: tBack("back"), onClick: back }} />
      <main className="mx-auto flex w-full max-w-xl flex-1 flex-col px-4 pt-6 md:px-6 md:pt-8">
        <div className="my-auto">
          <h1 className="title text-asphalt">{t("title")}</h1>
          <p className="mt-2 text-[15px] text-gravel">{t("sub")}</p>
          <div className="mt-6">
            <p className="label tabular-nums text-gravel">
              {tIntake("stopOf", { current: idx + 1, total: visible.length })}
            </p>
            <RouteStrip
              current={idx + 1}
              total={visible.length}
            />
            <div
              key={q.id}
              className="animate-step-in mt-6 flex flex-col gap-6"
            >
              <h2
                tabIndex={-1}
                className="title text-asphalt"
              >
                {label}
              </h2>
              {q.type === "single_select" && (
                <div
                  className={
                    q.cols === 1
                      ? "grid grid-cols-1 gap-3 md:grid-cols-2"
                      : "grid grid-cols-2 gap-3"
                  }
                >
                  {(q.options ?? []).map((o) => (
                    <Chip
                      key={o.value}
                      selected={selected === o.value}
                      onClick={() => applyAnswer(q.id, o.value)}
                    >
                      {pickText(o.label, locale)}
                    </Chip>
                  ))}
                </div>
              )}
              {isText && (
                <div className="flex flex-col gap-3">
                  <input
                    autoFocus
                    type="text"
                    inputMode="numeric"
                    autoComplete="off"
                    enterKeyHint={isLast ? "done" : "next"}
                    value={inputValue}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && isAnswered(q, answers)) next();
                    }}
                    aria-label={label}
                    className="min-h-12 w-44 max-w-full rounded-tile border-2 border-kerb-deep bg-board px-4 py-3 text-[17px] tabular-nums focus-ring"
                  />
                </div>
              )}
            </div>
          </div>
        </div>
        <div className="sticky bottom-0 -mx-4 mt-6 border-t-2 border-kerb-deep bg-board px-4 pb-5 pt-3 md:-mx-6 md:px-6">
          <div className="flex flex-col gap-2">
            <Button block disabled={!isAnswered(q, answers)} onClick={next}>
              {isLast ? tIntake("finish") : tIntake("continue")}
            </Button>
          </div>
        </div>
      </main>
    </>
  );
}
