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
import type { FetchSuccess, Platform, VideoFormat } from "@/lib/types";
import { PlatformIcon } from "./platform-icon";

type Status = "idle" | "loading" | "ready" | "error";

const PLATFORM_HINTS: Platform[] = ["youtube", "tiktok", "twitter", "facebook"];

export function FetcherPanel() {
  const [url, setUrl] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<FetchSuccess | null>(null);
  const [selectedFormat, setSelectedFormat] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const detected = useMemo(() => detectPlatform(url), [url]);
  const canSubmit = url.trim().length > 0 && status !== "loading";

  // Auto-select highest-quality "merged" format when results arrive
  useEffect(() => {
    if (data && data.formats.length > 0 && !selectedFormat) {
      const best =
        data.formats.find((f) => f.hasVideo && f.hasAudio) || data.formats[0];
      setSelectedFormat(best.formatId);
    }
  }, [data, selectedFormat]);

  async function handleSubmit(e?: React.FormEvent) {
    e?.preventDefault();
    const trimmed = url.trim();
    if (!trimmed) return;
    setStatus("loading");
    setError(null);
    setData(null);
    setSelectedFormat(null);

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
      // Clipboard permission denied — silently ignore
    }
  }

  function reset() {
    setUrl("");
    setStatus("idle");
    setError(null);
    setData(null);
    setSelectedFormat(null);
    inputRef.current?.focus();
  }

  return (
    <div className="w-full">
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
            placeholder="Paste a YouTube, TikTok, X, or Facebook link"
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
          <button
            type="submit"
            disabled={!canSubmit}
            className="btn-primary !px-5 !py-2.5"
          >
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
          <span className="hidden sm:block font-mono">
            ⌘V to paste
          </span>
        </div>
      </form>

      {/* Result area */}
      <AnimatePresence mode="wait">
        {status === "loading" && <LoadingState key="loading" />}
        {status === "error" && (
          <ErrorState key="error" message={error || ""} onDismiss={reset} />
        )}
        {status === "ready" && data && (
          <ResultCard
            key="ready"
            data={data}
            selected={selectedFormat}
            onSelect={setSelectedFormat}
            onReset={reset}
          />
        )}
      </AnimatePresence>

      {/* Hints when idle */}
      {status === "idle" && (
        <div className="mt-6 flex flex-wrap items-center justify-center gap-2 text-xs text-bone/40">
          <span className="mono-label !tracking-[0.2em] !text-bone/30">Supports</span>
          {PLATFORM_HINTS.map((p) => (
            <span
              key={p}
              className="inline-flex items-center gap-1.5 rounded-full border hairline px-3 py-1.5"
            >
              <PlatformIcon platform={p} className="h-3.5 w-3.5 text-bone/60" />
              <span className="text-bone/70">{PLATFORM_LABEL[p]}</span>
            </span>
          ))}
        </div>
      )}
    </div>
  );
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

function ErrorState({
  message,
  onDismiss,
}: {
  message: string;
  onDismiss: () => void;
}) {
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
}: {
  data: FetchSuccess;
  selected: string | null;
  onSelect: (id: string) => void;
  onReset: () => void;
}) {
  const chosen = data.formats.find((f) => f.formatId === selected) || null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
      className="card mt-8 overflow-hidden"
    >
      {/* Header */}
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
          {data.uploader && (
            <p className="mt-1 text-sm text-bone/50">by {data.uploader}</p>
          )}
        </div>
      </div>

      {/* Format picker */}
      <div className="border-t hairline p-5 sm:p-6">
        <div className="flex items-center justify-between">
          <h3 className="mono-label">Choose quality</h3>
          <button
            onClick={onReset}
            className="text-xs text-bone/40 hover:text-bone"
          >
            New link
          </button>
        </div>
        <div className="mt-4 grid gap-2 sm:grid-cols-2">
          {data.formats.map((f) => (
            <FormatRow
              key={f.formatId}
              format={f}
              selected={selected === f.formatId}
              onSelect={() => onSelect(f.formatId)}
            />
          ))}
        </div>
      </div>

      {/* CTA */}
      <div className="border-t hairline bg-ink-900/60 p-5 sm:p-6">
        <div className="flex flex-col-reverse items-stretch gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-xs text-bone/50">
            By downloading you confirm you have the right to do so.{" "}
            <a href="/terms" className="underline decoration-white/20 hover:text-bone">
              Terms
            </a>
            .
          </p>
          <a
            href={chosen ? chosen.downloadUrl : "#"}
            aria-disabled={!chosen}
            className={`btn-primary ${!chosen ? "pointer-events-none opacity-50" : ""}`}
            download
          >
            <Download className="h-4 w-4" />
            <span>
              Download {chosen?.quality ?? ""} {chosen ? `· ${chosen.ext.toUpperCase()}` : ""}
            </span>
          </a>
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

function FormatRow({
  format,
  selected,
  onSelect,
}: {
  format: VideoFormat;
  selected: boolean;
  onSelect: () => void;
}) {
  const isAudio = format.hasAudio && !format.hasVideo;
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
          <div className="flex items-baseline gap-2">
            <span className="font-medium tracking-tight">{format.quality}</span>
            <span className="font-mono text-[10px] uppercase text-bone/40">
              {format.ext}
            </span>
          </div>
          <div className="mt-0.5 flex items-center gap-1.5 text-xs text-bone/50">
            {format.size && <span>{format.size}</span>}
            {format.size && (format.hasAudio || !format.hasVideo) && (
              <span className="text-bone/20">·</span>
            )}
            {format.hasVideo && !format.hasAudio && (
              <span className="text-coral/80">video only</span>
            )}
            {isAudio && <span>audio only</span>}
            {format.hasVideo && format.hasAudio && <span>video + audio</span>}
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
