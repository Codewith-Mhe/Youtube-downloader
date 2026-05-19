import { Clipboard, Download, MousePointerClick, ShieldCheck } from "lucide-react";
import { FetcherPanel } from "@/components/fetcher-panel";
import { PlatformIcon } from "@/components/platform-icon";
import type { Platform } from "@/lib/types";

const PLATFORMS: { id: Platform; name: string; example: string }[] = [
  { id: "youtube", name: "YouTube", example: "youtu.be/dQw4w9WgXcQ" },
  { id: "tiktok", name: "TikTok", example: "tiktok.com/@user/video/…" },
  { id: "twitter", name: "X / Twitter", example: "x.com/user/status/…" },
  { id: "facebook", name: "Facebook", example: "fb.watch/…" },
];

const STEPS = [
  { icon: Clipboard, title: "Paste the link", body: "Copy a video URL from your favorite app and drop it in the box." },
  { icon: MousePointerClick, title: "Pick a quality", body: "We list every available format with file size and codec." },
  { icon: Download, title: "Download", body: "The file streams straight to your device. Nothing is stored on our servers." },
];

const FAQS = [
  {
    q: "Is ClipFetch free to use?",
    a: "Yes. There is no signup, no paywall, and no premium tier. The project is funded by goodwill and minimal operating costs.",
  },
  {
    q: "Do you store the videos I download?",
    a: "No. We stream the file directly from the source platform to your device. Nothing is written to permanent storage and download links expire automatically.",
  },
  {
    q: "Why can't I download some videos?",
    a: "Private, age-restricted, members-only, geo-restricted, and removed videos cannot be fetched because the underlying platforms gate access. The error message will tell you which case applies.",
  },
  {
    q: "Will this work on my phone?",
    a: "Yes. The interface is mobile-first. On iOS, large downloads land in the Files app or your browser's Downloads section.",
  },
  {
    q: "Why are some formats marked 'video only'?",
    a: "Platforms like YouTube serve high-resolution video and audio as separate streams. For the smoothest download, pick a format that says 'video + audio'.",
  },
];

export default function HomePage() {
  return (
    <>
      {/* ─── HERO ─── */}
      <section className="relative mx-auto max-w-6xl px-5 pt-12 sm:px-8 sm:pt-20">
        <div className="mx-auto max-w-4xl text-center">
          <span className="mono-label inline-flex items-center gap-2 rounded-full border hairline bg-ink-900/60 px-3 py-1.5 backdrop-blur">
            <span className="h-1.5 w-1.5 rounded-full bg-lime animate-pulse-soft" />
            no signup · no ads · no tracking
          </span>

          <h1 className="mt-7 font-display text-[2.6rem] leading-[1.02] tracking-tightest sm:text-6xl md:text-7xl">
            Download videos from
            <br className="hidden sm:block" />{" "}
            <span className="text-bone/85">YouTube, TikTok, X, and</span>{" "}
            <span className="italic text-lime">Facebook</span>{" "}
            <span className="text-bone/85">in</span>{" "}
            <span className="italic text-lime">seconds</span>.
          </h1>

          <p className="mx-auto mt-5 max-w-xl text-base text-bone/55 sm:text-lg">
            Paste your video link, choose your quality, and download instantly. That&apos;s
            the whole product.
          </p>
        </div>

        {/* Fetcher panel sits in the hero so it's the first interaction */}
        <div className="mx-auto mt-10 max-w-2xl">
          <FetcherPanel />
        </div>
      </section>

      {/* ─── SUPPORTED PLATFORMS ─── */}
      <section className="mx-auto mt-24 max-w-6xl px-5 sm:px-8">
        <div className="mb-8 flex items-end justify-between">
          <div>
            <span className="mono-label">/ 01 — coverage</span>
            <h2 className="mt-2 font-display text-3xl tracking-tightest sm:text-4xl">
              Four platforms. <span className="italic text-lime">One box.</span>
            </h2>
          </div>
        </div>

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {PLATFORMS.map((p) => (
            <div
              key={p.id}
              className="group relative overflow-hidden rounded-3xl border hairline bg-ink-900/60 p-5 backdrop-blur transition-colors hover:border-white/20"
            >
              <div className="flex items-center gap-3">
                <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-ink-700 text-lime">
                  <PlatformIcon platform={p.id} className="h-5 w-5" />
                </span>
                <h3 className="font-display text-xl tracking-tightest">{p.name}</h3>
              </div>
              <p className="mt-4 font-mono text-xs text-bone/40">{p.example}</p>
              <div
                className="pointer-events-none absolute -bottom-12 -right-12 h-28 w-28 rounded-full bg-lime/10 blur-2xl transition-opacity opacity-0 group-hover:opacity-100"
                aria-hidden
              />
            </div>
          ))}
        </div>
      </section>

      {/* ─── HOW IT WORKS ─── */}
      <section id="how" className="mx-auto mt-24 max-w-6xl px-5 sm:px-8">
        <div className="mb-10">
          <span className="mono-label">/ 02 — process</span>
          <h2 className="mt-2 font-display text-3xl tracking-tightest sm:text-4xl">
            How it <span className="italic text-lime">works</span>.
          </h2>
        </div>

        <ol className="grid gap-4 md:grid-cols-3">
          {STEPS.map((s, i) => (
            <li
              key={s.title}
              className="relative rounded-3xl border hairline bg-ink-900/60 p-6 backdrop-blur"
            >
              <div className="absolute right-6 top-6 font-display text-5xl text-lime/15 leading-none">
                0{i + 1}
              </div>
              <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-lime/10 text-lime">
                <s.icon className="h-5 w-5" />
              </span>
              <h3 className="mt-5 font-display text-2xl tracking-tightest">{s.title}</h3>
              <p className="mt-2 text-sm text-bone/55">{s.body}</p>
            </li>
          ))}
        </ol>
      </section>

      {/* ─── FAQ ─── */}
      <section id="faq" className="mx-auto mt-24 max-w-3xl px-5 sm:px-8">
        <div className="mb-10 text-center">
          <span className="mono-label">/ 03 — questions</span>
          <h2 className="mt-2 font-display text-3xl tracking-tightest sm:text-4xl">
            Frequently <span className="italic text-lime">asked</span>.
          </h2>
        </div>
        <div className="divide-y divide-white/[0.08] rounded-3xl border hairline bg-ink-900/60 backdrop-blur">
          {FAQS.map((f) => (
            <details key={f.q} className="group p-5 sm:p-6">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-4">
                <h3 className="font-display text-xl tracking-tightest text-bone/90 group-hover:text-bone">
                  {f.q}
                </h3>
                <span className="flex h-7 w-7 flex-none items-center justify-center rounded-full border hairline text-bone/50 transition-transform group-open:rotate-45">
                  <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth={2}>
                    <path d="M12 5v14M5 12h14" strokeLinecap="round" />
                  </svg>
                </span>
              </summary>
              <p className="mt-3 text-sm text-bone/60">{f.a}</p>
            </details>
          ))}
        </div>
      </section>

      {/* ─── DISCLAIMER ─── */}
      <section className="mx-auto mt-24 max-w-3xl px-5 sm:px-8">
        <div className="rounded-3xl border border-lime/15 bg-lime/[0.03] p-6 sm:p-8">
          <div className="flex items-start gap-3">
            <ShieldCheck className="h-5 w-5 flex-none text-lime" />
            <div>
              <h3 className="font-display text-xl tracking-tightest">A note on use</h3>
              <p className="mt-2 text-sm leading-relaxed text-bone/65">
                This tool is intended only for downloading videos you own, have permission to use,
                or that are legally available for download. Users are responsible for respecting
                copyright laws and platform terms of service.
              </p>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
