import { getTranslations, setRequestLocale } from "next-intl/server";
import { AppHeader } from "@/components/AppHeader";
import { QuickCheckWizard } from "@/components/quick-check-wizard";
import { ReloadButton } from "@/components/reload-button";
import { getQuestions } from "@/lib/api";
import type { Question } from "@/lib/types";

export const dynamic = "force-dynamic";

export default async function QuickCheckPage({
  params,
}: PageProps<"/[locale]/quick-check">) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("intake");

  let questions: Question[] | null = null;
  try {
    questions = await getQuestions(locale, "quick");
  } catch {
    questions = null;
  }

  if (!questions || questions.length === 0) {
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

  return <QuickCheckWizard questions={questions} />;
}
