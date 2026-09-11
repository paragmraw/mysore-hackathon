import { notFound } from "next/navigation";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { AppHeader } from "@/components/AppHeader";
import { CscFinder } from "@/components/csc-finder";
import { buttonClass } from "@/components/Button";
import { SchemeStatusBadge, SchemeVerdictBoards } from "@/components/scheme-verdict";
import { getScheme } from "@/lib/api";
import { pickText } from "@/lib/localize";
import type { Channel, SchemeRecord } from "@/lib/types";

export const dynamic = "force-dynamic";

function formatDate(iso: string, locale: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  try {
    return new Intl.DateTimeFormat(locale === "kn" ? "kn-IN" : "en-IN", {
      dateStyle: "medium",
    }).format(date);
  } catch {
    return iso;
  }
}

export default async function SchemeDetailPage({
  params,
}: PageProps<"/[locale]/scheme/[id]">) {
  const { locale, id } = await params;
  setRequestLocale(locale);

  const t = await getTranslations();

  let scheme: SchemeRecord | null = null;
  try {
    scheme = await getScheme(id, locale);
  } catch {
    notFound();
  }
  if (!scheme) notFound();

  const portals = scheme.channels.filter(
    (channel): channel is Extract<Channel, { type: "portal" }> =>
      channel.type === "portal",
  );
  const hasCsc = scheme.channels.some((channel) => channel.type === "csc");
  const verifiedDate = formatDate(scheme.last_verified, locale);

  return (
    <>
      <AppHeader back={{ href: "/results", label: t("back") }} />
      <main className="mx-auto w-full max-w-3xl flex-1 px-4 pb-10 pt-8 md:px-6 lg:grid lg:grid-cols-2 lg:gap-x-12">
        <div className="flex flex-col gap-6 lg:justify-center">
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="title text-asphalt">
              {pickText(scheme.name, locale)}
            </h1>
            <SchemeStatusBadge schemeId={scheme.id} />
          </div>

          <div className="board p-5">
            <p className="label text-gravel">
              {t("detail.whatYouGet")}
            </p>
            <p className="mt-1.5 text-[17px] text-asphalt">
              {pickText(scheme.benefit, locale)}
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              <span className="pill bg-arishina text-asphalt tabular-nums">
                {pickText(scheme.amount, locale)}
              </span>
              <span className="pill border-2 border-kerb-deep text-asphalt">
                {t("detail.deadline")}: {pickText(scheme.deadline, locale)}
              </span>
            </div>
          </div>
        </div>

        <div className="mt-6 flex flex-col gap-4 lg:mt-0">
          <SchemeVerdictBoards schemeId={scheme.id} />

          <div className="board p-5">
            <p className="label text-gravel">
              {t("detail.eligibility")}
            </p>
            <ul className="mt-1.5 list-disc space-y-1.5 pl-5">
              {scheme.eligibility_criteria.map((item, i) => (
                <li key={i} className="text-asphalt">
                  {pickText(item, locale)}
                </li>
              ))}
            </ul>
            {scheme.criteria_note && (
              <p className="mt-3 text-[13px] leading-[1.5] text-gravel">
                {pickText(scheme.criteria_note, locale)}
              </p>
            )}
          </div>

          <div className="board p-5">
            <p className="label text-gravel">
              {t("detail.howToApply")}
            </p>
            <ol className="mt-1.5 list-decimal space-y-1.5 pl-5">
              {scheme.application_steps.map((step, i) => (
                <li key={i} className="text-asphalt">
                  {pickText(step, locale)}
                </li>
              ))}
            </ol>
          </div>

          <div className="board p-5">
            <p className="label text-gravel">
              {t("detail.checklist")}
            </p>
            <ul className="mt-3 flex flex-col gap-2.5">
              {scheme.docs.map((doc, i) => (
                <li key={i} className="flex items-start gap-2.5">
                  <span
                    aria-hidden="true"
                    className="mt-[5px] size-4 shrink-0 rounded-[3px] border-2 border-kerb-deep bg-board"
                  />
                  <span className="text-[15px] text-asphalt">
                    {pickText(doc, locale)}
                  </span>
                </li>
              ))}
            </ul>
          </div>

          <div className="board p-5">
            <p className="label text-gravel">
              {t("detail.whereToApply")}
            </p>
            <div className="mt-3 flex flex-col gap-3">
              {portals.map((portal, i) => (
                <a
                  key={i}
                  href={portal.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={buttonClass("secondary", true)}
                >
                  {pickText(portal.label, locale)}
                </a>
              ))}
              {hasCsc && (
                <div className="mt-1 border-t border-kerb pt-3">
                  <p className="label text-gravel">{t("csc.title")}</p>
                  <p className="mt-1 text-[13px] leading-[1.5] text-gravel">
                    {t("csc.sub")}
                  </p>
                  <div className="mt-3">
                    <CscFinder limit={3} />
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="flex flex-col gap-1.5">
            <p className="text-[13px] leading-[1.5] text-gravel">
              {t("detail.verifiedOn", { date: verifiedDate })} ·{" "}
              <a
                href={scheme.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="underline underline-offset-2 focus-ring"
              >
                {t("detail.source")}
              </a>
            </p>
            <p className="text-[13px] leading-[1.5] text-gravel">
              {t("detail.screeningOnly")}
            </p>
          </div>
        </div>
      </main>
    </>
  );
}