"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Compass, Globe } from "lucide-react";
import { cn } from "@/lib/utils";

const navLinks = [
  { href: "/", label: "World", icon: Globe },
  { href: "/journey", label: "Journey" },
  { href: "/compare", label: "Compare" },
  { href: "/insights", label: "Insights" },
  { href: "/analyst", label: "AI Analyst" },
  { href: "/analytics", label: "Analytics" },
  { href: "/history", label: "History" },
  { href: "/settings", label: "Settings" },
];

export function NavBar() {
  const pathname = usePathname();

  // Generate dynamic breadcrumb items from pathname
  const pathSegments = pathname.split("/").filter(Boolean);

  return (
    <header className="sticky top-0 z-40 border-b border-surface-border bg-surface-0/85 backdrop-blur-md">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6">
        <div className="flex items-center gap-3">
          <Link
            href="/"
            className="flex items-center gap-2 font-display text-sm font-semibold tracking-wide text-ink-primary transition-opacity hover:opacity-90"
          >
            <Compass className="h-5 w-5 text-brass" />
            <span className="hidden sm:inline">Global Mobility Intelligence</span>
            <span className="sm:hidden">GMI</span>
          </Link>

          {/* Breadcrumb Bar */}
          {pathSegments.length > 0 && (
            <div className="hidden md:flex items-center gap-1.5 border-l border-surface-border pl-3 text-xs text-ink-muted">
              <Link href="/" className="hover:text-brass transition-colors">
                world
              </Link>
              {pathSegments.map((segment, index) => {
                const href = `/${pathSegments.slice(0, index + 1).join("/")}`;
                const isLast = index === pathSegments.length - 1;
                return (
                  <span key={href} className="flex items-center gap-1.5">
                    <span>/</span>
                    {isLast ? (
                      <span className="font-semibold text-brass truncate max-w-[120px]">
                        {segment}
                      </span>
                    ) : (
                      <Link href={href} className="hover:text-brass transition-colors truncate max-w-[100px]">
                        {segment}
                      </Link>
                    )}
                  </span>
                );
              })}
            </div>
          )}
        </div>

        <nav className="flex items-center gap-1.5 sm:gap-4 text-xs sm:text-sm">
          {navLinks.map((link) => {
            const isActive =
              link.href === "/"
                ? pathname === "/" || pathname.startsWith("/country") || pathname.startsWith("/city")
                : pathname.startsWith(link.href);

            return (
              <Link
                key={link.label}
                href={link.href}
                className={cn(
                  "px-2.5 py-1.5 rounded-lg transition-colors font-medium",
                  isActive
                    ? "bg-surface-1 text-brass font-semibold"
                    : "text-ink-secondary hover:text-ink-primary hover:bg-surface-1/50"
                )}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
