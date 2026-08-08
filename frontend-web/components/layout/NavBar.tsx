import Link from "next/link";
import { Compass } from "lucide-react";

const links = [
  { href: "/journey", label: "Journey", active: true },
  { href: "/compare", label: "Compare", active: true },
  { href: "/insights", label: "Insights", active: true },
  { href: "/analyst", label: "AI Analyst", active: true },
  { href: "/history", label: "History", active: true },
  { href: "/settings", label: "Settings", active: true },
];

export function NavBar() {
  return (
    <header className="sticky top-0 z-40 border-b border-surface-border bg-surface-0/80 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
        <div className="flex items-center gap-2 font-display text-sm font-semibold tracking-wide text-ink-primary">
          <Compass className="h-5 w-5 text-brass" />
          Journey Intelligence Engine
        </div>
        <nav className="flex items-center gap-6 text-sm">
          {links.map((link) =>
            link.active ? (
              <Link key={link.label} href={link.href} className="text-ink-secondary hover:text-ink-primary">
                {link.label}
              </Link>
            ) : (
              <span key={link.label} className="cursor-not-allowed text-ink-muted">
                {link.label}
              </span>
            )
          )}
        </nav>
      </div>
    </header>
  );
}
