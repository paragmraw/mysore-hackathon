import { getTranslations, setRequestLocale } from "next-intl/server";
import { AppHeader } from "@/components/AppHeader";
import { CscFinder } from "@/components/csc-finder";

export default async function CscPage({ params }: PageProps<"/[locale]/csc">) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("csc");

  return (
    <>
      <AppHeader />
      <main className="mx-auto flex w-full max-w-xl flex-1 flex-col px-4 pb-10 pt-6 md:px-6 md:pt-8">
        <h1 className="title text-asphalt">{t("title")}</h1>
        <p className="mt-2 text-[15px] text-gravel">{t("sub")}</p>
        <div className="mt-6">
          <div className="board p-5">
            <CscFinder />
          </div>
        </div>
      </main>
    </>
  );
}