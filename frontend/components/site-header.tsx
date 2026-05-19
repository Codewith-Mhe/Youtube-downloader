import Link from "next/link";
import { Github } from "lucide-react";

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-40 border-b hairline bg-ink-950/70 backdrop-blur-xl">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-5 py-4 sm:px-8">
        <Link href="/" className="group flex items-center gap-2.5">
          <LogoMark />
          <span className="font-display text-xl tracking-tightest">
            clip<span className="italic text-lime">fetch</span>
          </span>
        </Link>
        <nav className="flex items-center gap-1 sm:gap-2">
          <Link
            href="/#how"
            className="hidden sm:inline-flex px-3 py-2 text-sm text-bone/70 hover:text-bone transition-colors"
          >
            How it works
          </Link>
          <Link
            href="/#faq"
            className="hidden sm:inline-flex px-3 py-2 text-sm text-bone/70 hover:text-bone transition-colors"
          >
            FAQ
          </Link>
          <Link
            href="/contact"
            className="px-3 py-2 text-sm text-bone/70 hover:text-bone transition-colors"
          >
            Contact
          </Link>
        </nav>
      </div>
    </header>
  );
}

function LogoMark() {
  return (
    <span className="relative inline-flex h-8 w-8 items-center justify-center rounded-xl bg-lime text-ink-950 shadow-[0_0_0_1px_rgba(200,242,92,0.4)] transition-transform group-hover:rotate-[-3deg]">
      <svg viewBox="0 0 24 24" className="h-4 w-4" fill="currentColor" aria-hidden="true">
        <path d="M8 5v14l11-7L8 5z" />
      </svg>
    </span>
  );
}
