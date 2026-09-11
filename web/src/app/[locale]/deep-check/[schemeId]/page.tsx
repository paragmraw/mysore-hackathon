import { getTranslations, setRequestLocale } from "next-intl/server";
import { AppHeader } from "@/components/AppHeader";
import { DeepCheckWizard } from "@/components/deep-check-wizard";
import { ReloadButton } from "@/components/reload-button";
import { getQuestions, getScheme } from "@/lib/api";
import type { Question, SchemeRecord } from "@/lib/types";

export const dynamic = "force-dynamic";

export default async function DeepCheckPage({
  params,
}: PageProps<"/[locale]/deep-check/[schemeId]">) {
  const { locale, schemeId } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("intake");

  let questions: Question[] | null = null;
  let scheme: SchemeRecord | null = null;
  try {
    [questions, scheme] = await Promise.all([
      getQuestions(locale, "deep", schemeId),
      getScheme(schemeId, locale),
    ]);
  } catch {
    questions = null;
    scheme = null;
  }

  if (!questions || questions.length === 0 || !scheme) {
    return (
      <>
        <AppHeader />
        <main className="mx-auto flex w-full max-w-xl flex-1 flex-col justify-center px-4 py-10 md:px-6">
          <div className="board board-l-kumkuma p-5">
            <p className="label text-kumkuma">{t("loadError")}</p>
            <p className="mt-1.5 text-asphalt">
              {t("loadErrorHint")}
            </p>
          </div>
          <div className="mt-4">
            <ReloadButton label={t("retry")} />
          </div>
        </main>
      </>
    );
  }

  return <DeepCheckWizard questions={questions} scheme={scheme} />;
}
