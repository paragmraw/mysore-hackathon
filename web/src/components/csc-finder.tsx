"use client";

import { useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { Button } from "@/components/Button";
import { ApiError, getCsc } from "@/lib/api-client";
import { pickText } from "@/lib/localize";
import type { CscResponse } from "@/lib/types";

type FindState =
  | { phase: "idle" }
  | { phase: "loading" }
  | { phase: "done"; resp: CscResponse }
  | { phase: "error"; kind: "notKarnataka" | "noCoverage" | "network" };

export function CscFinder({
  initialPincode = "",
  limit = 5,
}: {
  initialPincode?: string;
  limit?: number;
}) {
  const t = useTranslations("csc");
  const locale = useLocale();
  const [pin, setPin] = useState(initialPincode);
  const [state, setState] = useState<FindState>({ phase: "idle" });

  const valid = /^\d{6}$/.test(pin);

  const find = async () => {
    if (!valid || state.phase === "loading") return;
    setState({ phase: "loading" });
    try {
      const resp = await getCsc(pin, locale, limit);
      if (!resp.centers.length) {
        setState({ phase: "error", kind: "noCoverage" });
      } else {
        setState({ phase: "done", resp });
      }
    } catch (e) {
      setState({
        phase: "error",
        kind:
          e instanceof ApiError && e.status === 422
            ? "notKarnataka"
            : "network",
      });
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-3">
        <input
          type="text"
          inputMode="numeric"
          autoComplete="postal-code"
          enterKeyHint="go"
          value={pin}
          onChange={(e) => setPin(e.target.value.replace(/\D/g, "").slice(0, 6))}
          onKeyDown={(e) => {
            if (e.key === "Enter") void find();
          }}
          placeholder={t("enterPincode")}
          aria-label={t("enterPincode")}
          className="min-h-12 w-44 max-w-full rounded-tile border-2 border-kerb-deep bg-board px-4 py-3 text-[17px] tabular-nums focus-ring"
        />
        <Button
          onClick={() => void find()}
          disabled={!valid || state.phase === "loading"}
        >
          {t("findButton")}
        </Button>
      </div>

      {state.phase === "error" && (
        <p role="alert" className="text-[15px] text-kumkuma">
          {state.kind === "noCoverage"
            ? t("noCoverage")
            : state.kind === "notKarnataka"
              ? t("notKarnataka")
              : t("error")}
        </p>
      )}

      {state.phase === "done" && (
        <div className="flex flex-col gap-3">
          {state.resp.match === "district_fallback" && (
            <p className="text-[13px] leading-[1.5] text-gravel">
              {t("fallbackNote")}
            </p>
          )}
          <p className="label tabular-nums text-gravel">
            {t("centersFound", { count: state.resp.centers.length })}
          </p>
          <div className="board">
            {state.resp.centers.map((center, i) => (
              <div
                key={center.id}
                className={`px-4 py-3${i > 0 ? " border-t border-kerb" : ""}`}
              >
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <span className="font-display text-[16px] font-bold text-asphalt">
                    {pickText(center.name, locale)}
                  </span>
                  {typeof center.distance_km === "number" && (
                    <span className="pill bg-arishina text-asphalt tabular-nums">
                      {t("distanceKm", { km: center.distance_km })}
                    </span>
                  )}
                </div>
                <p className="mt-1 text-[15px] text-gravel">
                  {pickText(center.address, locale)}
                </p>
                {center.phone && (
                  <p className="mt-1 text-[15px] text-gravel tabular-nums">
                    {center.phone}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}