import { NextRequest } from "next/server";
import { cookieHeaderFromRequest, proxyToApi } from "@/lib/api";

type Ctx = { params: Promise<{ path: string[] }> };

async function forward(req: NextRequest, pathParts: string[], method: string) {
  const path = `/api/v1/${pathParts.join("/")}`;
  const access = req.cookies.get("aarogya_access")?.value;
  const headers: HeadersInit = {};
  if (access) headers.Authorization = `Bearer ${access}`;
  // Prefer client Authorization if present (sessionStorage token)
  const clientAuth = req.headers.get("authorization");
  if (clientAuth) headers.Authorization = clientAuth;

  const hasBody = method !== "GET" && method !== "HEAD";
  const body = hasBody ? await req.text() : undefined;
  const qs = req.nextUrl.search || "";

  return proxyToApi(`${path}${qs}`, {
    method,
    body,
    headers,
    cookie: cookieHeaderFromRequest(req),
  });
}

export async function GET(req: NextRequest, ctx: Ctx) {
  const { path } = await ctx.params;
  return forward(req, path, "GET");
}

export async function POST(req: NextRequest, ctx: Ctx) {
  const { path } = await ctx.params;
  return forward(req, path, "POST");
}

export async function PUT(req: NextRequest, ctx: Ctx) {
  const { path } = await ctx.params;
  return forward(req, path, "PUT");
}

export async function PATCH(req: NextRequest, ctx: Ctx) {
  const { path } = await ctx.params;
  return forward(req, path, "PATCH");
}

export async function DELETE(req: NextRequest, ctx: Ctx) {
  const { path } = await ctx.params;
  return forward(req, path, "DELETE");
}
