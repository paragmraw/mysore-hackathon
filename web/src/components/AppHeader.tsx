"use client";

import Image from "next/image";
import { useLocale, useTranslations } from "next-intl";
import { Link, usePathname } from "@/i18n/navigation";
import { routing } from "@/i18n/routing";
import { useUser } from "@/lib/user-context";
import { BackIcon } from "./icons";

const localeLabels = { en: "English", kn: "ಕನ್ನಡ" } as const;

function LangToggle() {
  const t = useTranslations();
  const locale = useLocale();
  const pathname = usePathname();
  const activeIndex = routing.locales.indexOf(
    locale as (typeof routing.locales)[number],
  );
  const enActive = activeIndex === 0;

  return (
    <div
      role="group"
      aria-label={t("language")}
      className="relative inline-grid grid-cols-2 rounded-full border border-fog/25 p-[3px]"
    >
      <span
        aria-hidden="true"
        className={`absolute inset-y-[3px] left-[3px] w-[calc(50%-3px)] rounded-full transition-transform duration-200 ease-out ${
          enActive ? "bg-arishina" : "bg-kumkuma"
        }`}
        style={{ transform: `translateX(${activeIndex * 100}%)` }}
      />
      {routing.locales.map((l) => (
        <Link
          key={l}
          href={pathname}
          locale={l}
          aria-current={l === locale ? "true" : undefined}
          className={`relative z-10 grid h-11 place-items-center px-4 label transition-colors focus-ring-invert ${
            l === locale
              ? enActive
                ? "text-asphalt"
                : "text-fog"
              : "text-fog/60 hover:text-fog"
          }`}
        >
          {localeLabels[l]}
        </Link>
      ))}
    </div>
  );
}

type AppHeaderBack = {
  label: string;
  href?: string;
  onClick?: () => void;
};
const backCls =
  "grid size-11 place-items-center rounded-tile text-fog/80 transition-colors hover:text-fog focus-ring-invert";

export function AppHeader({ back }: { back?: AppHeaderBack }) {
  const t = useTranslations();
  const tAuth = useTranslations("auth");
  const tProfile = useTranslations("profile");
  const brand = t("brand");
  const { user, ready } = useUser();

  return (
    <header className="sticky top-0 z-20 flex h-14 items-center justify-between bg-asphalt px-4 text-fog md:h-16">
      <span className="flex items-center gap-1">
        {back &&
          (back.href ? (
            <Link
              href={back.href}
              aria-label={back.label}
              className={backCls}
            >
              <BackIcon />
            </Link>
          ) : (
            <button
              onClick={back.onClick}
              aria-label={back.label}
              className={backCls}
            >
              <BackIcon />
            </button>
          ))}
        <Link
          href="/"
          aria-label={t("home")}
          className="flex items-center gap-2 rounded-tile px-1.5 py-2 focus-ring-invert"
        >
          <Image
            src="/govt-karnataka.webp"
            alt=""
            width={252}
            height={216}
            className="h-7 w-auto md:h-8"
          />
          <span className="brand-flag font-display text-lg font-bold leading-none">
            {brand}
          </span>
        </Link>
      </span>
      <span className="flex items-center gap-1">
        {ready && (
          <Link
            href={user ? "/profile" : "/login"}
            className="label grid h-11 max-w-36 place-items-center truncate rounded-tile px-3 text-fog/80 transition-colors hover:text-fog focus-ring-invert"
          >
            {user ? user.name || tProfile("navProfile") : tAuth("navLogin")}
          </Link>
        )}
        <LangToggle />
      </span>
    </header>
  );
}