import { getSessionCookie } from "better-auth/cookies";
import { type NextRequest, NextResponse } from "next/server";

/**
 * Proxy for route protection (Next.js 16+)
 *
 * Replaces middleware.ts - runs on Node.js runtime.
 * Checks for session cookie and redirects to login if not present.
 * Note: This only checks cookie existence, not validity.
 * Full session validation happens in page/route handlers.
 */
export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Public paths that don't require authentication
  const publicPaths = [
    "/login",
    "/api/auth", // better-auth routes
    "/api/v1", // Backend API proxy (has its own auth)
    "/_next",
    "/favicon.ico",
  ];

  // Check if current path is public
  const isPublicPath = publicPaths.some((path) => pathname.startsWith(path));

  if (isPublicPath) {
    return NextResponse.next();
  }

  // Check for session cookie
  const sessionCookie = getSessionCookie(request);

  if (!sessionCookie) {
    // Redirect to login page with return URL
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("callbackUrl", pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  // Apply proxy to all routes except static files
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|.*\\.png$|.*\\.svg$).*)",
  ],
};
