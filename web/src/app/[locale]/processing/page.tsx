"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { AppHeader } from "@/components/AppHeader";
import { Button, buttonClass } from "@/components/Button";
import { RouteTrack } from "@/components/RouteTrack";
import { Link, useRouter } from "@/i18n/navigation";
import { postMatch } from "@/lib/api-client";
import { ANSWERS_KEY, RESULTS_KEY, readJson, writeJson } from "@/lib/session";
import type { MatchResponse } from "@/lib/types";

type StoredAnswers = {
  locale: string;
  answers: Record<string, string | null>;
};

export default function ProcessingPage() {
  const t = useTranslations("processing");
  const locale = useLocale();
  const router = useRouter();

  const [pct, setPct] = useState(0);
  const [count, setCount] = useState<number | null>(null);
  const [fetchState, setFetchState] = useState<"pending" | "ok" | "error">(
    "pending",
  );
  const [resp, setResp] = useState<MatchResponse | null>(null);
  const answersRef = useRef<Record<string, string | null> | null>(null);
  const navigateRef = useRef(false);

  const runMatch = useCallback(
    (answers: Record<string, string | null>) => {
      void (async () => {
        try {
          const r = await postMatch(answers, locale);
          setResp(r);
          setCount(r.results.length + r.hidden_route_groups.length);
          setFetchState("ok");
        } catch {
          setFetchState("error");
        }
      })();
    },
    [locale],
  );

  useEffect(() => {
    const id = setInterval(() => {
      setPct((p) => {
        if (p >= 100) {
          clearInterval(id);
          return 100;
        }
        return p + 8;
      });
    }, 120);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    let cancelled = false;
    void Promise.resolve().then(() => {
      if (cancelled) return;
      const stored = readJson<StoredAnswers>(ANSWERS_KEY);
      const answers = stored?.answers;
      if (!answers || Object.keys(answers).length === 0) {
        router.replace("/intake");
        return;
      }
      answersRef.current = answers;
      runMatch(answers);
    });
    return () => {
      cancelled = true;
    };
  }, [router, runMatch]);

  useEffect(() => {
    if (pct < 100 || fetchState !== "ok" || !resp) return;
    if (navigateRef.current) return;
    navigateRef.current = true;
    writeJson(RESULTS_KEY, resp);
    router.push("/results");
  }, [pct, fetchState, resp, router]);

  const retry = () => {
    if (!answersRef.current) return;
    setFetchState("pending");
    runMatch(answersRef.current);
  };

  return (
    <>
      <AppHeader />
      <main className="mx-auto flex w-full max-w-xl flex-1 flex-col px-4 py-10 md:px-6">
        {fetchState === "error" ? (
          <div className="my-auto">
            <div className="board board-l-kumkuma p-5">
              <p className="label text-kumkuma">{t("error")}</p>
              <p className="mt-1.5 text-asphalt">{t("errorHint")}</p>
            </div>
            <div className="mt-4 flex flex-col gap-2">
              <Button block onClick={retry}>
                {t("retry")}
              </Button>
              <Link href="/intake" className={buttonClass("secondary", true)}>
                {t("backToIntake")}
              </Link>
            </div>
          </div>
        ) : (
          <div className="my-auto">
            <span className="pill inline-block bg-arishina text-asphalt">
              {t("enRoute")}
            </span>
            <div className="mt-6">
              <RouteTrack pct={pct} />
            </div>
            <p
              className={`mt-6 text-[17px] text-asphalt${count === null ? " invisible" : ""}`}
            >
              {count === null ? "—" : t("checking", { count })}
            </p>
            <p className="mt-2 text-[13px] leading-[1.5] text-gravel">
              {t("slow")}
            </p>
          </div>
        )}
      </main>
    </>
  );
}