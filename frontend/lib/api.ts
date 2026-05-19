import type { FetchResult } from "./types";

/** Calls the local Next.js API route, which proxies to the FastAPI backend. */
export async function fetchVideo(url: string): Promise<FetchResult> {
  const res = await fetch("/api/fetch", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });
  let json: FetchResult;
  try {
    json = (await res.json()) as FetchResult;
  } catch {
    return { success: false, message: "The server returned an invalid response." };
  }
  return json;
}
