import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

const protectedRoutes = ['/inbox', '/settings', '/dashboard'];

export async function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Redirect root to inbox
  if (pathname === '/') {
    return NextResponse.redirect(new URL('/inbox', request.url));
  }

  // Stack Auth handler routes — always allow
  if (pathname.startsWith('/handler')) {
    return NextResponse.next();
  }

  // WhatsApp webhook — public, no auth required
  if (pathname.startsWith('/api/whatsapp/webhook')) {
    return NextResponse.next();
  }

  // Stripe webhook — public, no auth required
  if (pathname.startsWith('/api/stripe/webhook')) {
    return NextResponse.next();
  }

  const isProtectedRoute = protectedRoutes.some((r) =>
    pathname.startsWith(r)
  );

  // Stack Auth sets a cookie named "__stack-token" (or similar) — check for it
  // If no Stack Auth session cookie, redirect to sign-in
  const stackToken =
    request.cookies.get('__stack-token')?.value ||
    request.cookies.get('stack-token')?.value;

  if (isProtectedRoute && !stackToken) {
    return NextResponse.redirect(new URL('/handler/sign-in', request.url));
  }

  return NextResponse.next();
}

export { proxy as default };

export const config = {
  matcher: [
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
  ],
};
