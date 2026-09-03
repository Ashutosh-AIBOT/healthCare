import type { NextRequest } from "next/server";

const API_BASE = process.env.API_INTERNAL_URL || "http://localhost:8000";

/** Rewrite FastAPI refresh cookie so browsers send it on all routes (for middleware + BFF). */
export function rewriteUpstreamCookies(setCookieHeaders: string[]): string[] {
  return setCookieHeaders.map((cookie) =>
    cookie
      // Path=/ so /app middleware can see refresh; value stays httpOnly.
      .replace(/Path=\/api\/v1\/auth/gi, "Path=/")
      .replace(/Domain=[^;]+;?\s*/gi, ""),
  );
}

export function collectSetCookies(headers: Headers): string[] {
  const anyHeaders = headers as Headers & { getSetCookie?: () => string[] };
  if (typeof anyHeaders.getSetCookie === "function") {
    return anyHeaders.getSetCookie();
  }
  const single = headers.get("set-cookie");
  return single ? [single] : [];
}

export async function proxyToApi(
  path: string,
  init: RequestInit & { cookie?: string } = {},
): Promise<Response> {
  const headers = new Headers(init.headers);
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (init.cookie) headers.set("Cookie", init.cookie);

  const upstream = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
    cache: "no-store",
  });

  const body = await upstream.text();
  const out = new Headers();
  const ct = upstream.headers.get("content-type");
  if (ct) out.set("content-type", ct);

  for (const c of rewriteUpstreamCookies(collectSetCookies(upstream.headers))) {
    out.append("Set-Cookie", c);
  }

  return new Response(body, { status: upstream.status, headers: out });
}

export function cookieHeaderFromRequest(req: NextRequest): string {
  return req.headers.get("cookie") || "";
}

export type ApiProblem = {
  code?: string;
  detail?: string;
  title?: string;
  status?: number;
  message?: string;
};

export async function parseApiJson<T>(res: Response): Promise<{ data?: T; error?: ApiProblem }> {
  const text = await res.text();
  let json: unknown = null;
  try {
    json = text ? JSON.parse(text) : null;
  } catch {
    return { error: { detail: "Unexpected response from server.", status: res.status } };
  }
  if (!res.ok) {
    const problem = (json as ApiProblem) || {};
    return {
      error: {
        ...problem,
        detail: problem.detail || problem.message || "Request failed",
        status: res.status,
      },
    };
  }
  return { data: json as T };
}

export function accessCookie(value: string, maxAge = 900): string {
  const secure = process.env.NODE_ENV === "production" ? "; Secure" : "";
  return `aarogya_access=${value}; Path=/; HttpOnly; SameSite=Lax; Max-Age=${maxAge}${secure}`;
}

export function clearAccessCookie(): string {
  const secure = process.env.NODE_ENV === "production" ? "; Secure" : "";
  return `aarogya_access=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0${secure}`;
}
