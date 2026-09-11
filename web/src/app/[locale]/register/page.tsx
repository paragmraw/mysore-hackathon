"use client";

import { useState, type FormEvent } from "react";
import { useTranslations } from "next-intl";
import { AppHeader } from "@/components/AppHeader";
import { Button } from "@/components/Button";
import { Link, useRouter } from "@/i18n/navigation";
import { ApiError, BrowserApiError } from "@/lib/api-client";
import { register } from "@/lib/auth-client";
import { useUser } from "@/lib/user-context";

const MOBILE_RE = /^[6-9]\d{9}$/;
const PASSWORD_MIN = 8;

function safeNext(raw: string | null): string | null {
  return raw &&
    raw.startsWith("/") &&
    !raw.startsWith("//") &&
    !raw.includes("\\")
    ? raw
    : null;
}
function registerError(
  err: unknown,
  t: (key: string) => string,
): string {
  if (err instanceof ApiError && err.status !== 0) {
    const data =
      err instanceof BrowserApiError && typeof err.data === "object"
        ? (err.data as { detail?: unknown })
        : undefined;
    const detail = typeof data?.detail === "string" ? data.detail : "";
    if (/password/i.test(detail)) return t("authErrorWeakPassword");
    if (/exist|unique|already/i.test(detail)) return t("authErrorDuplicate");
    if (detail) return detail;
  }
  return t("authErrorGeneric");
}

export default function RegisterPage() {
  const t = useTranslations("auth");
  const router = useRouter();
  const { refresh } = useUser();
  const [mobile, setMobile] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const valid = MOBILE_RE.test(mobile) && password.length >= PASSWORD_MIN;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!valid || loading) return;
    setLoading(true);
    setError(null);
    try {
      await register(mobile, password, name.trim() || undefined);
      await refresh();
      const next = safeNext(
        new URLSearchParams(window.location.search).get("next"),
      );
      router.push(next ?? "/profile");
    } catch (err) {
      setLoading(false);
      setError(registerError(err, t));
    }
  };

  return (
    <>
      <AppHeader />
      <main className="mx-auto flex w-full max-w-xl flex-1 flex-col px-4 pb-10 pt-6 md:px-6 md:pt-8">
        <h1 className="title text-asphalt">{t("registerTitle")}</h1>
        <form onSubmit={submit} className="board mt-6 flex flex-col gap-4 p-5">
          <div className="flex flex-col gap-1.5">
            <label htmlFor="register-mobile" className="label text-gravel">
              {t("loginMobile")}
            </label>
            <input
              id="register-mobile"
              type="tel"
              inputMode="numeric"
              autoComplete="username"
              enterKeyHint="next"
              value={mobile}
              onChange={(e) =>
                setMobile(e.target.value.replace(/\D/g, "").slice(0, 10))
              }
              className="min-h-12 rounded-tile border-2 border-kerb-deep bg-board px-4 py-3 text-[17px] tabular-nums focus-ring"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label htmlFor="register-password" className="label text-gravel">
              {t("loginPassword")}
            </label>
            <input
              id="register-password"
              type="password"
              autoComplete="new-password"
              enterKeyHint="next"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="min-h-12 rounded-tile border-2 border-kerb-deep bg-board px-4 py-3 text-[17px] focus-ring"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label htmlFor="register-name" className="label text-gravel">
              {t("registerName")}
            </label>
            <input
              id="register-name"
              type="text"
              autoComplete="name"
              enterKeyHint="go"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="min-h-12 rounded-tile border-2 border-kerb-deep bg-board px-4 py-3 text-[17px] focus-ring"
            />
          </div>

          {error && (
            <p role="alert" className="text-[15px] text-kumkuma">
              {error}
            </p>
          )}

          <Button type="submit" block disabled={!valid || loading}>
            {t("registerSubmit")}
          </Button>
        </form>
        <p className="mt-4 text-[15px] text-gravel">
          <Link
            href="/login"
            className="font-semibold text-asphalt underline decoration-kerb-deep underline-offset-4 hover:decoration-asphalt focus-ring"
          >
            {t("toLogin")}
          </Link>
        </p>
      </main>
    </>
  );
}