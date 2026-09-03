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
    const err = (json as { detail?: string; code?: string }) || {};
    return { error: { detail: err.detail || "Request failed", status: res.status, code: err.code } };
  }
  return { data: json as T };
}
