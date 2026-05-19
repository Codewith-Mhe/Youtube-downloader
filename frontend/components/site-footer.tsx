import Link from "next/link";

export function SiteFooter() {
  return (
    <footer className="mt-32 border-t hairline">
      <div className="mx-auto max-w-6xl px-5 py-12 sm:px-8">
        <div className="grid gap-10 sm:grid-cols-2 md:grid-cols-4">
          <div className="md:col-span-2">
            <Link href="/" className="font-display text-2xl tracking-tightest">
              clip<span className="italic text-lime">fetch</span>
            </Link>
            <p className="mt-4 max-w-sm text-sm text-bone/60">
              A fast, private way to save videos from YouTube, TikTok, X, and Facebook.
              No signup. No tracking. No ads.
            </p>
          </div>

          <div>
            <h4 className="mono-label mb-4">Legal</h4>
            <ul className="space-y-2 text-sm">
              <li><Link href="/privacy" className="text-bone/70 hover:text-bone">Privacy</Link></li>
              <li><Link href="/terms" className="text-bone/70 hover:text-bone">Terms</Link></li>
              <li><Link href="/dmca" className="text-bone/70 hover:text-bone">DMCA</Link></li>
            </ul>
          </div>

          <div>
            <h4 className="mono-label mb-4">More</h4>
            <ul className="space-y-2 text-sm">
              <li><Link href="/#how" className="text-bone/70 hover:text-bone">How it works</Link></li>
              <li><Link href="/#faq" className="text-bone/70 hover:text-bone">FAQ</Link></li>
              <li><Link href="/contact" className="text-bone/70 hover:text-bone">Contact</Link></li>
            </ul>
          </div>
        </div>

        <div className="mt-12 flex flex-col gap-3 border-t hairline pt-6 text-xs text-bone/40 sm:flex-row sm:items-center sm:justify-between">
          <p>© {new Date().getFullYear()} ClipFetch. Built with care.</p>
          <p className="font-mono">
            Only download what you have the right to download.
          </p>
        </div>
      </div>
    </footer>
  );
}
