export type Platform = "youtube" | "tiktok" | "twitter" | "facebook";

export interface VideoFormat {
  formatId: string;
  quality: string;
  ext: string;
  size: string | null;
  hasAudio: boolean;
  hasVideo: boolean;
  note?: string | null;
  downloadUrl: string;
}

export interface FetchSuccess {
  success: true;
  platform: Platform;
  title: string;
  thumbnail?: string | null;
  duration?: string | null;
  uploader?: string | null;
  formats: VideoFormat[];
}

export interface FetchError {
  success: false;
  message: string;
}

export type FetchResult = FetchSuccess | FetchError;
