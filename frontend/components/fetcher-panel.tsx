"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  ArrowRight,
  Check,
  Clipboard,
  Download,
  Film,
  Music,
  TriangleAlert,
  X,
} from "lucide-react";
import { fetchVideo } from "@/lib/api";
import { detectPlatform, PLATFORM_LABEL } from "@/lib/platform";
import type { FetchSuccess, Platform, QualityOption } from "@/lib/types";
import { PlatformIcon } from "./platform-icon";

type Status = "idle" | "loading" | "ready" | "error";

const PLATFORM_HINTS: Platform[] = [ "tiktok", "twitter", "facebook"];

export function FetcherPanel() {
  const [url, setUrl] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<FetchSuccess | null>(null);
  const [selectedTier, setSelectedTier] = useState<string | null>(null);

  // Download state — separate from fetch state
  const [downloading, setDownloading] = useState(false);
  const [downloadProgress, setDownloadProgress] = useState<number | null>(null);
  const [downloadError, setDownloadError] = useState<string | null>(null);

  const inputRef = useRef<HTMLInputElement>(null);

  const detected = useMemo(() => detectPlatform(url), [url]);
  const canSubmit = url.trim().length > 0 && status !== "loading";

  // Default to "best" if available, else first option
  useEffect(() => {
    if (data && data.qualities.length > 0 && !selectedTier) {
      const best = data.qualities.find((q) => q.id === "best") || data.qualities[0];
      setSelectedTier(best.id);
    }
  }, [data, selectedTier]);

  async function handleSubmit(e?: React.FormEvent) {
    e?.preventDefault();
    const trimmed = url.trim();
    if (!trimmed) return;
    setStatus("loading");
    setError(null);
    setData(null);
    setSelectedTier(null);
    setDownloadError(null);

    const result = await fetchVideo(trimmed);
    if (result.success) {
      setData(result);
      setStatus("ready");
    } else {
      setError(result.message || "Something went wrong.");
      setStatus("error");
    }
  }

  async function pasteFromClipboard() {
    try {
      const text = await navigator.clipboard.readText();
      if (text) {
        setUrl(text.trim());
        inputRef.current?.focus();
      }
    } catch {
      /* permission denied — silently ignore */
    }
  }

  function reset() {
    setUrl("");
    setStatus("idle");
    setError(null);
    setData(null);
    setSelectedTier(null);
    setDownloadError(null);
    setDownloadProgress(null);
    inputRef.current?.focus();
  }

  /**
   * The download handler that fixes the `download.json` bug.
   *
   * We CANNOT use <a href download> here, because if the server returns a
   * JSON error (extraction failed, token expired, ffmpeg missing, etc.) the
   * browser would save it as `download.json` and show "Site wasn't available".
   *
   * Instead we:
   *   1. fetch() the URL ourselves.
   *   2. Check `response.ok` and `Content-Type`.
   *   3. If JSON or non-OK → parse the message and show it in the UI.
   *   4. If binary → read the streaming body with progress, build a Blob,
   *      and trigger a save via a temporary <a> with the real filename.
   */
  async function handleDownload() {
    const chosen = data?.qualities.find((q) => q.id === selectedTier);
    if (!chosen || !data) return;

    setDownloading(true);
    setDownloadError(null);
    setDownloadProgress(0);

    try {
      const response = await fetch(chosen.downloadUrl);
      const contentType = response.headers.get("content-type") || "";

      // Any JSON response is an error envelope — never a real download.
      if (!response.ok || contentType.includes("application/json")) {
        const text = await response.text();
        let message = `Download failed (HTTP ${response.status}).`;
        try {
          const parsed = JSON.parse(text);
          if (parsed?.message) message = parsed.message;
        } catch {
          /* not JSON, keep the generic message */
        }
        throw new Error(message);
      }

      // Pull a real filename out of Content-Disposition
      const cd = response.headers.get("content-disposition") || "";
      const filename = parseFilename(cd) || defaultFilename(data, chosen);

      const total = Number(response.headers.get("content-length") || 0);

      // Stream the body with progress so big videos don't look frozen
      if (!response.body) throw new Error("Streaming not supported in this browser.");
      const reader = response.body.getReader();
      const chunks: Uint8Array[] = [];
      let received = 0;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        if (value) {
          chunks.push(value);
          received += value.length;
          if (total > 0) {
            setDownloadProgress(Math.min(100, Math.round((received / total) * 100)));
          }
        }
      }

      const blob = new Blob(chunks as BlobPart[], { type: contentType });
      const blobUrl = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = blobUrl;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      // Give the browser a beat to start the save, then release memory
      setTimeout(() => URL.revokeObjectURL(blobUrl), 1_000);
    } catch (err) {
      setDownloadError(err instanceof Error ? err.message : "Download failed.");
    } finally {
      setDownloading(false);
      setDownloadProgress(null);
    }
  }

  return (
    <div className="w-full">
      {/* ─── URL input ─── */}
      <form onSubmit={handleSubmit} className="w-full">
        <div className="input-shell">
          <div className="pointer-events-none flex items-center pl-3 pr-1 text-bone/40">
            {detected ? (
              <span className="text-lime">
                <PlatformIcon platform={detected} className="h-4 w-4" />
              </span>
            ) : (
              <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={1.6}>
                <path d="M10 13a4 4 0 005.66 0l3.34-3.34a4 4 0 00-5.66-5.66L12 5.4" strokeLinecap="round" />
                <path d="M14 11a4 4 0 00-5.66 0l-3.34 3.34a4 4 0 005.66 5.66L12 18.6" strokeLinecap="round" />
              </svg>
            )}
          </div>

          <input
            ref={inputRef}
            type="url"
            inputMode="url"
            autoComplete="off"
            autoCorrect="off"
            spellCheck={false}
            placeholder="Paste TikTok, X, or Facebook link"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            className="flex-1 min-w-0 bg-transparent text-base sm:text-lg text-bone placeholder:text-bone/30 outline-none px-1 py-2"
          />
          <button
            type="button"
            onClick={pasteFromClipboard}
            className="hidden sm:inline-flex items-center justify-center px-3 text-bone/50 hover:text-bone transition-colors"
            aria-label="Paste from clipboard"
          >
            <Clipboard className="h-4 w-4" />
          </button>
          <button type="submit" disabled={!canSubmit} className="btn-primary !px-5 !py-2.5">
            {status === "loading" ? (
              <>
                <Spinner />
                <span className="hidden sm:inline">Fetching</span>
              </>
            ) : (
              <>
                <span>Fetch</span>
                <ArrowRight className="h-4 w-4" />
              </>
            )}
          </button>
        </div>

        <div className="mt-3 flex items-center justify-between px-1 text-xs text-bone/40">
          <span className="font-mono">
            {detected
              ? <>detected · <span className="text-lime">{PLATFORM_LABEL[detected]}</span></>
              : <>no link detected</>}
          </span>
          <span className="hidden sm:block font-mono">⌘V to paste</span>
        </div>
      </form>

      {/* ─── Result area ─── */}
      <AnimatePresence mode="wait">
        {status === "loading" && <LoadingState key="loading" />}
        {status === "error" && (
          <ErrorState key="error" message={error || ""} onDismiss={reset} />
        )}
        {status === "ready" && data && (
          <ResultCard
            key="ready"
            data={data}
            selected={selectedTier}
            onSelect={setSelectedTier}
            onReset={reset}
            onDownload={handleDownload}
            downloading={downloading}
            progress={downloadProgress}
            downloadError={downloadError}
          />
        )}
      </AnimatePresence>

      {/* ─── Idle hints ─── */}
      {status === "idle" && (
  <div className="mt-6 flex flex-wrap items-center justify-center gap-2 text-xs text-bone/40">
    <span className="mono-label !tracking-[0.2em] !text-bone/30">Supports</span>
    {PLATFORM_HINTS.map((p) => (
      <span key={p} className="inline-flex items-center gap-1.5 rounded-full border hairline px-3 py-1.5">
        <PlatformIcon platform={p} className="h-3.5 w-3.5 text-bone/60" />
        <span className="text-bone/70">{PLATFORM_LABEL[p]}</span>
      </span>
    ))}
    {/* YouTube Coming Soon */}
<span className="inline-flex items-center gap-1.5 rounded-full border border-red-500/30 px-3 py-1.5">
  <PlatformIcon platform="youtube" className="h-3.5 w-3.5 text-red-400" />
  <span className="text-red-400 font-semibold">YouTube</span>
  <span className="text-[10px] bg-red-500 text-white px-1.5 py-0.5 rounded-full font-black uppercase tracking-wider">soon</span>
</span>
  </div>
)}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────
function parseFilename(contentDisposition: string): string | null {
  // Prefer the RFC 5987 UTF-8 form
  const utf = /filename\*=UTF-8''([^;]+)/i.exec(contentDisposition);
  if (utf) {
    try {
      return decodeURIComponent(utf[1]);
    } catch {
      /* fall through */
    }
  }
  const ascii = /filename="?([^";]+)"?/i.exec(contentDisposition);
  return ascii ? ascii[1] : null;
}

function defaultFilename(data: FetchSuccess, q: QualityOption): string {
  const safe = (data.title || "video")
    .replace(/[^\w\s.-]/g, "")
    .trim()
    .slice(0, 60) || "video";
  const ext = q.id === "audio" ? "m4a" : "mp4";
  return `${safe}.${ext}`;
}

function Spinner() {
  return (
    <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="2.5" opacity="0.25" />
      <path d="M21 12a9 9 0 00-9-9" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
    </svg>
  );
}

function LoadingState() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.25 }}
      className="card mt-8 p-6 sm:p-8"
    >
      <div className="flex items-center gap-4">
        <div className="h-16 w-28 sm:h-20 sm:w-36 rounded-xl bg-gradient-to-r from-ink-700 via-ink-600 to-ink-700 bg-[length:200%_100%] animate-shimmer" />
        <div className="flex-1 space-y-3">
          <div className="h-4 w-3/4 rounded bg-gradient-to-r from-ink-700 via-ink-600 to-ink-700 bg-[length:200%_100%] animate-shimmer" />
          <div className="h-3 w-1/2 rounded bg-gradient-to-r from-ink-700 via-ink-600 to-ink-700 bg-[length:200%_100%] animate-shimmer" />
        </div>
      </div>
      <p className="mt-6 mono-label flex items-center gap-2">
        <span className="h-1.5 w-1.5 rounded-full bg-lime animate-pulse-soft" />
        reading metadata from upstream
      </p>
    </motion.div>
  );
}

function ErrorState({ message, onDismiss }: { message: string; onDismiss: () => void }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      className="card mt-8 border-coral/30 bg-coral/[0.04] p-5 sm:p-6"
    >
      <div className="flex items-start gap-3">
        <div className="mt-0.5 flex h-8 w-8 flex-none items-center justify-center rounded-full bg-coral/15 text-coral">
          <TriangleAlert className="h-4 w-4" />
        </div>
        <div className="flex-1">
          <h3 className="font-display text-xl tracking-tightest">Couldn&apos;t fetch that link</h3>
          <p className="mt-1 text-sm text-bone/70">{message}</p>
        </div>
        <button
          onClick={onDismiss}
          className="rounded-full p-1.5 text-bone/40 hover:bg-white/5 hover:text-bone"
          aria-label="Dismiss"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    </motion.div>
  );
}

function ResultCard({
  data,
  selected,
  onSelect,
  onReset,
  onDownload,
  downloading,
  progress,
  downloadError,
}: {
  data: FetchSuccess;
  selected: string | null;
  onSelect: (id: string) => void;
  onReset: () => void;
  onDownload: () => void;
  downloading: boolean;
  progress: number | null;
  downloadError: string | null;
}) {
  const chosen = data.qualities.find((q) => q.id === selected) || null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
      className="card mt-8 overflow-hidden"
    >
      <div className="grid gap-5 p-5 sm:grid-cols-[auto_1fr] sm:p-6">
        <Thumbnail src={data.thumbnail} platform={data.platform} duration={data.duration} />
        <div className="min-w-0">
          <div className="mono-label flex items-center gap-1.5 text-lime">
            <PlatformIcon platform={data.platform} className="h-3.5 w-3.5" />
            <span>{PLATFORM_LABEL[data.platform]}</span>
          </div>
          <h2 className="mt-2 font-display text-2xl tracking-tightest leading-tight sm:text-3xl">
            {data.title}
          </h2>
          {data.uploader && <p className="mt-1 text-sm text-bone/50">by {data.uploader}</p>}
        </div>
      </div>

      <div className="border-t hairline p-5 sm:p-6">
        <div className="flex items-center justify-between">
          <h3 className="mono-label">Choose quality</h3>
          <button onClick={onReset} className="text-xs text-bone/40 hover:text-bone">
            New link
          </button>
        </div>
        <div className="mt-4 grid gap-2 sm:grid-cols-2">
          {data.qualities.map((q) => (
            <QualityRow
              key={q.id}
              option={q}
              selected={selected === q.id}
              onSelect={() => onSelect(q.id)}
            />
          ))}
        </div>
      </div>

      {downloadError && (
        <div className="border-t border-coral/20 bg-coral/[0.04] px-5 py-3 sm:px-6">
          <p className="flex items-center gap-2 text-sm text-coral">
            <TriangleAlert className="h-4 w-4 flex-none" />
            {downloadError}
          </p>
        </div>
      )}

      <div className="border-t hairline bg-ink-900/60 p-5 sm:p-6">
        <div className="flex flex-col-reverse items-stretch gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-xs text-bone/50">
            By downloading you confirm you have the right to do so.{" "}
            <a href="/terms" className="underline decoration-white/20 hover:text-bone">
              Terms
            </a>
            .
          </p>
          <button
            type="button"
            onClick={onDownload}
            disabled={!chosen || downloading}
            className="btn-primary"
          >
            {downloading ? (
              <>
                <Spinner />
                <span>
                  {progress !== null ? `Downloading… ${progress}%` : "Preparing…"}
                </span>
              </>
            ) : (
              <>
                <Download className="h-4 w-4" />
                <span>Download {chosen?.label ?? ""}</span>
              </>
            )}
          </button>
        </div>
      </div>
    </motion.div>
  );
}

function Thumbnail({
  src,
  platform,
  duration,
}: {
  src?: string | null;
  platform: Platform;
  duration?: string | null;
}) {
  return (
    <div className="relative h-32 w-full overflow-hidden rounded-2xl bg-ink-700 sm:h-28 sm:w-48">
      {src ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={src}
          alt=""
          className="h-full w-full object-cover"
          loading="lazy"
          referrerPolicy="no-referrer"
        />
      ) : (
        <div className="flex h-full w-full items-center justify-center text-bone/30">
          <PlatformIcon platform={platform} className="h-8 w-8" />
        </div>
      )}
      {duration && (
        <span className="absolute bottom-2 right-2 rounded-md bg-black/70 px-1.5 py-0.5 font-mono text-[10px] text-bone">
          {duration}
        </span>
      )}
    </div>
  );
}

function QualityRow({
  option,
  selected,
  onSelect,
}: {
  option: QualityOption;
  selected: boolean;
  onSelect: () => void;
}) {
  const isAudio = option.id === "audio";
  const Icon = isAudio ? Music : Film;
  return (
    <button
      type="button"
      onClick={onSelect}
      className={`group relative flex items-center justify-between gap-3 rounded-2xl border px-4 py-3 text-left transition-all ${
        selected
          ? "border-lime/60 bg-lime/[0.06] shadow-[0_0_0_3px_rgba(200,242,92,0.10)]"
          : "border-white/[0.08] bg-ink-800/40 hover:border-white/20 hover:bg-ink-800/80"
      }`}
    >
      <div className="flex items-center gap-3">
        <div
          className={`flex h-9 w-9 flex-none items-center justify-center rounded-xl ${
            selected ? "bg-lime text-ink-950" : "bg-ink-700 text-bone/60"
          }`}
        >
          <Icon className="h-4 w-4" />
        </div>
        <div className="min-w-0">
          <div className="font-medium tracking-tight">{option.label}</div>
          <div className="mt-0.5 text-xs text-bone/50">
            {isAudio ? "M4A audio" : "MP4 · video + audio"}
            {/* ← NEW: show file size if available */}
            {option.filesize ? (
              <span className="ml-2 text-bone/40">{option.filesize}</span>
            ) : null}
          </div>
        </div>
      </div>
      {selected && (
        <span className="flex h-6 w-6 flex-none items-center justify-center rounded-full bg-lime text-ink-950">
          <Check className="h-3.5 w-3.5" />
        </span>
      )}
    </button>
  );
}
