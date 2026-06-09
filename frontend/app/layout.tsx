import type { Metadata, Viewport } from "next";
import { Inter, Instrument_Serif } from "next/font/google";
import { ThemeProvider } from "next-themes";
import "./globals.css";
import { SiteHeader } from "@/components/site-header";
import { SiteFooter } from "@/components/site-footer";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const instrumentSerif = Instrument_Serif({
  subsets: ["latin"],
  weight: ["400"],
  style: ["normal", "italic"],
  variable: "--font-instrument-serif",
  display: "swap",
});

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://clipfetch.app";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: "ClipFetch — Download videos from TikTok, X, and Facebook",
    template: "%s · ClipFetch",
  },
  description:
    "Download videos from TikTok, X, and Facebook instantly in multiple qualities — fast, free, and without signup.",
  keywords: [
    "tiktok downloader",
    "twitter video downloader",
    "x video downloader",
    "facebook video downloader",
    "free video downloader",
    "video downloader",
    "clipfetch",
  ],
  openGraph: {
    type: "website",
    title: "ClipFetch — Download videos in seconds",
    description: "Download videos from TikTok, X, and Facebook instantly in multiple qualities.",
    url: SITE_URL,
    siteName: "ClipFetch",
  },
  twitter: {
    card: "summary_large_image",
    title: "ClipFetch — Download videos in seconds",
    description: "Paste your video link, choose quality, and download instantly.",
  },
  robots: { index: true, follow: true },
};

export const viewport: Viewport = {
  themeColor: "#070708",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${instrumentSerif.variable}`} suppressHydrationWarning>
      <body className="min-h-screen relative antialiased">
        <ThemeProvider attribute="class" defaultTheme="dark" enableSystem>
          <div className="grain-overlay" aria-hidden="true" />
          <div className="relative z-10 flex min-h-screen flex-col">
            <SiteHeader />
            <main className="flex-1">{children}</main>
            <SiteFooter />
          </div>
        </ThemeProvider>
      </body>
    </html>
  );
}