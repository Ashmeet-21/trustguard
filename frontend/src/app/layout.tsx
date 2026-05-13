import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import Navbar from "@/components/Navbar";
import Providers from "@/lib/Providers";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: {
    default: "TrustGuard — AI-Powered Identity Verification",
    template: "%s | TrustGuard",
  },
  description:
    "Verify real humans with 4 AI agents: deepfake detection (99%+ accuracy), liveness analysis, voice verification, and behavioral biometrics — all combined into one trust score.",
  keywords: [
    "identity verification",
    "deepfake detection",
    "liveness detection",
    "voice verification",
    "behavioral biometrics",
    "KYC",
    "anti-spoofing",
    "trust score",
    "AI security",
  ],
  authors: [{ name: "Ashmeet Singh" }],
  openGraph: {
    title: "TrustGuard — AI-Powered Identity Verification",
    description:
      "4 independent AI agents verify identity through face, voice, and behavior analysis. Built with FastAPI, Vision Transformers, and Next.js.",
    type: "website",
    locale: "en_US",
    siteName: "TrustGuard",
  },
  twitter: {
    card: "summary_large_image",
    title: "TrustGuard — AI-Powered Identity Verification",
    description:
      "Multi-agent identity verification: deepfake detection, liveness checks, voice analysis, behavioral biometrics.",
  },
  robots: {
    index: true,
    follow: true,
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased min-h-screen`}
      >
        <div className="mesh-bg" />
        <div className="noise-overlay" />
        <Providers>
          <Navbar />
          <main>{children}</main>
        </Providers>
      </body>
    </html>
  );
}
