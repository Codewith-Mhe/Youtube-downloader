import type { ReactNode } from "react";

export function LegalPage({
  kicker,
  title,
  updated,
  children,
}: {
  kicker: string;
  title: string;
  updated: string;
  children: ReactNode;
}) {
  return (
    <article className="mx-auto max-w-3xl px-5 py-16 sm:px-8 sm:py-24">
      <span className="mono-label">/ {kicker}</span>
      <h1 className="mt-3 font-display text-4xl tracking-tightest sm:text-5xl">{title}</h1>
      <p className="mt-3 font-mono text-xs text-bone/40">Last updated · {updated}</p>
      <div className="prose-clipfetch mt-10 space-y-6 text-bone/75 leading-relaxed">
        {children}
      </div>
    </article>
  );
}
