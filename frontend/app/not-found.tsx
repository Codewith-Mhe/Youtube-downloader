import Link from "next/link";

export default function NotFound() {
  return (
    <section className="mx-auto flex max-w-xl flex-col items-center px-5 py-32 text-center sm:px-8">
      <span className="mono-label">/ 404</span>
      <h1 className="mt-4 font-display text-6xl tracking-tightest">
        Not <span className="italic text-lime">found</span>.
      </h1>
      <p className="mt-4 text-bone/55">
        That page doesn&apos;t exist — or it never did.
      </p>
      <Link href="/" className="btn-primary mt-8">
        Take me home
      </Link>
    </section>
  );
}
