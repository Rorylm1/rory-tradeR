import { NextRequest, NextResponse } from "next/server";

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};

function unauthorized() {
  return new NextResponse("Authentication required.", {
    status: 401,
    headers: {
      "WWW-Authenticate": 'Basic realm="Rory TradeR Dashboard"',
    },
  });
}

export function middleware(request: NextRequest) {
  const authEnabled = process.env.DASHBOARD_BASIC_AUTH_ENABLED === "true";

  if (!authEnabled) {
    return NextResponse.next();
  }

  const expectedUser = process.env.DASHBOARD_BASIC_AUTH_USER;
  const expectedPassword = process.env.DASHBOARD_BASIC_AUTH_PASSWORD;

  if (!expectedUser || !expectedPassword) {
    return new NextResponse("Dashboard auth is not configured.", { status: 503 });
  }

  const header = request.headers.get("authorization");
  if (!header?.startsWith("Basic ")) {
    return unauthorized();
  }

  const decoded = atob(header.slice("Basic ".length));
  const separator = decoded.indexOf(":");
  const user = decoded.slice(0, separator);
  const password = decoded.slice(separator + 1);

  if (user !== expectedUser || password !== expectedPassword) {
    return unauthorized();
  }

  return NextResponse.next();
}
