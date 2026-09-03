import { NextRequest } from "next/server";
import { cookieHeaderFromRequest, proxyToApi } from "@/lib/api";

export async function POST(req: NextRequest) {
  const body = await req.text();
  return proxyToApi("/api/v1/otp/send", {
    method: "POST",
    body,
    cookie: cookieHeaderFromRequest(req),
  });
}
