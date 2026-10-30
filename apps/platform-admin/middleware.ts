import { NextResponse, type NextRequest } from "next/server";

// Platform admin is served on its own domain (admin.<domain>), never indexed, never framed.
export function middleware(_request: NextRequest) {
  const response = NextResponse.next();
  const api = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  const oidc = process.env.NEXT_PUBLIC_OIDC_ISSUER ?? "";
  const oidcDomain = process.env.NEXT_PUBLIC_OIDC_DOMAIN ?? "";
  const dev = process.env.NODE_ENV !== "production";
  response.headers.set(
    "Content-Security-Policy",
    `default-src 'self'; script-src 'self' 'unsafe-inline'${dev ? " 'unsafe-eval'" : ""}; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self' ${api} ${oidc} ${oidcDomain} https://cognito-idp.ap-southeast-2.amazonaws.com; frame-ancestors 'none'; base-uri 'self'`,
  );
  response.headers.set("X-Frame-Options", "DENY");
  response.headers.set("X-Robots-Tag", "noindex, nofollow");
  response.headers.set("X-Content-Type-Options", "nosniff");
  response.headers.set("Referrer-Policy", "no-referrer");
  if (!dev) response.headers.set("Strict-Transport-Security", "max-age=63072000; includeSubDomains; preload");
  return response;
}

export const config = { matcher: ["/((?!_next/static|_next/image|favicon.ico|logo.svg).*)"] };
