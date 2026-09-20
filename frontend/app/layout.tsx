import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/lib/auth";
import { I18nProvider } from "@/components/I18nProvider";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  metadataBase: new URL("https://stickstock.lol"),
  title: "AI Control Tower",
  description: "Governance for every AI in your company — from shadow AI to autonomous agents, with verifiable accountability.",
  openGraph: {
    title: "AI Control Tower",
    description: "Governance for every AI in your company — from shadow AI to autonomous agents, with verifiable accountability.",
    type: "website",
    images: [{ url: "/og-image.png", width: 1200, height: 630, alt: "AI Control Tower" }],
  },
  twitter: {
    card: "summary_large_image",
    title: "AI Control Tower",
    description: "Governance for every AI in your company, with verifiable accountability.",
    images: ["/og-image.png"],
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable}`}>
      <body>
        <I18nProvider>
          <AuthProvider>{children}</AuthProvider>
        </I18nProvider>
      </body>
    </html>
  );
}