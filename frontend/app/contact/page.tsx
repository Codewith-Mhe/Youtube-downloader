import { LegalPage } from "@/components/legal-page";
import { Mail, MessageCircleQuestion, Shield } from "lucide-react";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Contact",
  description: "Get in touch with the ClipFetch team.",
};

const CHANNELS = [
  {
    icon: MessageCircleQuestion,
    title: "General questions",
    email: "hello@clipfetch.app",
    body: "Feedback, feature ideas, partnership inquiries.",
  },
  {
    icon: Shield,
    title: "Copyright / DMCA",
    email: "copyright@clipfetch.app",
    body: "See our DMCA page for what to include.",
  },
  {
    icon: Mail,
    title: "Security",
    email: "security@clipfetch.app",
    body: "Responsible disclosure of vulnerabilities. Please do not test on production without prior contact.",
  },
];

export default function ContactPage() {
  return (
    <LegalPage kicker="contact" title="Get in touch" updated="January 2026">
      <p>
        ClipFetch is a small operation. We read every email — please give us a few
        business days to reply.
      </p>

      <div className="mt-6 grid gap-3 sm:grid-cols-1">
        {CHANNELS.map((c) => (
          <a
            key={c.title}
            href={`mailto:${c.email}`}
            className="group flex items-start gap-4 rounded-3xl border hairline bg-ink-900/60 p-5 backdrop-blur transition-colors hover:border-white/20"
          >
            <span className="flex h-10 w-10 flex-none items-center justify-center rounded-xl bg-lime/10 text-lime">
              <c.icon className="h-5 w-5" />
            </span>
            <div className="min-w-0">
              <h3 className="font-display text-xl tracking-tightest text-bone">{c.title}</h3>
              <p className="mt-1 text-sm text-bone/60">{c.body}</p>
              <p className="mt-2 font-mono text-sm text-lime">{c.email}</p>
            </div>
          </a>
        ))}
      </div>
    </LegalPage>
  );
}
