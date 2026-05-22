export type Platform = "youtube" | "tiktok" | "twitter" | "facebook";

export type Tier = "best" | "1080p" | "720p" | "480p" | "360p" | "audio";

export interface QualityOption {
  id: Tier;
  label: string;
  downloadUrl: string;
}

export interface FetchSuccess {
  success: true;
  platform: Platform;
  title: string;
  thumbnail?: string | null;
  duration?: string | null;
  uploader?: string | null;
  qualities: QualityOption[];
}

export interface FetchError {
  success: false;
  message: string;
}

export type FetchResult = FetchSuccess | FetchError;
