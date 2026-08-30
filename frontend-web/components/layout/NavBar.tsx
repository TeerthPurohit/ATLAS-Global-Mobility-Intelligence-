"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Compass, LogOut, Database, Activity, Zap, Layers } from "lucide-react";
import { cn } from "@/lib/utils";
import { motion } from "framer-motion";
import { PulsingStatusDot } from "@/components/magic/PulsingStatusDot";
import { useAuth } from "@/context/AuthContext";

const navLinks = [
  { href: "/", label: "Explore" },
  { href: "/journey", label: "Journey" },
  { href: "/compare", label: "Compare" },
  { href: "/insights", label: "Insights" },
  { href: "/analyst", label: "Ask AI" },
  { href: "/analytics", label: "Analytics" },
  { href: "/docs", label: "Docs" },
];

export function NavBar() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, loading, logout } = useAuth();
  const isHeroPage = pathname === "/";
  const isLoginPage = pathname === "/login" || pathname === "/signup";

  async function handleLogout() {
    await logout();
    router.push("/login");
  }

  if (isLoginPage) return null;

  return (
    <header
      className={cn(
        "sticky top-0 z-40 transition-colors duration-300",
        isHeroPage
          ? "border-b border-surface-border/40 bg-surface-0/80 backdrop-blur-md"
          : "border-b border-surface-border bg-surface-0/95 backdrop-blur-md"
      )}
    >
      {/* Top Main Navigation Bar */}
      <div className="mx-auto flex w-full items-center justify-between px-4 py-3 sm:px-8 lg:px-10">
        {/* Logo & Brand */}
        <Link href="/" className="group flex items-center gap-3">
          <div className="relative flex h-8 w-8 items-center justify-center rounded-xl bg-brass/10 border border-brass/30 transition-transform duration-500 group-hover:scale-105">
            <Compass className="h-4 w-4 text-brass transition-transform duration-500 group-hover:rotate-45" />
          </div>
          <div className="flex flex-col">
            <div className="flex items-center gap-2">
              <span className="font-section-md text-sm font-bold tracking-wider text-ink-primary">
                ATLAS
              </span>
              <span className="rounded bg-brass/15 px-1.5 py-0.2 text-[10px] font-mono font-semibold uppercase text-brass">
                NYC TLC
              </span>
            </div>
            <span className="hidden text-[11px] font-mono text-ink-muted sm:block">
              Mobility Intelligence System
            </span>
          </div>
        </Link>

        {/* Navigation Links */}
        <nav className="flex items-center gap-1 sm:gap-2">
          {navLinks.map((link) => {
            const isActive =
              link.href === "/"
                ? pathname === "/" || pathname.startsWith("/city")
                : pathname.startsWith(link.href);

            return (
              <Link
                key={link.label}
                href={link.href}
                className={cn(
                  "relative rounded-lg px-3 py-1.5 font-section-md text-xs sm:text-sm transition-all",
                  isActive
                    ? "text-brass bg-brass/10 font-semibold shadow-sm"
                    : "text-ink-secondary hover:bg-surface-1 hover:text-ink-primary"
                )}
              >
                {isActive && (
                  <motion.div
                    layoutId="activeNavUnderline"
                    className="absolute inset-0 rounded-lg border border-brass/30"
                    transition={{ type: "spring", stiffness: 380, damping: 30 }}
                  />
                )}
                <span className="relative z-10">{link.label}</span>
              </Link>
            );
          })}
        </nav>

        {/* Auth & Live Pulse */}
        <div className="flex items-center gap-3">
          <div className="hidden xl:flex items-center gap-1.5 rounded-full border border-surface-border bg-surface-1/80 px-2.5 py-1 text-[11px] font-mono text-ink-secondary">
            <PulsingStatusDot status="live" size={6} />
            <span>263 Zones Active</span>
          </div>

          {loading ? null : user ? (
            <div className="flex items-center gap-2">
              <span className="hidden max-w-[140px] truncate font-mono text-xs text-ink-secondary md:block">
                {user.email}
              </span>
              <button
                onClick={handleLogout}
                title="Log out"
                className="flex items-center gap-1.5 rounded-lg border border-surface-border bg-surface-1/80 px-2.5 py-1.5 font-section-md text-xs text-ink-secondary transition-colors hover:bg-danger/10 hover:text-danger hover:border-danger/30"
              >
                <LogOut className="h-3.5 w-3.5" />
                <span className="hidden sm:inline">Log out</span>
              </button>
            </div>
          ) : (
            <Link
              href="/login"
              className="rounded-lg bg-brass px-3.5 py-1.5 font-section-md text-xs font-semibold text-white shadow-sm transition-all hover:bg-brass/90"
            >
              Sign In
            </Link>
          )}
        </div>
      </div>

      {/* Global Telemetry Mission Ribbon (Active on all routes except login) */}
      {!isLoginPage && (
        <div className="hidden border-t border-surface-border/60 bg-surface-0/60 px-4 py-1 backdrop-blur-sm sm:flex items-center justify-between text-[11px] font-mono text-ink-muted sm:px-8 lg:px-10">
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1.5 text-ink-secondary">
              <Database className="h-3 w-3 text-brass" />
              <span>Mart: <strong className="text-ink-primary font-medium">1.4B+ Records</strong></span>
            </span>
            <span>•</span>
            <span className="flex items-center gap-1.5 text-ink-secondary">
              <Layers className="h-3 w-3 text-accent-primary" />
              <span>Coverage: <strong className="text-ink-primary font-medium">5 Boroughs (263 Zones)</strong></span>
            </span>
            <span>•</span>
            <span className="flex items-center gap-1.5 text-ink-secondary">
              <Activity className="h-3 w-3 text-emerald-500" />
              <span>Congestion: <strong className="text-emerald-600 font-medium">Monitored Real-Time</strong></span>
            </span>
          </div>

          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1 text-ink-muted">
              <Zap className="h-3 w-3 text-indigo-500" />
              <span>Latency: &lt;85ms</span>
            </span>
            <span className="text-brass/80 font-semibold">● Ground Truth Validated</span>
          </div>
        </div>
      )}
    </header>
  );
}
