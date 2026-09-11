import type { Meta, Question, SchemeRecord } from "./types";

const DEFAULT_BASE = "http://localhost:8000";
const TIMEOUT_MS = 15000;

export function serverApiBase(): string {
  return process.env.API_URL ?? DEFAULT_BASE;
}

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export async function requestJson<T>(
  base: string,
  path: string,
  init?: { method?: "GET" | "POST"; body?: unknown },
): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  let response: Response;
  try {
    response = await fetch(`${base.replace(/\/$/, "")}${path}`, {
      method: init?.method ?? "GET",
      headers:
        init?.body !== undefined
          ? { "Content-Type": "application/json" }
          : undefined,
      body: init?.body !== undefined ? JSON.stringify(init.body) : undefined,
      signal: controller.signal,
      cache: "no-store",
    });
  } catch (e) {
    throw new ApiError(
      0,
      e instanceof Error ? e.message : "network error",
    );
  } finally {
    clearTimeout(timer);
  }

  if (!response.ok) {
    let detail = "";
    try {
      const data: unknown = await response.json();
      detail = JSON.stringify(data);
    } catch {
      // non-JSON error body — keep the bare status
    }
    throw new ApiError(response.status, `API ${response.status}: ${detail}`);
  }
  return (await response.json()) as T;
}

export function getMeta(): Promise<Meta> {
  return requestJson<Meta>(serverApiBase(), "/meta");
}

export function getQuestions(
  locale: string,
  stage?: "quick" | "full" | "deep",
  schemeId?: string,
): Promise<Question[]> {
  const params = new URLSearchParams({ locale });
  if (stage) params.set("stage", stage);
  if (schemeId) params.set("scheme_id", schemeId);
  return requestJson<Question[]>(serverApiBase(), `/questions?${params}`);
}

export function getScheme(id: string, locale: string): Promise<SchemeRecord> {
  return requestJson<SchemeRecord>(
    serverApiBase(),
    `/schemes/${encodeURIComponent(id)}?locale=${encodeURIComponent(locale)}`,
  );
}
