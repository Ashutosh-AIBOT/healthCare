"use client";

const ACCESS_KEY = "aarogya_access";

export function setAccessToken(token: string | null) {
  if (typeof window === "undefined") return;
  if (!token) {
    sessionStorage.removeItem(ACCESS_KEY);
    return;
  }
  sessionStorage.setItem(ACCESS_KEY, token);
}

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return sessionStorage.getItem(ACCESS_KEY);
}

function normalizeDetail(detail: unknown): string {
  if (typeof detail === "string" && detail.trim()) return detail;
  if (Array.isArray(detail)) {
    // FastAPI 422: [{type, loc, msg, input, ctx}, ...] — never render raw
    const msgs = detail
      .map((d) =>
        typeof d === "object" && d !== null && "msg" in d ? String((d as { msg: unknown }).msg) : null,
      )
      .filter((m): m is string => !!m);
    if (msgs.length > 0) return msgs.join("; ");
    return "Invalid request. Please check your input.";
  }
  if (typeof detail === "object" && detail !== null) return "Request failed. Please try again.";
  return "Request failed";
}

export async function apiClient<T>(
  path: string,
  init: RequestInit = {},
): Promise<{ data?: T; error?: { detail?: string; status?: number; code?: string } }> {
  const headers = new Headers(init.headers);
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const token = getAccessToken();
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const res = await fetch(path, { ...init, headers, credentials: "include" });
  const text = await res.text();
  let json: unknown = null;
  try {
    json = text ? JSON.parse(text) : null;
  } catch {
    return { error: { detail: "Unexpected response.", status: res.status } };
  }
  if (!res.ok) {
    const err = (json as { detail?: unknown; code?: string }) || {};
    return { error: { detail: normalizeDetail(err.detail), status: res.status, code: err.code } };
  }
  return { data: json as T };
}
