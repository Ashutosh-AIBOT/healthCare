import { NextRequest } from "next/server";
import { clearAccessCookie, cookieHeaderFromRequest, proxyToApi } from "@/lib/api";

export async function POST(req: NextRequest) {
  const upstream = await proxyToApi("/api/v1/auth/logout", {
    method: "POST",
    body: "{}",
    cookie: cookieHeaderFromRequest(req),
  });

  const text = await upstream.text();
  const headers = new Headers(upstream.headers);
  headers.append("Set-Cookie", clearAccessCookie());
  // Also clear rewritten refresh cookie on BFF path
  const secure = process.env.NODE_ENV === "production" ? "; Secure" : "";
  headers.append(
    "Set-Cookie",
    `aarogya_refresh=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0${secure}`,
  );

  return new Response(text, { status: upstream.status, headers });
}
