import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const BACKEND = process.env.BACKEND_URL || "http://127.0.0.1:8000";

export async function POST(req: NextRequest) {
  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json(
      { success: false, message: "Invalid request body." },
      { status: 400 },
    );
  }

  const forwardedFor =
    req.headers.get("x-forwarded-for") ||
    req.headers.get("x-real-ip") ||
    "";

  try {
    const r = await fetch(`${BACKEND}/api/fetch`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(forwardedFor ? { "X-Forwarded-For": forwardedFor } : {}),
      },
      body: JSON.stringify(body),
      // Reasonable client-side timeout
      signal: AbortSignal.timeout(30_000),
      cache: "no-store",
    });
    const text = await r.text();
    return new NextResponse(text, {
      status: r.status,
      headers: { "Content-Type": "application/json" },
    });
  } catch (err) {
    const isAbort = err instanceof Error && err.name === "TimeoutError";
    return NextResponse.json(
      {
        success: false,
        message: isAbort
          ? "Request timed out. Please try again."
          : "Could not reach the extraction service.",
      },
      { status: isAbort ? 504 : 502 },
    );
  }
}
