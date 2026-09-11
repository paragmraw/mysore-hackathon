export const ANSWERS_KEY = "namma-mitra:answers";
export const RESULTS_KEY = "namma-mitra:results";
export const QUICK_KEY = "namma-mitra:quick";

export function readJson<T>(key: string): T | null {
  try {
    const raw = sessionStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : null;
  } catch {
    return null;
  }
}

export function writeJson(key: string, value: unknown): void {
  try {
    sessionStorage.setItem(key, JSON.stringify(value));
  } catch {
    // storage unavailable — the flow degrades (results live only in memory)
  }
}