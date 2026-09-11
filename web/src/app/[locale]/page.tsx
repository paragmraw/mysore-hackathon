import { getTranslations, setRequestLocale } from "next-intl/server";
import { AppHeader } from "@/components/AppHeader";
import { buttonClass } from "@/components/Button";
import { GoIcon, LockIcon } from "@/components/icons";
import { Link } from "@/i18n/navigation";
import { getMeta } from "@/lib/api";
import type { Meta } from "@/lib/types";

const FALLBACK_META: Meta = {
  schemes: 19,
  questions: 23,
  last_data_update: "",
};

export default async function LandingPage({
  params,
}: PageProps<"/[locale]">) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("landing");

  let meta: Meta | null = null;
  try {
    meta = await getMeta();
  } catch {
    meta = null; 
  }
  const schemes = meta?.schemes ?? FALLBACK_META.schemes;
  const questions = meta?.questions ?? FALLBACK_META.questions;

  return (
    <>
      <AppHeader />
      <main className="mx-auto flex w-full max-w-xl flex-1 flex-col px-4 pb-6 pt-6 md:px-6 md:pb-10 md:pt-10">
        <div className="board-flag flex flex-1 flex-col rounded-board border-[3px] border-asphalt p-6 md:p-8">
          <p className="label tabular-nums text-asphalt">
            {t("boardKicker", { schemes, questions })}
          </p>
          <div className="center-line mt-5" aria-hidden="true" />
          <div className="my-auto py-8 md:py-12">
            <h1 className="font-display text-[32px] font-bold leading-[1.3] text-asphalt">
              {t("headline")}
            </h1>
            <p className="mt-3 text-[17px] text-asphalt">
              {t("sub")}
            </p>
          </div>
          <Link
            href="/quick-check"
            className={buttonClass("primary", true)}
          >
            {t("start")}
          </Link>
        </div>

        <Link
          href="/csc"
          aria-label={t("cscLink")}
          className="board mt-4 flex items-center gap-4 p-4 focus-ring"
        >
          <span className="min-w-0 flex-1">
            <span className="block font-display text-[17px] font-bold text-asphalt">
              {t("cscTitle")}
            </span>
            <span className="block text-[14px] text-gravel">
              {t("cscSub")}
            </span>
          </span>
          <GoIcon className="h-[18px] w-[18px] shrink-0 text-gravel" />
        </Link>

        <p className="mt-4 flex items-start gap-2 text-[13px] leading-[1.5] text-gravel">
          <LockIcon className="w-[18px] shrink-0 text-gravel" />
          <span>{t("privacy")}</span>
        </p>
      </main>
    </>
  );
}