"use client";

import { useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { AppHeader } from "@/components/AppHeader";
import { Button } from "@/components/Button";
import { useRouter } from "@/i18n/navigation";
import { logout, updateMe } from "@/lib/auth-client";
import type { Me } from "@/lib/types";
import { useUser } from "@/lib/user-context";

export default function ProfilePage() {
  const t = useTranslations("profile");
  const tAuth = useTranslations("auth");
  const router = useRouter();
  const { user, ready, setUser } = useUser();
  const [name, setName] = useState("");
  const [syncedUser, setSyncedUser] = useState<Me | null>(null);
  const [busy, setBusy] = useState<"save" | "logout" | null>(null);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const signingOutRef = useRef(false);

  useEffect(() => {
    if (ready && !user && !signingOutRef.current) {
      router.replace("/login");
    }
  }, [ready, user, router]);

  if (user !== syncedUser) {
    setSyncedUser(user);
    setName(user?.name ?? "");
  }

  const save = async () => {
    if (!user || busy) return;
    const next = name.trim();
    if (!next) return;
    setBusy("save");
    setSaved(false);
    setError(null);
    try {
      setUser(await updateMe({ name: next }));
      setSaved(true);
    } catch {
      setError(tAuth("authErrorGeneric"));
    } finally {
      setBusy(null);
    }
  };

  const signOut = async () => {
    if (busy) return;
    setBusy("logout");
    setError(null);
    signingOutRef.current = true;
    try {
      await logout();
    } catch {
    }
    setUser(null);
    router.push("/");
  };

  if (!user) {
    return (
      <>
        <AppHeader />
        <main className="mx-auto flex w-full max-w-xl flex-1 flex-col px-4 pb-10 pt-6 md:px-6 md:pt-8">
          <h1 className="title text-asphalt">{t("profileTitle")}</h1>
          <p className="mt-2 text-[15px] text-gravel">
            {t("profileLoading")}
          </p>
        </main>
      </>
    );
  }

  return (
    <>
      <AppHeader />
      <main className="mx-auto flex w-full max-w-xl flex-1 flex-col px-4 pb-10 pt-6 md:px-6 md:pt-8">
        <h1 className="title text-asphalt">{t("profileTitle")}</h1>
        <div className="board mt-6 flex flex-col gap-5 p-5">
          <div className="flex flex-col gap-1.5">
            <span id="profile-mobile-label" className="label text-gravel">
              {t("profileMobile")}
            </span>
            <p
              aria-labelledby="profile-mobile-label"
              className="text-[17px] tabular-nums text-asphalt"
            >
              {user.mobile}
            </p>
          </div>

          <div className="flex flex-col gap-1.5">
            <label htmlFor="profile-name" className="label text-gravel">
              {t("profileName")}
            </label>
            <input
              id="profile-name"
              type="text"
              autoComplete="name"
              value={name}
              onChange={(e) => {
                setName(e.target.value);
                setSaved(false);
              }}
              className="min-h-12 rounded-tile border-2 border-kerb-deep bg-board px-4 py-3 text-[17px] focus-ring"
            />
          </div>

          {error && (
            <p role="alert" className="text-[15px] text-kumkuma">
              {error}
            </p>
          )}
          {saved && !error && (
            <p role="status" className="text-[15px] text-gravel">
              {t("profileSaved")}
            </p>
          )}

          <div className="flex flex-wrap items-center gap-3">
            <Button
              onClick={() => void save()}
              disabled={busy !== null || !name.trim()}
            >
              {busy === "save" ? t("profileSaving") : t("profileSave")}
            </Button>
            <Button
              variant="secondary"
              onClick={() => void signOut()}
              disabled={busy !== null}
            >
              {t("profileLogout")}
            </Button>
          </div>
        </div>
      </main>
    </>
  );
}