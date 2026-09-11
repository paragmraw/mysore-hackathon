"use client";

import { useEffect, useMemo, useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { AppHeader } from "@/components/AppHeader";
import { Button } from "@/components/Button";
import { Chip } from "@/components/Chip";
import { RouteStrip } from "@/components/RouteStrip";
import { useRouter } from "@/i18n/navigation";
import { updateMe } from "@/lib/auth-client";
import { pickText } from "@/lib/localize";
import { ANSWERS_KEY, QUICK_KEY, readJson, writeJson } from "@/lib/session";
import { useUser } from "@/lib/user-context";
import type { Question, ShowIfMap } from "@/lib/types";

type Answers = Record<string, string | null>;

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

export function IntakeWizard({ questions }: { questions: readonly Question[] }) {
  const t = useTranslations("intake");
  const tBack = useTranslations();
  const locale = useLocale();
  const router = useRouter();
  const { user } = useUser();

  const [qIndex, setQIndex] = useState(0);
  const [answers, setAnswers] = useState<Answers>(() => {
    const quick = readJson<{ answers?: Answers }>(QUICK_KEY)?.answers ?? {};
    return { ...quick };
  });

  useEffect(() => {
    if (user?.answers && Object.keys(user.answers).length > 0) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- pre-fill merge after async profile load; user is referentially stable, runs once per session change
      setAnswers((prev) => ({ ...user.answers, ...prev }));
    }
  }, [user]);

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

  const finish = () => {
    if (user) {
      updateMe({ answers }).catch(() => {});
    }
    writeJson(ANSWERS_KEY, { locale, answers });
    router.push("/processing");
  };

  const next = () => {
    if (!q) return;
    if (idx < visible.length - 1) {
      setQIndex(idx + 1);
    } else {
      void finish();
    }
  };

  const back = () => {
    if (idx > 0) {
      setQIndex(idx - 1);
    } else {
      router.push("/");
    }
  };

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
            <p className="label tabular-nums text-gravel">
              {t("stopOf", { current: idx + 1, total: visible.length })}
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
                  {q.type === "pincode" && (
                    <p className="text-[13px] leading-[1.5] text-gravel">
                      {t("pincodeNote")}
                    </p>
                  )}
                </div>
              )}
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
                {t("skip")}
              </Button>
            )}
            <Button block disabled={!isAnswered(q, answers)} onClick={next}>
              {isLast ? t("finish") : t("continue")}
            </Button>
          </div>
        </div>
      </main>
    </>
  );
}