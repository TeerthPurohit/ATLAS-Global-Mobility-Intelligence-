import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "./providers";
import { ThemeProvider } from "@/context/ThemeContext";
import { AppProvider } from "@/context/AppContext";
import { AuthProvider } from "@/context/AuthContext";
import { NavBar } from "@/components/layout/NavBar";
import { CommandPalette } from "@/components/layout/CommandPalette";
import { SmoothScrollProvider } from "@/components/layout/SmoothScrollProvider";
import { RequireAuth } from "@/components/layout/RequireAuth";

export const metadata: Metadata = {
  title: "ATLAS | NYC Ride Intelligence",
  description: "Urban mobility intelligence built on real NYC TLC trip records. Demand, fares, and journey estimates for New York City.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `
              try {
                const saved = localStorage.getItem('atlas_theme');
                const theme = saved || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
                document.documentElement.setAttribute('data-theme', theme);
                if (theme === 'dark') document.documentElement.classList.add('dark');
              } catch (e) {}
            `,
          }}
        />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="min-h-screen font-body-md bg-surface-0 text-ink-primary">
        <Providers>
          <ThemeProvider>
            <SmoothScrollProvider>
              <AuthProvider>
                <AppProvider>
                  <NavBar />
                  <CommandPalette />
                  <main className="min-h-[calc(100dvh-5rem)] w-full px-4 py-5 sm:px-8 sm:py-8 lg:px-10">
                    <RequireAuth>{children}</RequireAuth>
                  </main>
                </AppProvider>
              </AuthProvider>
            </SmoothScrollProvider>
          </ThemeProvider>
        </Providers>
      </body>
    </html>
  );
}
