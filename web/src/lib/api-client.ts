import { ApiError } from "./api";
import type {
  CscResponse,
  DeepCheckResponse,
  MatchResponse,
  QuickMatchResponse,
} from "./types";

export { ApiError } from "./api";

const TIMEOUT_MS = 15000;

// Client-side data fetching: NEXT_PUBLIC_API_URL is inlined at build time.
export function browserApiBase(): string {
  const base = process.env.NEXT_PUBLIC_API_URL;
  if (!base) {
    throw new Error(
      "NEXT_PUBLIC_API_URL is not configured — set it in web/.env (dev) or via the Docker build arg; see .env.example.",
    );
  }
  return base;
}

export class BrowserApiError extends ApiError {
  data?: unknown;

  constructor(status: number, message: string, data?: unknown) {
    super(status, message);
    this.name = "BrowserApiError";
    this.data = data;
  }
}

type UnsafeMethod = "POST" | "PATCH";

export async function browserRequest<T>(
  path: string,
  init: { method?: "GET" | UnsafeMethod; body?: unknown } = {},
): Promise<T> {
  const method = init.method ?? "GET";
  const headers: Record<string, string> = {};
  if (init.body !== undefined) headers["Content-Type"] = "application/json";

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  let response: Response;
  try {
    response = await fetch(
      `${browserApiBase().replace(/\/$/, "")}${path}`,
      {
        method,
        headers: Object.keys(headers).length ? headers : undefined,
        body: init.body !== undefined ? JSON.stringify(init.body) : undefined,
        credentials: "include",
        signal: controller.signal,
        cache: "no-store",
      },
    );
  } catch (e) {
    throw new ApiError(
      0,
      e instanceof Error ? e.message : "network error",
    );
  } finally {
    clearTimeout(timer);
  }

  if (!response.ok) {
    let data: unknown;
    let detail = "";
    try {
      data = await response.json();
      detail = JSON.stringify(data);
    } catch {
      // non-JSON error body — keep the bare status
    }
    throw new BrowserApiError(
      response.status,
      `API ${response.status}: ${detail}`,
      data,
    );
  }
  return (await response.json()) as T;
}

export function postMatch(
  answers: Record<string, string | null>,
  locale: string,
): Promise<MatchResponse> {
  return browserRequest<MatchResponse>("/match", {
    method: "POST",
    body: { locale, answers },
  });
}

export function postQuickMatch(
  answers: Record<string, string | null>,
  locale: string,
): Promise<QuickMatchResponse> {
  return browserRequest<QuickMatchResponse>("/quick-match", {
    method: "POST",
    body: { locale, answers },
  });
}

export function postDeepCheck(
  schemeId: string,
  answers: Record<string, string | null>,
  locale: string,
): Promise<DeepCheckResponse> {
  return browserRequest<DeepCheckResponse>("/deep-check", {
    method: "POST",
    body: { locale, scheme_id: schemeId, answers },
  });
}

export function getCsc(
  pincode: string,
  locale: string,
  limit = 5,
): Promise<CscResponse> {
  const params = new URLSearchParams({
    pincode,
    locale,
    limit: String(limit),
  });
  return browserRequest<CscResponse>(`/csc?${params}`);
}