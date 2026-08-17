import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "./providers";
import { AppProvider } from "@/context/AppContext";
import { NavBar } from "@/components/layout/NavBar";
import { CommandPalette } from "@/components/layout/CommandPalette";
import { SmoothScrollProvider } from "@/components/layout/SmoothScrollProvider";

export const metadata: Metadata = {
  title: "ATLAS | Global Mobility Analysis",
  description: "Global urban mobility intelligence platform. Understand demand, fares, and patterns across NYC, London, and 500+ WorldMove-covered cities.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" data-theme="dark">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="min-h-screen font-body-md bg-surface-0 text-ink-primary">
        <Providers>
          <SmoothScrollProvider>
            <AppProvider>
              <NavBar />
              <CommandPalette />
              <main className="mx-auto max-w-7xl px-4 sm:px-6 py-8 sm:py-12">
                {children}
              </main>
            </AppProvider>
          </SmoothScrollProvider>
        </Providers>
      </body>
    </html>
  );
}
