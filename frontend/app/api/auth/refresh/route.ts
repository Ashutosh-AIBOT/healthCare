import { NextRequest } from "next/server";
import { accessCookie, cookieHeaderFromRequest, proxyToApi } from "@/lib/api";

type RefreshPayload = {
  access_token?: string;
  expires_in?: number;
};

export async function POST(req: NextRequest) {
  const cookie = cookieHeaderFromRequest(req);
  // Map BFF cookie path traffic → upstream expects aarogya_refresh on /api/v1/auth
  const upstream = await proxyToApi("/api/v1/auth/refresh", {
    method: "POST",
    body: "{}",
    cookie,
  });

  const text = await upstream.text();
  const headers = new Headers(upstream.headers);

  try {
    const json = JSON.parse(text) as RefreshPayload;
    if (upstream.ok && json.access_token) {
      headers.append("Set-Cookie", accessCookie(json.access_token, json.expires_in ?? 900));
    }
  } catch {
    /* ignore */
  }

  return new Response(text, { status: upstream.status, headers });
}
