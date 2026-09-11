import { browserRequest } from "./api-client";
import type { Me } from "./types";
export function register(mobile: string, password: string, name?: string) {
  return browserRequest<{ mobile: string; name: string }>("/auth/register", {
    method: "POST",
    body: name ? { mobile, password, name } : { mobile, password },
  });
}
export function login(mobile: string, password: string) {
  return browserRequest<Me>("/auth/login", {
    method: "POST",
    body: { mobile, password },
  });
}

export function logout() {
  return browserRequest<{ detail: string }>("/auth/logout", {
    method: "POST",
  });
}

export function getMe() {
  return browserRequest<Me>("/me");
}

export function updateMe(payload: {
  name?: string;
  answers?: Record<string, string | null>;
  deep_check_answers?: Record<string, string | null>;
}) {
  return browserRequest<Me>("/me", { method: "PATCH", body: payload });
}
