import { NextRequest, NextResponse } from "next/server";

type RouteContext = {
  params: Promise<{ path: string[] }>;
};

async function proxy(request: NextRequest, context: RouteContext) {
  const baseUrl = process.env.TRADER_BACKEND_URL;
  const token = process.env.TRADER_BACKEND_TOKEN;
  const authEnabled = process.env.DASHBOARD_BASIC_AUTH_ENABLED === "true";
  const publicReadOnly = !authEnabled || process.env.DASHBOARD_PUBLIC_READ_ONLY === "true";

  if (!baseUrl || !token) {
    return NextResponse.json({ error: "Backend connection is not configured." }, { status: 503 });
  }

  if (publicReadOnly && request.method !== "GET" && request.method !== "HEAD") {
    return NextResponse.json({ error: "Dashboard is public read-only." }, { status: 403 });
  }

  const { path } = await context.params;
  const target = `${baseUrl.replace(/\/$/, "")}/${path.join("/")}${request.nextUrl.search}`;
  const body = request.method === "GET" ? undefined : await request.text();

  const response = await fetch(target, {
    method: request.method,
    body,
    cache: "no-store",
    headers: {
      "X-Rory-Dashboard-Token": token,
      "Content-Type": request.headers.get("content-type") ?? "application/json",
    },
  });

  const text = await response.text();
  return new NextResponse(text, {
    status: response.status,
    headers: {
      "Content-Type": response.headers.get("content-type") ?? "application/json",
    },
  });
}

export async function GET(request: NextRequest, context: RouteContext) {
  return proxy(request, context);
}

export async function HEAD() {
  return new NextResponse(null, { status: 200 });
}

export async function POST(request: NextRequest, context: RouteContext) {
  return proxy(request, context);
}
