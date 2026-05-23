import { LegalPage } from "@/components/legal-page";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "DMCA & Copyright",
  description: "How to file a copyright notice with ClipFetch.",
};

export default function DmcaPage() {
  return (
    <LegalPage kicker="dmca" title="DMCA & Copyright" updated="January 2026">
      <p>
        ClipFetch does not host any video content. We are a thin proxy that
        retrieves publicly accessible videos from third-party platforms at the
        request of an end user. Nothing is stored on our servers.
      </p>

      <p>
        Even so, if you are a rights holder and you believe our service is being
        used to infringe your copyright, we want to hear from you.
      </p>

      <Section title="Filing a notice">
        <p>Send an email to the address below with the following information:</p>
        <ul className="ml-5 list-disc space-y-1">
          <li>Identification of the copyrighted work you believe is being infringed.</li>
          <li>The URL on the source platform where the content is located.</li>
          <li>Your full name, address, telephone number, and email address.</li>
          <li>
            A statement that you have a good-faith belief that the use described
            is not authorized by the copyright owner, its agent, or the law.
          </li>
          <li>
            A statement that the information in your notice is accurate, and
            under penalty of perjury, that you are authorized to act on behalf
            of the copyright owner.
          </li>
          <li>Your physical or electronic signature.</li>
        </ul>
      </Section>

      <Section title="Where to send">
        <p className="font-mono text-sm text-lime">copyright joshuasundayola@gmail.com</p>
        <p className="text-sm text-bone/55">
          We aim to respond to valid notices within five business days. For the
          fastest result, please direct your notice to the platform hosting the
          original video as well — they are the party who can actually remove it.
        </p>
      </Section>

      <Section title="Counter-notices">
        <p>
          If you believe content was reported in error, you may submit a
          counter-notice to the same address. Include your contact information,
          identification of the material, and a statement under penalty of
          perjury that you have a good-faith belief the report was a mistake.
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
