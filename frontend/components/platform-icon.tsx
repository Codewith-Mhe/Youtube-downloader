import type { Platform } from "@/lib/types";

interface Props {
  platform: Platform;
  className?: string;
}

export function PlatformIcon({ platform, className = "h-5 w-5" }: Props) {
  switch (platform) {
    case "youtube":
      return (
        <svg viewBox="0 0 24 24" className={className} aria-hidden="true">
          <rect x="2" y="5" width="20" height="14" rx="3.5" fill="currentColor" opacity="0.18" />
          <path d="M10 9l5 3-5 3V9z" fill="currentColor" />
        </svg>
      );
    case "tiktok":
      return (
        <svg viewBox="0 0 24 24" className={className} aria-hidden="true">
          <path
            d="M14 3v9.2a2.8 2.8 0 11-2.8-2.8h.8V7a5.4 5.4 0 102 4.2V8.4a6.4 6.4 0 003.6 1.1V6.7A3.7 3.7 0 0114 3z"
            fill="currentColor"
          />
        </svg>
      );
    case "twitter":
      return (
        <svg viewBox="0 0 24 24" className={className} aria-hidden="true">
          <path
            d="M3 3h4.2l4.5 6.3L17.4 3H21l-7 8.1L21.5 21H17l-5-7-5.6 7H3l7.4-8.7L3 3z"
            fill="currentColor"
          />
        </svg>
      );
    case "facebook":
      return (
        <svg viewBox="0 0 24 24" className={className} aria-hidden="true">
          <path
            d="M14 8.5h2.5V5.5h-2.5c-2 0-3.5 1.5-3.5 3.5V11H8v3h2.5v7H14v-7h2.5l.5-3H14V9c0-.3.2-.5.5-.5h.5z"
            fill="currentColor"
          />
        </svg>
      );
    default:
      return null;
  }
}
