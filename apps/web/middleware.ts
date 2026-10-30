import { NextResponse, type NextRequest } from "next/server";

// Security headers for every page. Auth happens client-side (OIDC tokens never touch the Next server) and
// again in the API, so the middleware only hardens responses.
export function middleware(request: NextRequest) {
  const response = NextResponse.next();
  const api = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  const ws = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000";
  const oidc = process.env.NEXT_PUBLIC_OIDC_ISSUER ?? "";
  const oidcDomain = process.env.NEXT_PUBLIC_OIDC_DOMAIN ?? "";
  const dev = process.env.NODE_ENV !== "production";
  response.headers.set(
    "Content-Security-Policy",
    [
      "default-src 'self'",
      `script-src 'self' 'unsafe-inline'${dev ? " 'unsafe-eval'" : ""}`,
      "style-src 'self' 'unsafe-inline'",
      "img-src 'self' data: blob:",
      `connect-src 'self' ${api} ${ws} ${oidc} ${oidcDomain} https://cognito-idp.ap-southeast-2.amazonaws.com`,
      "frame-ancestors 'none'",
      "base-uri 'self'",
      "form-action 'self'",
    ].join("; "),
  );
  response.headers.set("X-Frame-Options", "DENY");
  response.headers.set("X-Content-Type-Options", "nosniff");
  response.headers.set("Referrer-Policy", "strict-origin-when-cross-origin");
  response.headers.set("Permissions-Policy", "camera=(), microphone=(), geolocation=()");
  if (!dev) response.headers.set("Strict-Transport-Security", "max-age=63072000; includeSubDomains; preload");
  return response;
}

export const config = { matcher: ["/((?!_next/static|_next/image|favicon.ico|logo.svg).*)"] };
