"use client";

import { useEffect, useMemo, useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { AppHeader } from "@/components/AppHeader";
import { Button, buttonClass } from "@/components/Button";
import { Chip } from "@/components/Chip";
import { RouteStrip } from "@/components/RouteStrip";
import { Link, useRouter } from "@/i18n/navigation";
import { postDeepCheck } from "@/lib/api-client";
import { updateMe } from "@/lib/auth-client";
import { pickText } from "@/lib/localize";
import { useUser } from "@/lib/user-context";
import type {
  DeepCheckResponse,
  Question,
  SchemeRecord,
  ShowIfMap,
} from "@/lib/types";

type Answers = Record<string, string | null>;
type Phase = "questions" | "loading" | "result" | "error";

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

export function DeepCheckWizard({
  questions,
  scheme,
}: {
  questions: readonly Question[];
  scheme: SchemeRecord;
}) {
  const t = useTranslations("deepCheck");
  const tIntake = useTranslations("intake");
  const tDetail = useTranslations("detail");
  const tProcessing = useTranslations("processing");
  const tBack = useTranslations();
  const locale = useLocale();
  const router = useRouter();
  const { user, ready } = useUser();

  const [phase, setPhase] = useState<Phase>("questions");
  const [qIndex, setQIndex] = useState(0);
  const [answers, setAnswers] = useState<Answers>(() => {
    const saved = user?.deep_check_answers ?? {};
    return { ...saved };
  });
  const [result, setResult] = useState<DeepCheckResponse | null>(null);
  useEffect(() => {
    if (
      user?.deep_check_answers &&
      Object.keys(user.deep_check_answers).length > 0
    ) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- pre-fill merge after async profile load; user is referentially stable, runs once per session change
      setAnswers((prev) => ({ ...user.deep_check_answers, ...prev }));
    }
  }, [user]);

  useEffect(() => {
    if (ready && !user) {
      router.replace(`/login?next=/deep-check/${scheme.id}`);
    }
  }, [ready, user, router, scheme.id]);

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

  const runDeepCheck = async () => {
    setPhase("loading");
    try {
      const r = await postDeepCheck(scheme.id, answers, locale);
      updateMe({ deep_check_answers: answers }).catch(() => {});
      setResult(r);
      setPhase("result");
    } catch {
      setPhase("error");
    }
  };

  const next = () => {
    if (!q) return;
    if (idx < visible.length - 1) {
      setQIndex(idx + 1);
    } else {
      void runDeepCheck();
    }
  };

  const back = () => {
    if (idx > 0) {
      setQIndex(idx - 1);
    } else {
      router.push("/results");
    }
  };

  if (!ready || !user) {
    return (
      <>
        <AppHeader />
        <main className="mx-auto flex w-full max-w-xl flex-1 flex-col px-4 pt-6 md:px-6 md:pt-8" />
      </>
    );
  }

  if (phase === "loading") {
    return (
      <>
        <AppHeader back={{ href: "/results", label: tBack("back") }} />
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
        <AppHeader back={{ href: "/results", label: tBack("back") }} />
        <main className="mx-auto flex w-full max-w-xl flex-1 flex-col px-4 py-10 md:px-6">
          <div className="my-auto">
            <div className="board board-l-kumkuma p-5">
              <p className="label text-kumkuma">{t("error")}</p>
            </div>
            <div className="mt-4">
              <Button block onClick={() => void runDeepCheck()}>
                {t("retry")}
              </Button>
            </div>
          </div>
        </main>
      </>
    );
  }

  if (phase === "result" && result) {
    return (
      <>
        <AppHeader back={{ href: "/results", label: tBack("back") }} />
        <main className="mx-auto flex w-full max-w-xl flex-1 flex-col px-4 pb-10 pt-6 md:px-6 md:pt-8">
          <div className="my-auto">
            <h1 className="title text-asphalt">
              {pickText(scheme.name, locale)}
            </h1>
            <div className="center-line mt-4 mb-8" aria-hidden="true" />

            {result.status === "eligible" ? (
              <div className="board board-l-arishina p-5">
                <p className="label text-asphalt">{t("eligibleTitle")}</p>
                <p className="mt-1.5 text-asphalt">{t("eligibleSub")}</p>
              </div>
            ) : result.status === "blocked" ? (
              <>
                <div className="board board-l-kumkuma p-5">
                  <p className="label text-kumkuma">{t("blockedTitle")}</p>
                  <ul className="mt-1.5 list-disc space-y-1.5 pl-5">
                    {result.reasons.map((reason, i) => (
                      <li key={i} className="text-asphalt">
                        {pickText(reason.message, locale)}
                      </li>
                    ))}
                  </ul>
                </div>
                <div className="board board-l-arishina mt-4 p-5">
                  <p className="label text-asphalt">{tDetail("howToFix")}</p>
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
            ) : (
              <div className="board board-l-gravel p-5">
                <p className="label text-gravel">{tDetail("notEligibleReason")}</p>
                <ul className="mt-1.5 list-disc space-y-1.5 pl-5">
                  {result.reasons.map((reason, i) => (
                    <li key={i} className="text-asphalt">
                      {pickText(reason.message, locale)}
                    </li>
                  ))}
                </ul>
                <p className="mt-3 text-[13px] leading-[1.5] text-gravel">
                  {tDetail("criteriaChange")}
                </p>
              </div>
            )}

            <p className="mt-4 text-[13px] leading-[1.5] text-gravel">
              {t("savedNote")}
            </p>
            <div className="mt-4">
              <Link href="/results" className={buttonClass("primary", true)}>
                {t("backToResults")}
              </Link>
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
            {q.optional && (
              <Button
                variant="secondary"
                block
                onClick={() => {
                  applyAnswer(q.id, null);
                  next();
                }}
              >
                {tIntake("skip")}
              </Button>
            )}
            <Button block disabled={!isAnswered(q, answers)} onClick={next}>
              {isLast ? tIntake("finish") : tIntake("continue")}
            </Button>
          </div>
        </div>
      </main>
    </>
  );
}
