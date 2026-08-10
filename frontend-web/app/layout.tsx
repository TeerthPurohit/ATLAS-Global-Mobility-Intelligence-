import type { Metadata } from "next";
import { Inter, IBM_Plex_Mono, Outfit } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";
import { AppProvider } from "@/context/AppContext";
import { NavBar } from "@/components/layout/NavBar";
import { CommandPalette } from "@/components/layout/CommandPalette";

const inter = Inter({ subsets: ["latin"], variable: "--font-sans", display: "swap" });
const outfit = Outfit({ subsets: ["latin"], variable: "--font-display", display: "swap" });
const plexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Global Mobility Intelligence",
  description: "Fare, ETA, demand, and risk intelligence engine with capability-aware basis transparency.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" data-theme="dark">
      <body
        className={`min-h-screen font-sans bg-surface-0 text-ink-primary ${inter.variable} ${outfit.variable} ${plexMono.variable}`}
      >
        <Providers>
          <AppProvider>
            <NavBar />
            <CommandPalette />
            <main className="mx-auto max-w-7xl px-4 sm:px-6 py-6 sm:py-8">{children}</main>
          </AppProvider>
        </Providers>
      </body>
    </html>
  );
}
