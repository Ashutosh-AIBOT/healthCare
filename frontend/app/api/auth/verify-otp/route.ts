import { NextRequest } from "next/server";
import { accessCookie, cookieHeaderFromRequest, proxyToApi } from "@/lib/api";

type VerifyPayload = {
  tokens?: { access_token?: string; expires_in?: number } | null;
};

export async function POST(req: NextRequest) {
  const raw = await req.text();
  let purpose: string | undefined;
  try {
    purpose = raw ? (JSON.parse(raw) as { purpose?: string }).purpose : undefined;
  } catch {
    purpose = undefined;
  }
  // Signup OTP completes registration: creates the verified account and
  // signs the user in (tokens + httpOnly refresh cookie forwarded below).
  if (purpose === "verify_email") {
    let email = "";
    let code = "";
    try {
      ({ email = "", code = "" } = JSON.parse(raw) as { email?: string; code?: string });
    } catch {
      // fall through with empty fields; backend validation will reject
    }
    const upstream = await proxyToApi("/api/v1/auth/verify-registration", {
      method: "POST",
      body: JSON.stringify({ email, code }),
      cookie: cookieHeaderFromRequest(req),
    });
    const text = await upstream.text();
    const headers = new Headers(upstream.headers);
    try {
      const json = JSON.parse(text) as VerifyPayload;
      if (upstream.ok && json.tokens?.access_token) {
        headers.append("Set-Cookie", accessCookie(json.tokens.access_token, json.tokens.expires_in ?? 900));
      }
    } catch {
      /* leave body as-is */
    }
    return new Response(text, { status: upstream.status, headers });
  }
  return proxyToApi("/api/v1/otp/verify", {
    method: "POST",
    body: raw,
    cookie: cookieHeaderFromRequest(req),
  });
}
