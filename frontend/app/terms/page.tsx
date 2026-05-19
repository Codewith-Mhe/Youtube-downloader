import { LegalPage } from "@/components/legal-page";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Terms of Use",
  description: "The rules for using ClipFetch.",
};

export default function TermsPage() {
  return (
    <LegalPage kicker="terms" title="Terms of Use" updated="January 2026">
      <p>
        By using ClipFetch you agree to these terms. They are written to be plain
        and short.
      </p>

      <Section title="Acceptable use">
        <p>You may use ClipFetch only to download content that you:</p>
        <ul className="ml-5 list-disc space-y-1">
          <li>own, or</li>
          <li>have explicit permission to download, or</li>
          <li>are otherwise legally allowed to download (e.g. content in the public domain or licensed for reuse).</li>
        </ul>
        <p>
          You agree not to use ClipFetch to infringe copyright, distribute pirated
          material, or violate the terms of the source platform (YouTube, TikTok,
          X, Facebook).
        </p>
      </Section>

      <Section title="No warranty">
        <p>
          ClipFetch is provided &quot;as is&quot; without warranty of any kind. We
          do not guarantee that any specific video can be downloaded, that the
          service will be available, or that downloads will be free of errors.
        </p>
      </Section>

      <Section title="Limitation of liability">
        <p>
          To the maximum extent permitted by law, ClipFetch and its operators are
          not liable for any damages arising from the use or inability to use the
          service.
        </p>
      </Section>

      <Section title="Rate limits and abuse">
        <p>
          We apply per-IP rate limits to keep the service fast for everyone. We
          reserve the right to block traffic that appears abusive, automated, or
          designed to circumvent these limits.
        </p>
      </Section>

      <Section title="Changes">
        <p>
          We may update these terms occasionally. Continued use of the service
          after changes constitutes acceptance.
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
