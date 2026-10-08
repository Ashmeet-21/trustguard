import type { Metadata } from "next";
import { Schibsted_Grotesk, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";
import Navbar from "@/components/Navbar";
import Providers from "@/lib/Providers";

const schibsted = Schibsted_Grotesk({
  variable: "--font-schibsted",
  subsets: ["latin"],
});

const plexMono = IBM_Plex_Mono({
  variable: "--font-plex-mono",
  subsets: ["latin"],
  weight: ["400", "500"],
});

const API_DOCS = `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/docs`;

export const metadata: Metadata = {
  title: {
    default: "TrustGuard — identity verification",
    template: "%s | TrustGuard",
  },
  description:
    "Checks a selfie, a voice sample and typing behaviour to decide whether a person is real — with every check, score and rule shown.",
  keywords: [
    "identity verification",
    "deepfake detection",
    "liveness detection",
    "voice verification",
    "behavioral biometrics",
    "KYC",
  ],
  authors: [{ name: "Ashmeet Singh" }],
  openGraph: {
    title: "TrustGuard — identity verification",
    description:
      "Four independent checks on face, voice and typing, combined into one auditable decision.",
    type: "website",
    locale: "en_US",
    siteName: "TrustGuard",
  },
  robots: { index: true, follow: true },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${schibsted.variable} ${plexMono.variable} antialiased min-h-screen flex flex-col`}>
        <Providers>
          <Navbar />
          <main className="flex-1">{children}</main>
          <footer className="border-t border-rule mt-8">
            <div className="max-w-6xl mx-auto px-6 py-8 flex flex-col sm:flex-row gap-3 sm:items-center justify-between text-sm text-ink-faint">
              <p>TrustGuard is a portfolio project by Ashmeet Singh.</p>
              <div className="flex gap-6">
                <a className="hover:text-ink" href="https://github.com/Ashmeet-21/trustguard" target="_blank" rel="noopener noreferrer">
                  Source code
                </a>
                <a className="hover:text-ink" href={API_DOCS} target="_blank" rel="noopener noreferrer">
                  API reference
                </a>
              </div>
            </div>
          </footer>
        </Providers>
      </body>
    </html>
  );
}
