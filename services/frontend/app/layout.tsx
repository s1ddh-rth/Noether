import type { Metadata } from "next";
import localFont from "next/font/local";

import "./globals.css";
import { Header } from "@/components/Header";

// Self-hosted fonts (bundled .woff under app/fonts) — no Google Fonts,
// no external requests (air-gap requirement, spec §"Air-gapped operation").
const geistSans = localFont({
  src: "./fonts/GeistVF.woff",
  variable: "--font-geist-sans",
  weight: "100 900",
});
const geistMono = localFont({
  src: "./fonts/GeistMonoVF.woff",
  variable: "--font-geist-mono",
  weight: "100 900",
});

export const metadata: Metadata = {
  title: "Noether",
  description: "Live plant telemetry, anomalies, and operator chat.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased`}>
        <Header />
        <main className="mx-auto max-w-7xl px-4 py-6">{children}</main>
      </body>
    </html>
  );
}
