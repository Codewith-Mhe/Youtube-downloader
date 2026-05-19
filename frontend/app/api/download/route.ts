import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const BACKEND = process.env.BACKEND_URL || "http://127.0.0.1:8000";

export async function GET(req: NextRequest) {
  const token = req.nextUrl.searchParams.get("token");
  if (!token || token.length < 8 || token.length > 256) {
    return NextResponse.json(
      { success: false, message: "Missing or invalid download token." },
      { status: 400 },
    );
  }
  const forwardedFor =
    req.headers.get("x-forwarded-for") ||
    req.headers.get("x-real-ip") ||
    "";

  try {
    const upstream = await fetch(
      `${BACKEND}/api/download?token=${encodeURIComponent(token)}`,
      {
        method: "GET",
        headers: forwardedFor ? { "X-Forwarded-For": forwardedFor } : {},
        cache: "no-store",
      },
    );

    if (!upstream.ok || !upstream.body) {
      const text = await upstream.text().catch(() => "");
      try {
        const parsed = JSON.parse(text);
        return NextResponse.json(parsed, { status: upstream.status });
      } catch {
        return NextResponse.json(
          { success: false, message: "Download failed." },
          { status: upstream.status || 502 },
        );
      }
    }

    // Pass through the streaming body and select headers
    const headers = new Headers();
    const pass = ["content-type", "content-length", "content-disposition", "cache-control"];
    for (const h of pass) {
      const v = upstream.headers.get(h);
      if (v) headers.set(h, v);
    }
    headers.set("X-Content-Type-Options", "nosniff");

    return new NextResponse(upstream.body, { status: 200, headers });
  } catch {
    return NextResponse.json(
      { success: false, message: "Could not reach the extraction service." },
      { status: 502 },
    );
  }
}
