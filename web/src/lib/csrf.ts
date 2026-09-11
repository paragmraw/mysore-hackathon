const DEFAULT_BASE = "http://localhost:8000";
function browserApiBase(): string {
  return process.env.NEXT_PUBLIC_API_URL ?? DEFAULT_BASE;
}
export function readCsrfToken(): string | null {
  if (typeof document === "undefined") return null;
  try {
    const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]*)/);
    return match ? decodeURIComponent(match[1]) : null;
  } catch {
    return null;
  }
}

let csrfPromise: Promise<string | null> | null = null;

export function ensureCsrf(): Promise<string | null> {
  const existing = readCsrfToken();
  if (existing) return Promise.resolve(existing);

  if (!csrfPromise) {
    csrfPromise = (async () => {
      try {
        await fetch(`${browserApiBase().replace(/\/$/, "")}/auth/csrf`, {
          method: "GET",
          credentials: "include",
          cache: "no-store",
        });
      } catch {
        // network failure — fall through and report "no token"
      }
      const token = readCsrfToken();
      if (!token) {
        csrfPromise = null;
      }
      return token;
    })();
  }
  return csrfPromise;
}