import { NextRequest } from "next/server";
import { cookieHeaderFromRequest, proxyToApi } from "@/lib/api";

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
    return proxyToApi("/api/v1/auth/verify-registration", {
      method: "POST",
      body: JSON.stringify({ email, code }),
      cookie: cookieHeaderFromRequest(req),
    });
  }
  return proxyToApi("/api/v1/otp/verify", {
    method: "POST",
    body: raw,
    cookie: cookieHeaderFromRequest(req),
  });
}
