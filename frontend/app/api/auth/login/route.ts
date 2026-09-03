import { NextRequest } from "next/server";
import { accessCookie, cookieHeaderFromRequest, proxyToApi } from "@/lib/api";

type AuthPayload = {
  tokens?: { access_token?: string; expires_in?: number } | null;
};

export async function POST(req: NextRequest) {
  const body = await req.text();
  const upstream = await proxyToApi("/api/v1/auth/login", {
    method: "POST",
    body,
    cookie: cookieHeaderFromRequest(req),
  });

  const text = await upstream.text();
  const headers = new Headers(upstream.headers);

  try {
    const json = JSON.parse(text) as AuthPayload;
    if (upstream.ok && json.tokens?.access_token) {
      headers.append(
        "Set-Cookie",
        accessCookie(json.tokens.access_token, json.tokens.expires_in ?? 900),
      );
    }
  } catch {
    /* leave body as-is */
  }

  return new Response(text, { status: upstream.status, headers });
}
