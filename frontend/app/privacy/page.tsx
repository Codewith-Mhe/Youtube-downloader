import { LegalPage } from "@/components/legal-page";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Privacy Policy",
  description: "How ClipFetch handles your data — short version: we don't.",
};

export default function PrivacyPage() {
  return (
    <LegalPage kicker="privacy" title="Privacy Policy" updated="January 2026">
      <p>
        ClipFetch is designed to do its job and forget. We do not require accounts,
        we do not run third-party analytics or advertising trackers, and we do not
        store the videos you download.
      </p>

      <Section title="What we collect">
        <p>
          We collect only what is technically necessary to operate the service:
        </p>
        <ul className="ml-5 list-disc space-y-1">
          <li>Your IP address, briefly, for rate limiting and abuse prevention.</li>
          <li>Aggregated, anonymous error logs for debugging.</li>
          <li>Request metadata required to fulfill a download (URL submitted, format chosen).</li>
        </ul>
      </Section>

      <Section title="What we don't collect">
        <ul className="ml-5 list-disc space-y-1">
          <li>Your name, email, or any account information.</li>
          <li>Cookies for advertising or cross-site tracking.</li>
          <li>Copies of the videos you download — we stream them, we don&apos;t store them.</li>
        </ul>
      </Section>

      <Section title="Retention">
        <p>
          Operational logs are kept for up to 14 days, then deleted. Download tokens
          expire automatically after 30 minutes.
        </p>
      </Section>

      <Section title="Third parties">
        <p>
          To extract video metadata, our server contacts the source platform
          (YouTube, TikTok, X, or Facebook) on your behalf. Those platforms have
          their own privacy practices, which we cannot control.
        </p>
      </Section>

      <Section title="Contact">
        <p>
          Questions? Reach out via the <a className="text-lime hover:underline" href="/contact">contact page</a>.
        </p>
      </Section>
    </LegalPage>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <h2 className="font-display text-2xl tracking-tightest text-bone">{title}</h2>
      <div className="mt-3 space-y-3">{children}</div>
    </section>
  );
}
