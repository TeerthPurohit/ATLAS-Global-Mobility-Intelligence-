"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Compass } from "lucide-react";
import { cn } from "@/lib/utils";
import { motion } from "framer-motion";
import { PulsingStatusDot } from "@/components/magic/PulsingStatusDot";

const navLinks = [
  { href: "/", label: "Explore" },
  { href: "/journey", label: "Journey" },
  { href: "/compare", label: "Compare" },
  { href: "/insights", label: "Insights" },
  { href: "/analyst", label: "Ask" },
  { href: "/analytics", label: "Analytics" },
];

export function NavBar() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-40 border-b border-surface-border bg-surface-0/95 backdrop-blur-sm transition-shadow duration-300">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4 sm:px-6">
        {/* Logo & Brand */}
        <Link
          href="/"
          className="flex items-center gap-3 group"
        >
          <div className="relative flex items-center justify-center">
            <Compass className="h-5 w-5 text-brass transition-transform duration-500 group-hover:rotate-45" />
          </div>
          <div className="flex flex-col gap-0">
            <span className="hidden sm:block font-section-md text-ink-primary leading-tight">
              WORLDMOVE
            </span>
            <span className="hidden sm:block font-label-sm text-ink-muted">
              Mobility Intelligence
            </span>
            <span className="sm:hidden font-section-md text-ink-primary">
              WORLDMOVE
            </span>
          </div>
          <PulsingStatusDot status="live" size={6} className="ml-2" />
        </Link>

        {/* Navigation Links */}
        <nav className="flex items-center gap-1 sm:gap-3">
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
                  "relative px-3 py-2 transition-colors font-section-md text-sm",
                  isActive
                    ? "text-brass"
                    : "text-ink-secondary hover:text-ink-primary"
                )}
              >
                {isActive && (
                  <motion.div
                    layoutId="activeNavUnderline"
                    className="absolute bottom-0 left-0 right-0 h-0.5 bg-brass"
                    transition={{ type: "spring", stiffness: 380, damping: 30 }}
                  />
                )}
                <span className="relative z-10">{link.label}</span>
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
