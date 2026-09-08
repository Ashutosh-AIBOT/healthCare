import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const PROTECTED_PREFIXES = ["/app", "/doctor", "/lab", "/admin"];
const PUBLIC_AUTH = ["/login", "/register", "/verify", "/forgot-password", "/reset-password"];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const isProtected = PROTECTED_PREFIXES.some((p) => pathname === p || pathname.startsWith(`${p}/`));
  const isPublicAuth = PUBLIC_AUTH.some((p) => pathname === p || pathname.startsWith(`${p}/`));

  const access = request.cookies.get("aarogya_access");
  const refresh = request.cookies.get("aarogya_refresh");
  const isAuthed = Boolean(access || refresh);

  if (isProtected) {
    if (!isAuthed) {
      const url = request.nextUrl.clone();
      url.pathname = "/login";
      // Validate next is internal
      if (pathname.startsWith("/") && !pathname.startsWith("//")) {
        url.searchParams.set("next", pathname);
      }
      return NextResponse.redirect(url);
    }
    return NextResponse.next();
  }

  if (isPublicAuth && isAuthed) {
    const url = request.nextUrl.clone();
    const next = request.nextUrl.searchParams.get("next");
    // Only allow internal redirects
    if (next && next.startsWith("/") && !next.startsWith("//") && !next.startsWith("/login") && !next.startsWith("/register")) {
      url.pathname = next.split("?")[0];
      url.search = "";
    } else {
      url.pathname = "/app";
      url.search = "";
    }
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/app/:path*", "/doctor/:path*", "/lab/:path*", "/admin/:path*"],
};
