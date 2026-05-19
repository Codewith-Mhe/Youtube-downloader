import type { Platform } from "./types";

const PATTERNS: Array<{ re: RegExp; platform: Platform }> = [
  { re: /^(www\.|m\.|music\.)?youtube\.com$/i, platform: "youtube" },
  { re: /^youtu\.be$/i, platform: "youtube" },
  { re: /^(www\.|m\.|vm\.|vt\.)?tiktok\.com$/i, platform: "tiktok" },
  { re: /^(www\.|mobile\.)?(twitter|x)\.com$/i, platform: "twitter" },
  { re: /^(www\.|m\.|web\.)?facebook\.com$/i, platform: "facebook" },
  { re: /^fb\.watch$/i, platform: "facebook" },
];

export function detectPlatform(url: string): Platform | null {
  try {
    const parsed = new URL(url.trim());
    if (parsed.protocol !== "https:" && parsed.protocol !== "http:") return null;
    const host = parsed.hostname.toLowerCase();
    for (const { re, platform } of PATTERNS) {
      if (re.test(host)) return platform;
    }
    return null;
  } catch {
    return null;
  }
}

export const PLATFORM_LABEL: Record<Platform, string> = {
  youtube: "YouTube",
  tiktok: "TikTok",
  twitter: "X / Twitter",
  facebook: "Facebook",
};
